#!/usr/bin/env python3
"""
AI Infrastructure Scout Agent
==============================
Powered by Claude. Covers accelerators A1, A2, A3, A5, A7, A8 (Linux + Windows).
One agent. One command. Client-ready executive report in minutes.

Usage:
  python agent.py --host 192.168.1.10 --user admin --key ~/.ssh/id_rsa
  python agent.py --vcenter vc.client.local --vc-user admin --vc-pass secret
  python agent.py --subnet 10.0.0.0/24
  python agent.py --full  # runs everything
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic
from gatekeeper_client import request_access
from dotenv import load_dotenv
load_dotenv()

# Check --demo in sys.argv early so mock imports happen before argparse runs
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true" or "--demo" in sys.argv

if DEMO_MODE:
    from tools.mock_tools import (
        mock_scan_linux_environment    as scan_linux_environment,
        mock_check_cis_benchmarks      as check_cis_benchmarks,
        mock_audit_automation_maturity as audit_automation_maturity,
        mock_scan_vmware_environment   as scan_vmware_environment,
        mock_scan_network_health       as scan_network_health,
        mock_assess_ai_stack           as assess_ai_stack,
    )
else:
    from tools.linux_scout    import scan_linux_environment, check_cis_benchmarks, audit_automation_maturity
    from tools.vmware_scout   import scan_vmware_environment
    from tools.network_scout  import scan_network_health
    from tools.ai_stack_scout import assess_ai_stack
    from tools.windows_scout  import scan_windows_environment, check_windows_security

# ── Model config ──────────────────────────────────────────────────────────────
# DEPLOY_MODE controls which backend the agent runs on:
#   "claude"       → direct Anthropic API  (fast, default, data touches Anthropic)
#   "bedrock"      → AWS Bedrock           (stays in client AWS account, compliance-friendly)
#   "ollama"       → local Ollama server   (air-gap / fully on-prem, needs GPU)
#   "venice"       → Venice AI via Agent Zero key (OpenAI-compat, open-source models)
#   "azure_openai" → Azure OpenAI Service  (stays in client Azure tenant, compliance-friendly)
DEPLOY_MODE = os.getenv("DEPLOY_MODE", "claude").lower()

# Model IDs per backend
MODELS = {
    "claude":        "claude-opus-4-6",
    "bedrock":       "us.anthropic.claude-sonnet-4-6",                        # Bedrock model ID format
    "ollama":        os.getenv("OLLAMA_MODEL", "llama3"),                # configurable local model
    "venice":        os.getenv("VENICE_MODEL", "llama-3.3-70b"),        # Venice AI (Agent Zero)
    "azure_openai":  os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),    # Azure OpenAI Service
}


def get_client():
    """Returns the right Claude client based on DEPLOY_MODE."""
    if DEPLOY_MODE == "bedrock":
        return anthropic.AnthropicBedrock(
            aws_access_key=os.getenv("aws_access_key_id"),
            aws_secret_key=os.getenv("aws_secret_access_key"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            aws_session_token=os.getenv("aws_session_token"),
        )
    elif DEPLOY_MODE == "ollama":
        # Ollama exposes an OpenAI-compatible endpoint — requires openai library
        try:
            from openai import OpenAI
            return OpenAI(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                api_key="ollama",
            )
        except ImportError:
            raise RuntimeError("DEPLOY_MODE=ollama requires: pip install openai")
    elif DEPLOY_MODE == "venice":
        # Venice AI via Agent Zero — OpenAI-compatible endpoint
        try:
            from openai import OpenAI
            return OpenAI(
                base_url="https://api.venice.ai/api/v1",
                api_key=os.getenv("VENICE_API_KEY"),
            )
        except ImportError:
            raise RuntimeError("DEPLOY_MODE=venice requires: pip install openai")
    elif DEPLOY_MODE == "azure_openai":
        # Azure OpenAI Service — Microsoft's enterprise OpenAI endpoint
        # Compatible with Derek/Quinnox Azure stack
        try:
            from openai import AzureOpenAI
            return AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            )
        except ImportError:
            raise RuntimeError("DEPLOY_MODE=azure_openai requires: pip install openai")
    else:
        return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def _is_openai_compat(client) -> bool:
    """True when the client is an OpenAI-compatible backend (venice, ollama, azure_openai)."""
    try:
        from openai import OpenAI, AzureOpenAI
        return isinstance(client, (OpenAI, AzureOpenAI))
    except ImportError:
        try:
            from openai import OpenAI
            return isinstance(client, OpenAI)
        except ImportError:
            return False


def _to_openai_tools(tools: list) -> list:
    """Convert Anthropic tool schema format → OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name":        t["name"],
                "description": t["description"],
                "parameters":  t["input_schema"],
            },
        }
        for t in tools
    ]


