#!/usr/bin/env python3
"""
AI Infrastructure Scout Agent
==============================
Powered by Claude. Covers accelerators A1, A2, A3, A5, A7, A8.
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
from datetime import datetime
from pathlib import Path

import anthropic

from tools.linux_scout    import scan_linux_environment, check_cis_benchmarks, audit_automation_maturity
from tools.vmware_scout   import scan_vmware_environment
from tools.network_scout  import scan_network_health
from tools.ai_stack_scout import assess_ai_stack

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

if DEMO_MODE:
    from tools.mock_tools import (
        mock_scan_linux_environment    as scan_linux_environment,
        mock_check_cis_benchmarks      as check_cis_benchmarks,
        mock_audit_automation_maturity as audit_automation_maturity,
        mock_scan_vmware_environment   as scan_vmware_environment,
        mock_scan_network_health       as scan_network_health,
        mock_assess_ai_stack           as assess_ai_stack,
    )

# ── Model config ──────────────────────────────────────────────────────────────
# DEPLOY_MODE controls which backend Claude runs on:
#   "claude"  → direct Anthropic API  (fast, default, data touches Anthropic)
#   "bedrock" → AWS Bedrock           (stays in client AWS account, compliance-friendly)
#   "ollama"  → local Ollama server   (air-gap / fully on-prem, needs GPU)
DEPLOY_MODE = os.getenv("DEPLOY_MODE", "claude").lower()

# Model IDs per backend
MODELS = {
    "claude":  "claude-opus-4-6",
    "bedrock": "anthropic.claude-opus-4-5",         # Bedrock model ID format
    "ollama":  os.getenv("OLLAMA_MODEL", "llama3"),  # configurable local model
}


def get_client():
    """Returns the right Claude client based on DEPLOY_MODE."""
    if DEPLOY_MODE == "bedrock":
        return anthropic.AnthropicBedrock(
            aws_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
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
    else:
        return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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
            },
            "required": ["host", "username"],
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
                        "Each section must end with: Applicable Apex Accelerator — e.g. A1, A2, A5."
                    ),
                },
            },
            "required": ["client_name", "all_findings", "report_sections"],
        },
    },
]


# ── Tool dispatcher ───────────────────────────────────────────────────────────
def dispatch_tool(name: str, inputs: dict) -> str:
    """Routes Claude's tool call to the right Python function."""
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

    system_prompt = f"""You are the AI Infrastructure Scout Agent, built by Apex Systems Infrastructure Practice.
You are the most advanced infrastructure assessment agent available — designed to replace weeks of manual consulting work with a single automated run.
Today's date: {datetime.now().strftime('%Y-%m-%d')}.
Client: {client_name}

## Your Role
You are a senior infrastructure consultant with deep expertise in Linux, VMware, networking, AI/ML stacks, security hardening, and cost optimization. You think like an engineer but write like a CIO advisor. You find the things clients don't know they should be worried about.

## Assessment Rules
1. Run EVERY tool that applies to the credentials provided. Never skip a tool you have access to.
2. SSH credentials given → always run ALL THREE: scan_linux_environment + check_cis_benchmarks + audit_automation_maturity + assess_ai_stack
3. vCenter credentials given → always run scan_vmware_environment
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
- Each section ends with the applicable Apex accelerator reference

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
                    return block.text
            return "Assessment complete — no report generated."

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

    return "Assessment complete."


# ── Save report to file ───────────────────────────────────────────────────────
def save_report(report: str, client_name: str) -> str:
    Path("reports").mkdir(exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = client_name.lower().replace(" ", "_")
    path = f"reports/{slug}_{ts}.md"
    with open(path, "w") as f:
        f.write(report)
    print(f"\n[Scout] Report saved → {path}")
    return path


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Infrastructure Scout Agent — Apex Systems")
    parser.add_argument("--client",   default="Client",  help="Client name for the report")
    parser.add_argument("--host",     help="Linux host IP/hostname")
    parser.add_argument("--user",     help="SSH username")
    parser.add_argument("--key",      help="SSH private key path")
    parser.add_argument("--password", help="SSH password")
    parser.add_argument("--vcenter",  help="vCenter hostname")
    parser.add_argument("--vc-user",  help="vCenter username")
    parser.add_argument("--vc-pass",  help="vCenter password")
    parser.add_argument("--subnet",   help="Network subnet e.g. 10.0.0.0/24")
    parser.add_argument("--demo",     action="store_true", help="Run with mock data — no real infra needed")
    args = parser.parse_args()

    if args.demo:
        os.environ["DEMO_MODE"] = "true"

    parts = []
    if args.host:
        creds = f"SSH user={args.user}"
        if args.key:      creds += f" key={args.key}"
        elif args.password: creds += f" password={args.password}"
        parts.append(f"Scan Linux host {args.host} ({creds}). Run linux assessment, CIS benchmarks, and automation audit.")
    if args.vcenter:
        parts.append(f"Scan VMware vCenter at {args.vcenter} user={args.vc_user} password={args.vc_pass}.")
    if args.subnet:
        parts.append(f"Run network health check on subnet {args.subnet}.")
    if not parts:
        parts.append("Run a full infrastructure assessment using all available tools.")

    parts.append("After all scans, generate the full executive report.")
    request = " ".join(parts)

    report = run_scout(request, client_name=args.client)
    save_report(report, args.client)
