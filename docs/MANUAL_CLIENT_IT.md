# ScoutAgent 2.0 — Client IT Team Manual

**Everforth (an Apex Systems company) | Infrastructure Practice**
**Document Classification: Client Confidential**

---

## Table of Contents

1. [What ScoutAgent Does](#1-what-scoutagent-does)
2. [Prerequisites](#2-prerequisites)
3. [Installation](#3-installation)
4. [Configuration](#4-configuration)
5. [Running Scans](#5-running-scans)
6. [Understanding the Report](#6-understanding-the-report)
7. [Deployment Modes](#7-deployment-modes)
8. [Troubleshooting](#8-troubleshooting)
9. [FAQ](#9-faq)

---

## 1. What ScoutAgent Does

ScoutAgent 2.0 is an AI-powered, read-only infrastructure assessment tool built by Everforth. It connects to your Linux servers via SSH, your VMware vCenter via the vSphere API, and your network via passive nmap scans. It collects configuration data, security posture metrics, and resource utilization — then passes all findings to an AI reasoning engine (Claude, AWS Bedrock, a local Ollama model, or Venice AI via Agent Zero) to synthesize them into a structured executive report.

No changes are ever made to any system ScoutAgent touches. Every operation is strictly read-only: it runs shell commands via SSH, reads vCenter API responses over HTTPS, and performs host-discovery and port scans with nmap. The output is a single Markdown report covering six sections: Executive Summary, Server Inventory, Risk Map, Savings Estimate, License Cost Comparison, and Migration Roadmap. The entire assessment typically completes in 3 to 8 minutes depending on environment size and network latency.

---

## 2. Prerequisites

### Software Requirements

| Requirement | Minimum Version | Notes |
|---|---|---|
| Python | 3.12+ | 3.12 strongly recommended |
| nmap | 7.80+ | Must be on system PATH |
| pip | 23.0+ | Bundled with Python 3.12 |
| Docker | 24.0+ | Required for Docker install path only |
| Docker Compose | 2.20+ | Required for Docker install path only |

### Network / Access Requirements

- **SSH access** to target Linux hosts: TCP 22, key-based or password auth
- **vCenter access** (if scanning VMware): HTTPS port 443 to vCenter server, read-only credentials
- **Network scan access**: The host running ScoutAgent must be able to reach the target subnet for nmap discovery
- **Outbound HTTPS** (port 443): Required for `DEPLOY_MODE=claude`, `DEPLOY_MODE=bedrock`, and `DEPLOY_MODE=venice`. Not required for `DEPLOY_MODE=ollama`

### Credentials Required

| Credential | When Needed | Minimum Permission Level |
|---|---|---|
| ANTHROPIC_API_KEY | DEPLOY_MODE=claude | Valid Anthropic API key |
| AWS credentials | DEPLOY_MODE=bedrock | IAM: `bedrock:InvokeModel` on Claude model |
| Ollama endpoint | DEPLOY_MODE=ollama | HTTP reachable from scan host |
| VENICE_API_KEY | DEPLOY_MODE=venice | Agent Zero API key (sk-a0-...) |
| SSH username + key | Linux scans | Read-only user, no sudo required |
| vCenter credentials | VMware scans | Read-only role on vCenter |

> **Security note:** SSH key-based authentication is strongly preferred over passwords. Never store credentials in the ScoutAgent codebase. All credentials are passed via environment variables.

---

## 3. Installation

### Option A — pip Direct Install (development / evaluation)

```bash
# Clone the repository
git clone https://github.com/everforth/scoutagent2.git
cd ScoutAgent2.0

# Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate          # Linux/macOS
.venv\Scripts\activate             # Windows

# Install dependencies
pip install -r requirements.txt

# Install nmap (if not already installed)
# Ubuntu/Debian:
sudo apt-get install -y nmap
# RHEL/Rocky/AlmaLinux:
sudo dnf install -y nmap

# Copy and edit the environment file
cp .env.example .env
nano .env
```

### Option B — Docker (Recommended for Client Engagements)

Docker is the recommended deployment method for client engagements. It eliminates dependency conflicts, bundles nmap, and provides a consistent environment regardless of the host OS.

```bash
# Clone the repository
git clone https://github.com/everforth/scoutagent2.git
cd ScoutAgent2.0

# Copy and edit the environment file
cp .env.example .env
nano .env

# Build and start
docker compose up -d

# Run a demo scan to verify the container is working
docker compose exec scoutagent python3 agent.py --demo
```

The Docker image includes nmap, Python 3.12, and all Python dependencies. Your `.env` file is mounted into the container at runtime — credentials are never baked into the image.

**Mapping SSH keys into Docker:**

If you are scanning real hosts with SSH key authentication, mount the key directory:

```yaml
# In docker-compose.yml, under the scoutagent service volumes:
volumes:
  - ./.env:/app/.env
  - ~/.ssh:/root/.ssh:ro        # Mount SSH keys read-only
  - ./reports:/app/reports      # Persist reports outside container
```

### Option C — Existing Everforth Deployment

If your engagement is being delivered by an Everforth consultant, ScoutAgent is already deployed on a dedicated assessment server. Your Everforth contact will provide:

- The server IP / hostname
- VPN access instructions (if required)
- The UI URL (default: `http://<server>:7070`)
- The `.env` pre-configured for your environment

In this case, you do not need to install anything. You only need to provide SSH credentials and vCenter credentials to your Everforth consultant, who will populate the `.env` and run the assessment.

---

## 4. Configuration

All configuration is done through the `.env` file. Copy `.env.example` to `.env` and edit the values for your environment.

### Variable Reference

---

#### `DEPLOY_MODE`

**Required.** Controls which AI backend processes the scan findings.

| Value | Description |
|---|---|
| `claude` | Anthropic API (default). Fast, requires internet access and an Anthropic API key. |
| `bedrock` | AWS Bedrock. Data stays within the client AWS account. Requires AWS IAM credentials with Bedrock permissions. |
| `ollama` | Local Ollama server. Fully air-gapped. No data leaves the facility. Requires a GPU server running Ollama. |
| `venice` | Venice AI via Agent Zero. OpenAI-compatible cloud API running open-source models (Llama, Mistral, etc.). Requires an Agent Zero API key. No Anthropic account needed. |

```
DEPLOY_MODE=claude
```

---

#### `DEMO_MODE`

**Optional.** When set to `true`, ScoutAgent runs with synthetic mock data — no real infrastructure connections are made. Use this to validate your installation, practice with the tool, or prepare for client demos.

```
DEMO_MODE=false
```

> Set to `true` for initial testing. Switch to `false` before real assessments.

---

#### `ANTHROPIC_API_KEY`

**Required when `DEPLOY_MODE=claude`.** Your Anthropic API key.

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

Obtain from: [console.anthropic.com](https://console.anthropic.com) → API Keys

---

#### `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION`

**Required when `DEPLOY_MODE=bedrock`.** IAM credentials for an account that has AWS Bedrock enabled with Claude access.

```
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
```

The IAM user or role must have the `bedrock:InvokeModel` permission on the Claude model ARN for your chosen region. Claude on Bedrock is an official Anthropic + AWS partnership. Your data never leaves your AWS account.

---

#### `OLLAMA_BASE_URL`

**Required when `DEPLOY_MODE=ollama`.** The base URL of your Ollama server's OpenAI-compatible API endpoint.

```
OLLAMA_BASE_URL=http://gpu-server.internal:11434/v1
```

The Ollama server must be reachable from the ScoutAgent host. The `/v1` suffix is required — Ollama exposes an OpenAI-compatible API at this path.

---

#### `OLLAMA_MODEL`

**Required when `DEPLOY_MODE=ollama`.** The name of the model loaded in Ollama to use for reasoning.

```
OLLAMA_MODEL=llama3
```

Recommended minimum: Llama 3 8B on a GPU with at least 24 GB VRAM (e.g., NVIDIA A10). Larger models (70B) produce better report quality but require significantly more VRAM and run slower.

---

#### `VENICE_API_KEY`

**Required when `DEPLOY_MODE=venice`.** Your Agent Zero API key for the Venice AI platform.

```
VENICE_API_KEY=sk-a0-...
```

Obtain from your Agent Zero account at [agent-zero.ai](https://www.agent-zero.ai). Venice AI exposes an OpenAI-compatible endpoint and does not require an Anthropic account.

---

#### `VENICE_MODEL`

**Optional when `DEPLOY_MODE=venice`.** The Venice model to use. Defaults to `llama-3.3-70b`.

```
VENICE_MODEL=llama-3.3-70b
```

Other available Venice models include Mistral, Qwen3, DeepSeek, and others. See Venice documentation for the current model list.

---

### Complete `.env` Example

```bash
# Deploy mode: claude | bedrock | ollama | venice
DEPLOY_MODE=claude

# Set true for demos and testing — no real infrastructure needed
DEMO_MODE=false

# Anthropic API (required for claude mode)
ANTHROPIC_API_KEY=sk-ant-api03-...

# AWS Bedrock (required for bedrock mode)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Ollama (required for ollama mode)
OLLAMA_BASE_URL=http://gpu-server.internal:11434/v1
OLLAMA_MODEL=llama3

# Venice AI via Agent Zero (required for venice mode)
VENICE_API_KEY=sk-a0-...
VENICE_MODEL=llama-3.3-70b
```

---

## 5. Running Scans

ScoutAgent is invoked via `agent.py`. All scan targets and credentials are passed as command-line arguments.

### Demo Mode (No Infrastructure Required)

Use this to validate your installation and familiarize yourself with the report format. No credentials required.

```bash
python3 agent.py --demo
```

Or with Docker:

```bash
docker compose exec scoutagent python3 agent.py --demo
```

Output: `reports/demo_<timestamp>.md`

---

### Linux-Only Scan

Scans one or more Linux hosts via SSH. Runs `scan_linux_environment`, `check_cis_benchmarks`, and `audit_automation_maturity`.

```bash
python3 agent.py \
  --client "Acme Corporation" \
  --ssh-host 10.10.0.5 \
  --ssh-user admin \
  --ssh-key ~/.ssh/id_rsa
```

**Using password authentication (less preferred):**

```bash
python3 agent.py \
  --client "Acme Corporation" \
  --ssh-host 10.10.0.5 \
  --ssh-user admin \
  --ssh-password "your-password"
```

---

### VMware-Only Scan

Scans a vCenter instance. Runs `scan_vmware_environment`.

```bash
python3 agent.py \
  --client "Acme Corporation" \
  --vcenter-host vc.acme.local \
  --vcenter-user readonly@vsphere.local \
  --vcenter-password "your-password"
```

---

### Network-Only Scan

Scans a subnet with nmap. Runs `scan_network_health`.

```bash
python3 agent.py \
  --client "Acme Corporation" \
  --network 10.10.0.0/24
```

> nmap must be installed and on the system PATH. On Linux you may need to run as root or with `sudo` for certain scan types.

---

### Full Scan (All Three Modules)

Pass all credential sets to run Linux, VMware, and network scans in a single assessment.

```bash
python3 agent.py \
  --client "Acme Corporation" \
  --ssh-host 10.10.0.5 \
  --ssh-user admin \
  --ssh-key ~/.ssh/id_rsa \
  --vcenter-host vc.acme.local \
  --vcenter-user readonly@vsphere.local \
  --vcenter-password "your-password" \
  --network 10.10.0.0/24
```

The agent reasons about which tools to call based on the credentials provided. If SSH credentials are supplied, it will always run all three SSH-based tools (linux scan, CIS benchmarks, automation audit). If vCenter credentials are supplied, it runs the VMware scan. If a network target is supplied, it runs the network scan.

Reports are written to `reports/<client>_<timestamp>.md` and `reports/latest.json` (for the UI).

---

## 6. Understanding the Report

The report always contains six sections in this order. Here is what each section tells you and who it is written for.

---

### Section 1 — Executive Summary

**Audience:** CIO, VP Infrastructure, project sponsor

**What it contains:** A two-page maximum summary of the entire assessment. It leads with risk and money, not technology. Page 1 covers what was found (estate overview, top risks, savings identified). Page 2 covers the top three recommendations with effort estimates, business impact explanations, and the Everforth accelerator that delivers each recommendation.

**What to look for:** The overall risk rating (CRITICAL / HIGH / MEDIUM / LOW) and the top three priorities. These three priorities are the core deliverable — everything else in the report is evidence supporting them.

---

### Section 2 — Server Inventory

**Audience:** IT Manager, Systems Administrator, Architect

**What it contains:** A complete asset register of every host the agent scanned. For Linux hosts: hostname, IP, OS version, end-of-support date, CPU, RAM, disk usage, uptime, last reboot, last patch date, failed login count, open ports, and detected automation tools.

**What to look for:** Flagged cells. The agent auto-flags: patch gaps >60 days (PATCH GAP), reboots >90 days (STABILITY RISK), disk usage >80% (CAPACITY RISK), failed logins >50 (BRUTE FORCE INDICATOR), and OS within 12 months of end-of-support (EOL RISK). Any flag in this table is a specific action item.

---

### Section 3 — Risk Map

**Audience:** CISO, Security Lead, IT Manager

**What it contains:** A risk register listing every security finding with Likelihood (1–5), Impact (1–5), Score (product of the two), and Rating (CRITICAL/HIGH/MEDIUM/LOW). Each finding names the specific host, the specific control that failed, and the remediation action.

**What to look for:** Anything rated CRITICAL (score 20–25) or HIGH (score 12–19). These are the findings that need a scheduled remediation window, not a backlog ticket. Pay particular attention to finding combinations — for example, root SSH enabled plus auditd disabled on the same host is more dangerous than either finding alone.

---

### Section 4 — Savings Estimate

**Audience:** CFO, Procurement, IT Budget Owner

**What it contains:** Three savings scenarios (conservative, moderate, aggressive), each with an annual figure, the source of the savings, and a confidence level. Also includes a 3-year projection table.

**What to look for:** The confidence level declaration. HIGH confidence means the agent had complete data (full vCenter access, accurate license counts). MEDIUM means some data was estimated. LOW means the scan covered a partial sample. Use the confidence level to calibrate how you present these numbers to finance stakeholders.

---

### Section 5 — License Cost Comparison

**Audience:** Procurement, Finance, IT Manager

**What it contains:** A per-VM breakdown of powered-off VMs consuming licenses (candidates for decommission) and oversized VMs (candidates for rightsizing). Each row shows current cost, recommended action, and estimated annual savings.

**What to look for:** The immediate recovery number — powered-off VMs and clearly oversized VMs often represent savings that can be captured with zero risk and zero migration effort. These are the fastest wins to bring to a budget conversation.

---

### Section 6 — Migration Roadmap

**Audience:** IT Manager, Project Manager, Technical Lead

**What it contains:** A three-phase 90-day plan. Phase 1 (Days 1–30): security hardening and quick wins. Phase 2 (Days 31–60): patching, monitoring, and network cleanup. Phase 3 (Days 61–90): VM rightsizing and Linux migration pilot. Each phase lists specific servers in scope, step-by-step activities, hour estimates, prerequisites, and measurable success criteria.

**What to look for:** The out-of-scope table at the end of the roadmap. Servers listed there have a documented reason they cannot be migrated yet (vendor dependency, AD integration, etc.) along with the trigger condition that would allow them to be addressed. This table is important for planning purposes — it shows what the roadmap intentionally excludes and why.

---

## 7. Deployment Modes

ScoutAgent supports four AI backends, selected via the `DEPLOY_MODE` environment variable. The mode controls only how findings are processed by the AI — the scanning tools (SSH, vCenter, nmap) behave identically in all modes.

---

### Claude API (`DEPLOY_MODE=claude`)

**How it works:** Scan findings are sent to Anthropic's Claude API over HTTPS. Claude reasons about the findings and generates the report. The API call is encrypted in transit (TLS 1.3).

**Data handling:** Your infrastructure data is sent to Anthropic's infrastructure for processing. Anthropic's data handling policy applies. Scan data is not used for model training under the default API terms.

**When to use:** Standard commercial engagements where the client has no specific data residency requirements. Fastest mode, best report quality.

**Requirements:** `ANTHROPIC_API_KEY` set. Outbound HTTPS on port 443 to `api.anthropic.com`.

---

### AWS Bedrock (`DEPLOY_MODE=bedrock`)

**How it works:** Scan findings are sent to the Claude model hosted on AWS Bedrock within the client's AWS account. The API call stays within AWS infrastructure.

**Data handling:** Data never leaves the client's AWS account. AWS Bedrock does not use customer prompts for model training. This is the correct mode for clients with HIPAA, SOC 2, FedRAMP, or other compliance requirements. It is also appropriate for any client whose legal or security policy prohibits sending infrastructure data to third-party APIs.

**When to use:** Regulated industries (healthcare, finance, government). Clients with explicit data residency requirements. Engagements where a DPA with Anthropic has not been executed.

**Requirements:** AWS account with Bedrock enabled in the target region. Claude model access granted in Bedrock (requires requesting access in the AWS console). IAM credentials with `bedrock:InvokeModel` permission.

```bash
DEPLOY_MODE=bedrock
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```

---

### Ollama / Air-Gap (`DEPLOY_MODE=ollama`)

**How it works:** Scan findings are sent to a locally-hosted LLM server running Ollama. No data leaves the physical facility.

**Data handling:** Zero data leaves the facility. Appropriate for government, defense, classified environments, or any air-gapped network where outbound internet connectivity is not available.

**When to use:** Air-gapped networks. Government and defense clients. Any environment where outbound internet is prohibited or unavailable.

**Requirements:** A GPU server running Ollama with a compatible model loaded. ScoutAgent must have network access to the Ollama server. Minimum recommended hardware: NVIDIA A10 or equivalent, 24 GB VRAM, Llama 3 8B model.

```bash
DEPLOY_MODE=ollama
OLLAMA_BASE_URL=http://gpu-server.internal:11434/v1
OLLAMA_MODEL=llama3
```

> **Report quality note:** Open-source models available via Ollama produce adequate reports but will not match the synthesis quality of Claude via the API or Bedrock. For air-gapped deployments, Llama 3 70B (requires ~80 GB VRAM) produces significantly better output than the 8B variant.

---

### Venice AI / Agent Zero (`DEPLOY_MODE=venice`)

**How it works:** Scan findings are sent to the Venice AI platform via your Agent Zero API key. Venice exposes an OpenAI-compatible API and runs a variety of open-source models (Llama, Mistral, Qwen, DeepSeek, and others).

**Data handling:** Your infrastructure data is sent to Venice AI's infrastructure for processing. Venice AI's privacy and data handling policy applies. This mode does not require an Anthropic account.

**When to use:** When you have an Agent Zero subscription and prefer to use open-source models, or when an Anthropic account is not available.

**Requirements:** `VENICE_API_KEY` set (Agent Zero key). Outbound HTTPS on port 443 to `api.venice.ai`.

```bash
DEPLOY_MODE=venice
VENICE_API_KEY=sk-a0-...
VENICE_MODEL=llama-3.3-70b
```

> **Report quality note:** Open-source models via Venice produce good results but the synthesis quality may differ from Claude. Larger models (e.g., Llama 3 70B) produce better output than smaller variants.

---

## 8. Troubleshooting

### SSH Authentication Failure

**Symptom:** `scan_linux_environment` returns `Authentication failed` or `No existing session`

**Checklist:**
1. Verify the SSH host is reachable: `ssh -i ~/.ssh/id_rsa admin@10.10.0.5`
2. Check that the key file has correct permissions: `chmod 600 ~/.ssh/id_rsa`
3. Confirm the username matches an account on the target host
4. If using password auth, ensure `PasswordAuthentication yes` is set in the target's `sshd_config`
5. Check that TCP 22 is not blocked by a firewall between the ScoutAgent host and the target
6. If the target uses a non-standard SSH port, pass `--ssh-port <port>`

### vCenter SSL Certificate Errors

**Symptom:** `scan_vmware_environment` fails with `SSL: CERTIFICATE_VERIFY_FAILED` or `SSLError`

**Cause:** vCenter is using a self-signed certificate (common in lab and smaller environments).

**Fix:** Set `VCENTER_DISABLE_SSL_VERIFY=true` in your `.env` file. This disables SSL certificate verification for the vCenter connection only. Use this only in controlled environments — do not disable SSL verification when connecting through untrusted networks.

```
VCENTER_DISABLE_SSL_VERIFY=true
```

Alternatively, add the vCenter CA certificate to the system trust store and restart ScoutAgent.

### nmap Not Found

**Symptom:** `scan_network_health` fails with `nmap: command not found` or `FileNotFoundError: [Errno 2] No such file or directory: 'nmap'`

**Fix:**
```bash
# Ubuntu/Debian
sudo apt-get install -y nmap

# RHEL/Rocky/AlmaLinux
sudo dnf install -y nmap

# macOS
brew install nmap
```

After installing, verify nmap is on the PATH: `which nmap` and `nmap --version`.

If running via Docker, nmap is bundled in the image. This error when using Docker indicates a custom image build that skipped the nmap installation step.

### API Key Issues

**Symptom:** Agent fails with `AuthenticationError`, `Invalid API key`, or `401 Unauthorized`

**Checklist:**
1. Confirm the API key in `.env` starts with `sk-ant-` (Anthropic) or `sk-a0-` (Venice/Agent Zero), or that AWS credentials are valid
2. Check for leading/trailing whitespace in the key value in `.env`
3. For Anthropic: verify the key is active at [console.anthropic.com](https://console.anthropic.com)
4. For Bedrock: verify the IAM user has `bedrock:InvokeModel` permission and that Claude is enabled in your Bedrock region
5. For Venice: verify the Agent Zero key is active in your Agent Zero dashboard
6. Ensure `DEPLOY_MODE` matches the credentials provided (e.g., do not set `DEPLOY_MODE=venice` while only providing `ANTHROPIC_API_KEY`)

### Scan Runs But Report Is Empty or Truncated

**Symptom:** The report file exists but is very short, missing sections, or contains only partial content.

**Likely cause:** The AI model hit a token limit or the API call timed out.

**Fix for claude mode:** Check your Anthropic account has sufficient credits and rate limits for your tier.

**Fix for ollama mode:** The model may have run out of context window. Try a larger model variant (e.g., switch from `llama3:8b` to `llama3:70b` if VRAM permits) or ensure no other processes are competing for GPU memory.

### No Data in UI (`/api/latest` returns 404)

**Symptom:** The ScoutAgent UI shows "No scan results yet."

**Cause:** No scan has been completed yet, or the `reports/latest.json` file was deleted.

**Fix:** Run a scan (including `--demo` for testing). The UI polls `/api/latest` every 4 seconds and will update automatically once a scan completes.

---

## 9. FAQ

**Q: Does ScoutAgent make any changes to the systems it scans?**
A: No. Every operation is strictly read-only. ScoutAgent runs shell commands via SSH that only read data (no writes, no installs, no config changes), queries the vCenter API with read-only credentials, and performs passive nmap scans. Nothing is modified on any scanned system.

**Q: What data does ScoutAgent collect and where does it go?**
A: ScoutAgent collects system configuration data (OS version, patch level, open ports, CIS benchmark results, VM inventory). In `claude` mode this data is sent to Anthropic's API. In `bedrock` mode it stays in your AWS account. In `ollama` mode it never leaves your network. In `venice` mode it is sent to Venice AI's infrastructure via your Agent Zero key. No credentials or private keys are ever collected — only the metadata about the configuration state of your servers.

**Q: How long does a full scan take?**
A: A typical full scan (1–3 Linux hosts, one vCenter with 50 VMs, and a /24 network) takes 3–8 minutes. Network scan time scales with the number of live hosts discovered (capped at 20 hosts for the risky port check). Large vCenter environments (500+ VMs) may take slightly longer on the vSphere API queries.

**Q: Can ScoutAgent scan Windows servers?**
A: The current version focuses on Linux/VMware environments. Windows server scanning (WinRM, PowerShell Remoting) is on the roadmap. For Windows environments, the VMware and network scan modules still apply and will inventory Windows VMs through vCenter.

**Q: What happens if one scan module fails (e.g., SSH times out)?**
A: The agent captures the error in a `failed_tools` field and continues with the remaining modules. The final report includes a note stating which tools could not connect and the reason. A partial report is always better than no report.

**Q: Can I run multiple scans in sequence and compare reports?**
A: Yes. Each scan produces a timestamped report file in `reports/`. The UI's `/api/scans` endpoint lists all completed reports. The `latest.json` file always reflects the most recent completed scan. Future versions will include a diff/comparison view.

**Q: What is the minimum access level required on vCenter?**
A: A read-only role at the vCenter level (not just datacenter level). The account needs permission to enumerate VMs, read resource usage statistics, and read power state. No admin or write permissions are required.

**Q: Can I run ScoutAgent on a Windows host?**
A: Yes, with Python 3.12 installed. nmap must be installed separately from [nmap.org](https://nmap.org). SSH key handling works on Windows via the `paramiko` library. Docker Desktop on Windows is also a supported path.

---

*Everforth Infrastructure Practice | An Apex Systems Company*
*ScoutAgent 2.0 | Client IT Team Manual | Confidential*