def _run_openai_loop(client, model: str, system_prompt: str,
                     user_request: str, client_name: str):
    """
    Agent loop for OpenAI-compatible backends (venice, ollama).
    Mirrors run_scout() but uses chat.completions API + OpenAI tool format.
    """
    oai_tools    = _to_openai_tools(TOOLS)
    messages     = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_request},
    ]
    all_findings = {}
    failed_tools = []

    print(f"\n[Scout] Starting assessment for: {client_name}")
    print(f"[Scout] {user_request}\n")

    while True:
        response = client.chat.completions.create(
            model=model,
            max_tokens=8096,
            tools=oai_tools,
            messages=messages,
        )
        choice = response.choices[0]
        msg    = choice.message

        if msg.content:
            print(msg.content)

        if choice.finish_reason == "stop":
            if msg.content and len(msg.content) > 200:
                return msg.content, all_findings
            return "Assessment complete — no report generated.", all_findings

        if choice.finish_reason != "tool_calls":
            break

        # Append assistant turn with tool_calls
        messages.append({
            "role":       "assistant",
            "content":    msg.content or "",
            "tool_calls": [
                {
                    "id":       tc.id,
                    "type":     "function",
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in (msg.tool_calls or [])
            ],
        })

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        for tc in (msg.tool_calls or []):
            inputs     = json.loads(tc.function.arguments)
            print(f"[Scout] ▶ {tc.function.name}({list(inputs.keys())})")
            result_str  = dispatch_tool(tc.function.name, inputs)
            result_json = json.loads(result_str)

            if "error" in result_json:
                failed_tools.append({"tool": tc.function.name, "error": result_json["error"]})
            else:
                all_findings[tc.function.name] = result_json
                _write_latest(map_findings_to_ui(
                    all_findings, client_name, ts,
                    status="scanning",
                    current_node=TOOL_TO_NODE.get(tc.function.name),
                ))

            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      result_str,
            })

        if failed_tools:
            messages.append({
                "role":    "user",
                "content": f"Note: the following tools failed: {json.dumps(failed_tools)}. Mention this in the report.",
            })
            failed_tools = []

    return "Assessment complete.", all_findings


