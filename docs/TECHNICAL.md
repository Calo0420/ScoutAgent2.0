# AI Infrastructure Scout Agent — Technical Reference
**Apex Systems | Infrastructure Practice | Internal Use Only**

---

## Overview

The Scout Agent is a Claude-powered autonomous agent that performs read-only infrastructure assessments and generates structured executive reports. It uses Claude's native tool-use capability to decide which scans to run, execute them in the right order, and synthesize all findings into a standardized deliverable.

---

## Architecture

```
CLI / API request
       ↓
  agent.py — run_scout()
       ↓
  Claude (brain) — reasons about what tools to call
       ├── scan_linux_environment()    SSH read-only
       ├── check_cis_benchmarks()      SSH read-only
       ├── audit_automation_maturity() SSH read-only
       ├── scan_vmware_environment()   pyVmomi read-only
       └── scan_network_health()       nmap passive
       ↓
  generate_executive_report()
       ↓
  reports/<client>_<timestamp>.md
```

Claude acts as the routing brain. It receives the user request, decides which tools are applicable based on what credentials were provided, calls them in sequence, accumulates findings, and then generates the structured report. No hardcoded scan order — the agent reasons about it.

---

## Deployment Modes

Controlled by the `DEPLOY_MODE` environment variable.

| Mode | Backend | Data leaves client? | Speed | Use case |
|---|---|---|---|---|
| `claude` | Anthropic API | Yes — encrypted, Anthropic policy | Fast | Standard commercial clients |
| `bedrock` | AWS Bedrock | No — stays in client AWS account | Fast | Regulated clients, HIPAA/SOC2 |
| `ollama` | Local LLM server | Never | Slow (GPU required) | Air-gap, government, classified |

### Claude (default)
```bash
DEPLOY_MODE=claude
ANTHROPIC_API_KEY=sk-ant-...
```

### AWS Bedrock
```bash
DEPLOY_MODE=bedrock
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```
Client must have Claude enabled in their Bedrock console. Claude on Bedrock is an official Anthropic/AWS partnership. Data stays within the client's AWS VPC.

### Ollama (air-gap)
```bash
DEPLOY_MODE=ollama
OLLAMA_BASE_URL=http://gpu-server.internal:11434/v1
OLLAMA_MODEL=llama3
```
Requires a GPU server running Ollama with a compatible model loaded. Recommended minimum: NVIDIA A10 or equivalent, 24GB VRAM for Llama 3 8B at acceptable speed.

---

## System Prompt

The agent is initialized with this system prompt on every run:

```
You are the AI Infrastructure Scout Agent built by Apex Systems.
You have access to read-only scanning tools that assess client infrastructure.

Your job:
1. Run ALL appropriate scans based on the credentials provided.
2. If SSH creds are given: always run scan_linux_environment,
   check_cis_benchmarks, AND audit_automation_maturity.
3. After all scans complete, call generate_executive_report
   with ALL findings combined.
4. The report_sections field defines the exact structure —
   follow it without skipping any section.
5. Be conservative — report only, never suggest making changes
   without approval.
```

The client name is injected at runtime. The date is injected to ensure roadmap timelines are accurate.

---

## Tool Definitions

### scan_linux_environment
**Accelerator:** A1 — Linux Fast Track
**Transport:** SSH (paramiko)
**Access level:** Read-only shell commands

Collects:
- OS name, kernel version
- CPU cores, RAM (GB), disk usage
- System uptime, last reboot time
- Last patch installed
- Currently logged-in users
- Last 5 login events (with timestamps)
- Open listening ports
- Installed package count
- Failed login attempts (auth.log / secure)
- Active cron jobs count

**Required inputs:** `host`, `username`
**Optional inputs:** `key_path` (preferred), `password`

---

### check_cis_benchmarks
**Accelerator:** A2 — Linux Hardening Sprint
**Transport:** SSH (paramiko)
**Access level:** Read-only shell commands

Runs 10 CIS Benchmark Level 1 spot checks:

| Control | Check | Remediation if failed |
|---|---|---|
| SSH PermitRootLogin | Must be `no` | Set in sshd_config |
| SSH PasswordAuthentication | Must be `no` | Keys only |
| SSH Protocol | Must be `2` | Set Protocol 2 |
| Firewall active | ufw/firewalld running | Enable firewall |
| SELinux enforcing | Must be `enforcing` | Set in selinux/config |
| Empty passwords | None allowed | Lock accounts |
| IP forwarding | Must be disabled | sysctl setting |
| ICMP redirects | Must be disabled | sysctl setting |
| umask | Must be 027 | Set in /etc/profile |
| auditd | Must be enabled | systemctl enable |

Returns: pass/fail per control, score (X/10), risk level (LOW/MEDIUM/HIGH), remediation per failure.

---

### audit_automation_maturity
**Accelerator:** A8 — Automation & IaC
**Transport:** SSH (paramiko)
**Access level:** Read-only version checks

Detects presence of:
`ansible` `terraform` `puppet` `chef` `salt` `git` `docker` `podman` `jenkins`

Returns: tools detected with versions, maturity rating:
- **HIGH** — 4+ tools detected
- **MEDIUM** — 2-3 tools
- **LOW** — 0-1 tools (manual operations risk)

---

### scan_vmware_environment
**Accelerator:** A5 — VMware Cost Optimizer
**Transport:** pyVmomi HTTPS (port 443)
**Access level:** Read-only vCenter API

Collects:
- Total VM count, total vCPU, total RAM
- Powered-off VMs (wasting Broadcom licenses)
- Oversized VMs (>4 vCPU, <10% CPU usage)
- VMs with active snapshots (storage + licensing waste)
- Estimated recoverable licenses
- Dollar savings estimate ($200/license/year baseline)

**Required inputs:** `vcenter_host`, `username`, `password`

---

### scan_network_health
**Accelerator:** A3 — Network Health Check
**Transport:** nmap (must be installed)
**Access level:** Passive network scan

Process:
1. Host discovery across target subnet (`nmap -sn`)
2. Risky port scan on discovered hosts (capped at 20 hosts)
3. Latency measurement per host

Risky ports flagged:

| Port | Service | Risk |
|---|---|---|
| 21 | FTP | Plaintext credentials |
| 23 | Telnet | Plaintext session |
| 445 | SMB | Lateral movement risk |
| 3389 | RDP | Remote access exposure |
| 3306 | MySQL | Database exposed |
| 5432 | PostgreSQL | Database exposed |
| 6379 | Redis | Often no auth |
| 27017 | MongoDB | Often no auth |

Risk rating: CRITICAL (>10 findings) / HIGH (>5) / MEDIUM (>0) / LOW

---

## Error Handling

If a tool fails (host unreachable, auth failure, timeout), the error is captured in `failed_tools` and the agent continues with remaining scans. The final report includes a section noting which tools could not connect and why.

---

## Report Structure

The `generate_executive_report` tool enforces this section order:

1. Executive Summary
2. Server Inventory
3. Risk Map
4. Savings Estimate
5. License Cost Comparison
6. Migration Roadmap

Each section ends with the applicable Apex accelerator reference.

---

## File Structure

```
ScoutAgent/
├── agent.py                  # Main agent loop + tool dispatcher
├── tools/
│   ├── linux_scout.py        # A1, A2, A8 tools
│   ├── vmware_scout.py       # A5 tool
│   └── network_scout.py      # A3 tool
├── docs/
│   ├── TECHNICAL.md          # This document
│   └── DELIVERY.md           # Client-facing report reference
├── reports/                  # Generated reports (gitignored)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Dependencies

```
anthropic>=0.25.0    # Claude API + Bedrock client
paramiko>=3.4.0      # SSH transport
pyVmomi>=8.0.2       # VMware vCenter API
python-dotenv>=1.0.0 # Environment config
nmap                 # System package (included in Docker image)
```

---

## Security Posture

- All scans are **read-only** — no writes, no config changes
- Credentials passed via environment variables only — never in image
- SSH keys preferred over passwords
- No findings stored server-side — output is a local Markdown file
- In Bedrock mode: zero data reaches Anthropic infrastructure
- In Ollama mode: zero data leaves the physical facility

---

*Apex Systems | Infrastructure Practice | Confidential*
