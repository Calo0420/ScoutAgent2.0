# 🔍 ScoutAgent 2.0 — AI Infrastructure Scanner

> *"We scan it. We explain it. We show you what it costs you."*

**ScoutAgent 2.0** is a Claude-powered AI agent that connects to a client's Linux or Windows environment, runs a comprehensive security and operational audit mapped to CIS Controls v8 and NIST SP 800-53, and delivers a board-ready PDF report — in under 10 minutes, with no client-side software required.

Every tool call ScoutAgent makes is governed in real time by **[Gatekeeper](https://github.com/Calo0420/Gatekeeper)** — the AI Trust Gateway that approves, blocks, and audits every action before it runs.

Built by **Oscar Reyes Luna** · Everforth Innovation Labs · Apex Systems  
**Everforth Galactic Hackathon 2026 — Grand Finalist**

---

## 🚀 Live Demo

**→ [http://18.216.220.211:7070](http://18.216.220.211:7070)**

| Service | URL |
|---|---|
| ScoutAgent (AI Infrastructure Scanner) | http://18.216.220.211:7070 |
| Gatekeeper (AI Trust Gateway) | http://18.216.220.211:8001 |

**To run the demo:** Open ScoutAgent → click **Auto Demo** → watch the live scan → download the PDF report → open Gatekeeper to see the signed audit trail of every action taken.

---

## 💡 What It Does

| Phase | What Happens |
|---|---|
| **Connect** | SSHs into Linux targets or connects via WinRM to Windows Servers — read-only, no changes made |
| **Scan** | Runs parallel assessments: security, network, CIS benchmarks, automation maturity, AI stack |
| **Score** | Produces a severity-weighted health score with risk level per finding |
| **Report** | Generates a full executive PDF — risk register, heat map, roadmap, and cost savings estimate |
| **Govern** | Every tool call checked against Gatekeeper before execution — approved or blocked in real time |

---

## 🔐 Trust Layer — Powered by Gatekeeper

ScoutAgent 2.0 integrates with **[Gatekeeper](https://github.com/Calo0420/Gatekeeper)** — the AI governance layer that makes enterprise AI deployable.

Before ScoutAgent runs any tool:
1. Gatekeeper intercepts the request
2. Claude on AWS Bedrock evaluates it against the approved scope
3. Allowed or blocked — in milliseconds
4. Every decision is logged with a SHA-256 signed audit trail
5. On exit, a tamper-evident PDF audit report is generated

> *Gatekeeper is what makes ScoutAgent enterprise-deployable. It's the answer to every client who asks "how do we prove it's safe?"*

---

## 🧰 Accelerators Covered

| ID | Name | Platform | What It Detects |
|---|---|---|---|
| **A1** | Windows Fast Track | Windows | OS health, open ports, user accounts, uptime, disk, patch status, running services |
| **A1** | Linux Fast Track | Linux | OS health, CPU/RAM/disk, uptime, logged-in users, open ports, running services |
| **A2** | Hardening Sprint | Linux + Windows | CIS Benchmark checks — SELinux, AppArmor, auditd, firewall, Defender, UAC, SMBv1, password policy |
| **A3** | Network Health Check | Any | Live host discovery, risky open ports (Telnet, RDP, MongoDB, Redis) via nmap |
| **A5** | VMware Cost Optimizer | VMware | Powered-off VMs, oversized VMs, unmanaged snapshots via vCenter API |
| **A7** | AI Stack Assessment | Linux | GPU detection, CUDA, ML frameworks, model serving platforms, vector DBs |
| **A8** | Automation & IaC | Linux | Ansible, Terraform, Jenkins, CI/CD pipeline maturity |

---

## 📊 Report Sections

Every scan produces a multi-section PDF including:

- **Executive Summary** — situation, what was found, top 3 recommendations
- **Server Inventory** — full hardware and software baseline
- **Risk Heat Map** — likelihood vs. impact matrix for all findings
- **Risk Register** — every finding with CIS/NIST control mapping
- **Savings Estimate** — annual cost reduction opportunities identified
- **License Cost Comparison** — current vs. optimized licensing costs
- **Remediation Roadmap** — 30/60/90-day phased action plan

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| AI Agent | Claude Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6`) |
| Backend API | Python 3.14 + FastAPI |
| Deploy Mode | Claude API (Anthropic) or AWS Bedrock |
| Linux Scanning | Paramiko SSH |
| Windows Scanning | pywinrm (WinRM) |
| Network Scanning | nmap |
| VMware Scanning | pyVmomi |
| PDF Generation | WeasyPrint |
| Frontend | Vanilla HTML/CSS/JS — animated topology canvas |
| Deployment | AWS EC2 · Ubuntu · systemd service (port 7070) |
| Governance | Gatekeeper AI Trust Gateway |

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- Anthropic API key OR AWS Bedrock access
- SSH access to Linux targets (key or password)
- WinRM enabled on Windows targets (`winrm quickconfig`)
- nmap installed for network scans
- vCenter read-only access for VMware scans

### Install

```bash
git clone https://github.com/Calo0420/ScoutAgent2.0.git
cd ScoutAgent2.0

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Set ANTHROPIC_API_KEY or DEPLOY_MODE=bedrock

# Run
uvicorn ui.server:app --host 0.0.0.0 --port 7070
```

Open `http://localhost:7070`

---

## 🔗 Integration with Gatekeeper

```bash
# In your .env
GATEKEEPER_URL=http://localhost:8001
GATEKEEPER_ENABLED=true
```

With Gatekeeper enabled, every tool call ScoutAgent makes is intercepted, evaluated, and logged before execution. The Gatekeeper audit PDF serves as the compliance receipt for the entire scan session.

---

## 🆚 Why ScoutAgent + Gatekeeper?

| Capability | ScoutAgent + Gatekeeper | Manual IT Audit | Other Scanners |
|---|---|---|---|
| Time to report | Under 10 minutes | Days to weeks | Hours |
| Governed AI execution | ✅ | N/A | ❌ |
| Signed audit trail | ✅ | ❌ | ❌ |
| CIS + NIST mapped | ✅ | Varies | Partial |
| Windows + Linux | ✅ | ✅ | Partial |
| Cost savings estimate | ✅ | ❌ | ❌ |
| Client-ready PDF | ✅ | ✅ | Partial |

---

## 🗺️ Roadmap

| Phase | Status | Features |
|---|---|---|
| Linux Scanning | ✅ Live | Full A1–A8 accelerator suite |
| Windows Scanning | ✅ Live | WinRM, CIS benchmarks, security hardening |
| Gatekeeper Integration | ✅ Live | Real-time governance on every tool call |
| Network Scanning | ✅ Live | nmap-powered host discovery and port analysis |
| VMware Scanning | ✅ Live | vCenter API, powered-off VMs, cost optimizer |
| AI Stack Detection | ✅ Live | GPU, CUDA, ML frameworks, vector DBs |
| Multi-Target | 🔜 Next | Scan entire subnets in parallel |
| Scheduled Scans | 🔜 Next | Recurring automated assessments |
| CMDB Integration | 🔜 Future | Push findings to ServiceNow / Azure DevOps |

---

## 👤 Author

| Name | Role |
|---|---|
| **Oscar Reyes Luna** (Calo0420) | Creator · Builder · Everforth Innovation Labs |
| **Juan Alonso** | Creator · Accelerators Implementation · Everforth Innovation Labs |

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>ScoutAgent 2.0 · Everforth Innovation Labs · Apex Systems · Galactic Hackathon 2026 Grand Finalist</sub>
</div>