# ── Tool definitions (what Claude sees and can call) ──────────────────────────
TOOLS = [
    {
        "name": "scan_linux_environment",
        "description": "A1 - Linux Fast Track: Scans a Linux host via SSH. Returns OS info, uptime, users, open ports, last patch, last reboot, failed logins. Read-only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "host":     {"type": "string", "description": "IP or hostname"},
                "username": {"type": "string"},
                "key_path": {"type": "string", "description": "Path to SSH private key (optional)"},
                "password": {"type": "string", "description": "SSH password (optional, prefer key)"},
                "port":     {"type": "integer", "description": "SSH port (default 22)"},
            },
            "required": ["host", "username"],
        },
    },
    {
        "name": "check_cis_benchmarks",
        "description": "A2 - Linux Hardening Sprint: Runs CIS Benchmark Level 1 spot checks via SSH. Returns pass/fail per control with remediation steps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "host":     {"type": "string"},
                "username": {"type": "string"},
                "key_path": {"type": "string"},
                "password": {"type": "string"},
                "port":     {"type": "integer", "description": "SSH port (default 22)"},
            },
            "required": ["host", "username"],
        },
    },
    {
        "name": "audit_automation_maturity",
        "description": "A8 - Automation & IaC: Checks what automation tooling is installed (Ansible, Terraform, Puppet, etc). Returns maturity level: LOW/MEDIUM/HIGH.",
        "input_schema": {
            "type": "object",
            "properties": {
                "host":     {"type": "string"},
                "username": {"type": "string"},
                "key_path": {"type": "string"},
                "password": {"type": "string"},
                "port":     {"type": "integer", "description": "SSH port (default 22)"},
            },
            "required": ["host", "username"],
        },
    },
    {
        "name": "scan_vmware_environment",
        "description": "A5 - VMware Cost Optimizer: Connects to vCenter, inventories all VMs, finds powered-off VMs wasting licenses, oversized VMs, snapshots. Estimates dollar savings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "vcenter_host": {"type": "string"},
                "username":     {"type": "string"},
                "password":     {"type": "string"},
            },
            "required": ["vcenter_host", "username", "password"],
        },
    },
    {
        "name": "assess_ai_stack",
        "description": "A7 - AI Stack Assessment: Scans for GPU hardware, CUDA, model serving frameworks (Triton, vLLM, Ollama), vector databases (Chroma, Qdrant, pgvector), ML frameworks (PyTorch, TensorFlow, Transformers), data pipelines, and AI security gaps. Returns readiness rating: NOT_STARTED / EARLY_STAGE / DEVELOPMENT_READY / PRODUCTION_READY.",
        "input_schema": {
            "type": "object",
            "properties": {
                "host":     {"type": "string"},
                "username": {"type": "string"},
                "key_path": {"type": "string"},
                "password": {"type": "string"},
                "port":     {"type": "integer", "description": "SSH port (default 22)"},
            },
            "required": ["host", "username"],
        },
    },
    {
        "name": "scan_windows_environment",
        "description": "A1 — Windows Fast Track: scans a Windows Server via WinRM. Collects OS version, CPU/RAM/disk, uptime, logged users, local admins, open ports, patch status. Read-only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "host":     {"type": "string", "description": "Windows Server hostname or IP"},
                "username": {"type": "string", "description": "Username (DOMAIN\\user or local admin)"},
                "password": {"type": "string", "description": "Password"},
                "port":     {"type": "integer", "description": "WinRM port, default 5985", "default": 5985},
            },
            "required": ["host", "username", "password"],
        },
    },
    {
        "name": "check_windows_security",
        "description": "A2 — Windows Hardening: checks firewall, RDP exposure, Defender, UAC, SMBv1, password policy, failed logins, auto-logon. Returns CIS score and risk level.",
        "input_schema": {
            "type": "object",
            "properties": {
                "host":     {"type": "string", "description": "Windows Server hostname or IP"},
                "username": {"type": "string", "description": "Username"},
                "password": {"type": "string", "description": "Password"},
                "port":     {"type": "integer", "description": "WinRM port, default 5985", "default": 5985},
            },
            "required": ["host", "username", "password"],
        },
    },
    {
        "name": "scan_network_health",
        "description": "A3 - Network Health Check: Discovers live hosts on a subnet, flags risky open ports (Telnet, RDP, MongoDB, Redis etc), measures latency. Returns risk rating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_subnet": {"type": "string", "description": "CIDR notation e.g. 10.0.0.0/24"},
            },
            "required": ["target_subnet"],
        },
    },
    {
        "name": "generate_executive_report",
        "description": "Call this LAST after all scans are done. Synthesizes all findings into a client-ready executive report in Markdown.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name":  {"type": "string"},
                "all_findings": {"type": "object", "description": "All scan results collected so far"},
                "report_focus": {"type": "string", "description": "e.g. cost savings, security hardening, modernization"},
                "report_sections": {
                    "type": "string",
                    "description": (
                        "Required sections the report MUST include in this exact order: "
                        "1. Executive Summary (situation, what we found, top 3 recommendations) | "
                        "2. Server Inventory (hostname, OS, CPU, RAM, disk, role, environment, end-of-support date) | "
                        "3. Risk Map (risk heat map with likelihood/impact rating per finding, risk register table) | "
                        "4. Savings Estimate (annual savings, 3-year TCO comparison, break-even, confidence level) | "
                        "5. License Cost Comparison (current vs Linux/alternative, per-server cost detail) | "
                        "6. Migration Roadmap (30/60/90-day phases, scope per phase, out-of-scope servers, success criteria) | "
                        "Each section must end with: Applicable Everforth Accelerator — e.g. A1, A2, A5."
                    ),
                },
            },
            "required": ["client_name", "all_findings", "report_sections"],
        },
    },
]


TOOL_TO_NODE = {
    "scan_linux_environment":    "Linux Server",
    "check_cis_benchmarks":      "Linux Server",
    "audit_automation_maturity": "Automation",
    "assess_ai_stack":           "AI/ML Stack",
    "scan_network_health":       "Network Scan",
    "scan_vmware_environment":   "VMware Cluster",
    "scan_windows_environment":  "Windows Server",
    "check_windows_security":    "Windows Server",
}


def map_findings_to_ui(all_findings: dict, client_name: str, ts: str,
                        status: str = "complete", current_node: str = None) -> dict:
    """Maps raw tool output to the UI's findings key format."""
    findings, details = {}, {}

    # CIS Benchmarks → linux toggles
    cis      = all_findings.get("check_cis_benchmarks", {})
    controls = {c["control"]: c for c in cis.get("controls", [])}
    toggle_map = {
        "ssh":      "SSH: PermitRootLogin disabled",
        "passauth": "SSH: Password auth disabled",
        "selinux":  "SELinux enforcing",
        "auditd":   "auditd enabled",
    }
    for key, label in toggle_map.items():
        ctrl = controls.get(label, {})
        findings[key] = not ctrl.get("passed", True)
        details[key]  = ctrl.get("remediation", "") if ctrl else ""

    # Linux env → disk, patch
    linux    = all_findings.get("scan_linux_environment", {})
    disk_str = linux.get("disk_usage", "")
    try:
        pct = int(disk_str.split("%")[0].strip().split()[-1])
        findings["disk"] = pct >= 85
    except Exception:
        findings["disk"] = False
    details["disk"]  = disk_str
    last_patch       = linux.get("last_patch", "")
    findings["patch"] = False  # conservative — requires distro-specific date parsing
    details["patch"]  = last_patch or "Unknown"

    # Network risks → port toggles
    net      = all_findings.get("scan_network_health", {})
    risks    = net.get("risks", [])
    port_map = {"mongo": 27017, "redis": 6379, "telnet": 23, "rdp": 3389}
    for key, port in port_map.items():
        hit = next((r for r in risks if r["port"] == port), None)
        findings[key] = bool(hit)
        details[key]  = f"{hit['host']}:{hit['port']} — {hit['label']}" if hit else ""

    # VMware
    vmw = all_findings.get("scan_vmware_environment", {})
    findings["vmsoff"]   = bool(vmw.get("powered_off_vms"))
    findings["oversize"] = bool(vmw.get("oversized_vms"))
    findings["snap"]     = bool(vmw.get("vms_with_snapshots"))
    details["vmsoff"]   = f"{len(vmw.get('powered_off_vms', []))} VMs" if vmw.get("powered_off_vms") else ""
    details["oversize"] = str(vmw.get("oversized_vms", ""))
    details["snap"]     = str(vmw.get("vms_with_snapshots", ""))

    # AI stack
    ai = all_findings.get("assess_ai_stack", {})
    findings["nogpu"]   = not bool(ai.get("gpu"))
    findings["nomodel"] = not bool(ai.get("model_serving"))
    details["nogpu"]    = ai.get("summary", "No GPU detected")
    details["nomodel"]  = str(list(ai.get("model_serving", {}).keys())) if ai.get("model_serving") else "No serving platform found"

    # Automation
    auto  = all_findings.get("audit_automation_maturity", {})
    tools = auto.get("tools_detected", {})
    findings["noansible"] = not bool(tools.get("ansible") or tools.get("terraform") or
                                     tools.get("puppet") or tools.get("chef") or tools.get("salt"))
    findings["nocicd"]    = not (tools.get("jenkins", "") == "active")
    details["noansible"] = f"Detected: {list(tools.keys())}" if tools else "No IaC tools found"
    details["nocicd"]    = f"Jenkins: {tools.get('jenkins', 'not found')}"

    return {
        "scan_id":      f"{client_name.lower().replace(' ', '_')}_{ts}",
        "client":       client_name,
        "scanned_at":   ts,
        "status":       status,
        "current_node": current_node,
        "findings":     findings,
        "details":      details,
        "meta": {
            "host":                linux.get("host", ""),
            "os":                  linux.get("os", ""),
            "cis_score":           cis.get("score", ""),
            "cis_risk":            cis.get("risk_level", ""),
            "network_risk":        net.get("risk_rating", ""),
            "ai_readiness":        ai.get("ai_readiness", ""),
            "automation_maturity": auto.get("maturity_level", ""),
        },
    }


def _write_latest(data: dict) -> None:
    """Atomically write reports/latest.json for the live UI."""
    Path("reports").mkdir(exist_ok=True)
    tmp = Path("reports/latest.json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(Path("reports/latest.json"))


# ── Tool dispatcher ───────────────────────────────────────────────────────────
def dispatch_tool(name: str, inputs: dict) -> str:
    """Routes Claude's tool call to the right Python function."""
    if not request_access(name):
        return json.dumps({"error": f"Gatekeeper blocked: {name}"})
    try:
        if name == "scan_linux_environment":
            result = scan_linux_environment(**inputs)
        elif name == "check_cis_benchmarks":
            result = check_cis_benchmarks(**inputs)
        elif name == "audit_automation_maturity":
            result = audit_automation_maturity(**inputs)
        elif name == "scan_vmware_environment":
            result = scan_vmware_environment(**inputs)
        elif name == "assess_ai_stack":
            result = assess_ai_stack(**inputs)
        elif name == "scan_network_health":
            result = scan_network_health(**inputs)
        elif name == "scan_windows_environment":
            result = scan_windows_environment(**inputs)
        elif name == "check_windows_security":
            result = check_windows_security(**inputs)
        elif name == "generate_executive_report":
            result = {"status": "report_ready", "findings": inputs["all_findings"]}
        else:
            result = {"error": f"Unknown tool: {name}"}
    except Exception as e:
        result = {"error": str(e), "tool": name}

    return json.dumps(result, indent=2)


# ── Agent loop ────────────────────────────────────────────────────────────────
def run_scout(user_request: str, client_name: str = "Client") -> str:
    """
    Main agent loop. Claude decides which tools to call, in what order,
    then synthesizes everything into the executive report.
    """
    claude = get_client()
    model  = MODELS.get(DEPLOY_MODE, MODELS["claude"])

    print(f"[Scout] Mode: {DEPLOY_MODE.upper()} | Model: {model}{' | DEMO' if DEMO_MODE else ''}")

    # OpenAI-compatible backends (venice, ollama) use a separate loop
    if _is_openai_compat(claude):
        system_prompt = f"""You are the AI Infrastructure Scout Agent, built by Everforth (an Apex Systems company).
You are the most advanced infrastructure assessment agent available — designed to replace weeks of manual consulting work with a single automated run.
Today's date: {datetime.now().strftime('%Y-%m-%d')}.
Client: {client_name}

## Your Role
You are a senior infrastructure consultant with deep expertise in Linux, Windows Server, VMware, networking, AI/ML stacks, security hardening, and cost optimization. You think like an engineer but write like a CIO advisor. You find the things clients don't know they should be worried about.

## Assessment Rules
1. Run EVERY tool that applies to the credentials provided. Never skip a tool you have access to.
2. SSH credentials given → always run ALL FOUR: scan_linux_environment + check_cis_benchmarks + audit_automation_maturity + assess_ai_stack
3. WinRM credentials given → always run BOTH: scan_windows_environment + check_windows_security
4. vCenter credentials given → always run scan_vmware_environment
4. Subnet given → always run scan_network_health
5. If multiple hosts are provided, scan each one individually
6. Never assume a finding is minor — let the data speak and rate it objectively

## Reasoning Approach
- After each tool result, briefly analyze what you found before calling the next tool
- Look for correlations across tools: a server with no firewall AND exposed MongoDB AND no auditd is a critical finding, not three separate medium findings
- The savings estimate must use real numbers from the scan — never use placeholder values
- Flag end-of-support OS versions as HIGH risk minimum — they are never LOW

## Report Standards
- Every finding must reference the specific host it came from
- Every risk must have a likelihood score, impact score, and combined rating
- Every dollar figure must have a source and confidence level
- The roadmap must have real 30/60/90-day phases — not vague recommendations
- Executive Summary must be readable by a CIO in under 5 minutes with no technical background
- Each section ends with the applicable Everforth accelerator reference

## What You Never Do
- Never suggest making changes to client systems — assess only
- Never include findings you are not confident about — mark uncertain items as "requires manual verification"
- Never leave a report section empty — if data was not available, explain why
- Never use jargon without defining it on first use
- Never give a LOW risk rating to a server that has not been patched in over 60 days, has root SSH enabled, or has a database port exposed to the network"""
        return _run_openai_loop(claude, model, system_prompt, user_request, client_name)

    system_prompt = f"""You are the AI Infrastructure Scout Agent, built by Everforth (an Apex Systems company).
You are the most advanced infrastructure assessment agent available — designed to replace weeks of manual consulting work with a single automated run.
Today's date: {datetime.now().strftime('%Y-%m-%d')}.
Client: {client_name}

## Your Role
You are a senior infrastructure consultant with deep expertise in Linux, Windows Server, VMware, networking, AI/ML stacks, security hardening, and cost optimization. You think like an engineer but write like a CIO advisor. You find the things clients don't know they should be worried about.

## Assessment Rules
1. Run EVERY tool that applies to the credentials provided. Never skip a tool you have access to.
2. SSH credentials given → always run ALL FOUR: scan_linux_environment + check_cis_benchmarks + audit_automation_maturity + assess_ai_stack
3. WinRM credentials given → always run BOTH: scan_windows_environment + check_windows_security
4. vCenter credentials given → always run scan_vmware_environment
4. Subnet given → always run scan_network_health
5. If multiple hosts are provided, scan each one individually
6. Never assume a finding is minor — let the data speak and rate it objectively

## Reasoning Approach
- After each tool result, briefly analyze what you found before calling the next tool
- Look for correlations across tools: a server with no firewall AND exposed MongoDB AND no auditd is a critical finding, not three separate medium findings
- The savings estimate must use real numbers from the scan — never use placeholder values
- Flag end-of-support OS versions as HIGH risk minimum — they are never LOW

## Report Standards
- Every finding must reference the specific host it came from
- Every risk must have a likelihood score, impact score, and combined rating
- Every dollar figure must have a source and confidence level
- The roadmap must have real 30/60/90-day phases — not vague recommendations
- Executive Summary must be readable by a CIO in under 5 minutes with no technical background
- Each section ends with the applicable Everforth accelerator reference

## What You Never Do
- Never suggest making changes to client systems — assess only
- Never include findings you are not confident about — mark uncertain items as "requires manual verification"
- Never leave a report section empty — if data was not available, explain why
- Never use jargon without defining it on first use
- Never give a LOW risk rating to a server that has not been patched in over 60 days, has root SSH enabled, or has a database port exposed to the network"""

    messages     = [{"role": "user", "content": user_request}]
    all_findings = {}

    print(f"\n[Scout] Starting assessment for: {client_name}")
    print(f"[Scout] {user_request}\n")

    failed_tools = []

    while True:
        response = claude.messages.create(
            model=model,
            max_tokens=8096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        # Print any text Claude outputs mid-loop
        for block in response.content:
            if hasattr(block, "text") and block.text:
                print(block.text)

        if response.stop_reason == "end_turn":
            for block in reversed(response.content):
                if hasattr(block, "text") and len(block.text) > 200:
                    return block.text, all_findings
            return "Assessment complete — no report generated.", all_findings

        if response.stop_reason != "tool_use":
            break

        # Execute each tool Claude requested
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            print(f"[Scout] ▶ {block.name}({list(block.input.keys())})")
            result_str  = dispatch_tool(block.name, block.input)
            result_json = json.loads(result_str)
            if "error" in result_json:
                failed_tools.append({"tool": block.name, "error": result_json["error"]})
            else:
                all_findings[block.name] = result_json
                # Write partial results so the UI can show live progress
                _write_latest(map_findings_to_ui(
                    all_findings, client_name,
                    datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
                    status="scanning",
                    current_node=TOOL_TO_NODE.get(block.name),
                ))

            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": block.id,
                "content":     result_str,
            })

        messages.append({"role": "assistant", "content": response.content})
        # Inject failed tools summary so Claude mentions them in the report
        if failed_tools:
            tool_results.append({
                "type":    "text",
                "text":    f"Note: the following tools failed and could not collect data: {json.dumps(failed_tools)}. Mention this in the report under each affected section.",
            })
        messages.append({"role": "user", "content": tool_results})

    return "Assessment complete.", all_findings


# ── Save report to file ───────────────────────────────────────────────────────
def save_report(report: str, client_name: str, all_findings: dict = None) -> str:
    Path("reports").mkdir(exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = client_name.lower().replace(" ", "_")

    md_path = f"reports/{slug}_{ts}.md"
    with open(md_path, "w") as f:
        f.write(report)
    print(f"\n[Scout] Report saved → {md_path}")

    if all_findings is not None:
        ui_data = map_findings_to_ui(all_findings, client_name, ts, status="complete")
        json_path = f"reports/{slug}_{ts}.json"
        Path(json_path).write_text(json.dumps(ui_data, indent=2))
        _write_latest(ui_data)
        print(f"[Scout] JSON saved   → {json_path}")
        print(f"[Scout] Live UI      → reports/latest.json updated")

    return md_path


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Infrastructure Scout Agent — Everforth")
    parser.add_argument("--client",   default="Client",  help="Client name for the report")
    parser.add_argument("--host",     help="Linux host IP/hostname")
    parser.add_argument("--user",     help="SSH username")
    parser.add_argument("--key",      help="SSH private key path")
    parser.add_argument("--password", help="SSH password (fallback if no key)")
    parser.add_argument("--port",     type=int, default=22, help="SSH port (default 22)")
    parser.add_argument("--vcenter",  help="vCenter hostname")
    parser.add_argument("--vc-user",  help="vCenter username")
    parser.add_argument("--vc-pass",  help="vCenter password")
    parser.add_argument("--windows",  metavar="HOST", help="Windows Server host to scan via WinRM")
    parser.add_argument("--win-user", metavar="USERNAME", help="Windows username (domain\\user or local)")
    parser.add_argument("--win-pass", metavar="PASSWORD", help="Windows password")
    parser.add_argument("--win-port", metavar="PORT", type=int, default=5985, help="WinRM port (default 5985)")
    parser.add_argument("--subnet",   help="Network subnet e.g. 10.0.0.0/24")
    parser.add_argument("--demo",     action="store_true", help="Run with mock data — no real infra needed")
    args = parser.parse_args()

    if args.demo:
        os.environ["DEMO_MODE"] = "true"

    parts = []
    if args.host:
        creds = f"SSH user={args.user} port={args.port}"
        if args.key:        creds += f" key={args.key}"
        elif args.password: creds += f" password={args.password}"
        parts.append(f"Scan Linux host {args.host} ({creds}). Run linux assessment, CIS benchmarks, automation audit, and AI stack assessment.")
    if args.windows:
        parts.append(f"Scan Windows Server {args.windows} via WinRM (user={args.win_user} password={args.win_pass} port={args.win_port}). Run Windows environment scan and Windows security hardening check.")
    if args.vcenter:
        parts.append(f"Scan VMware vCenter at {args.vcenter} user={args.vc_user} password={args.vc_pass}.")
    if args.subnet:
        parts.append(f"Run network health check on subnet {args.subnet}.")
    if not parts:
        if DEMO_MODE:
            parts.append("Scan Linux host 10.0.0.10 (SSH user=demo password=demo). Run linux assessment, CIS benchmarks, automation audit, and AI stack assessment.")
            parts.append("Scan VMware vCenter at vcenter.demo.local user=administrator@vsphere.local password=Demo1234!.")
            parts.append("Run network health check on subnet 10.0.0.0/24.")
        else:
            parts.append("Run a full infrastructure assessment using all available tools.")

    parts.append("After all scans, generate the full executive report.")
    request = " ".join(parts)

    report, findings = run_scout(request, client_name=args.client)
    save_report(report, args.client, findings)
