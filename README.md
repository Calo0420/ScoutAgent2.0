# ScoutAgent 2.0
### AI Infrastructure Scout — by Everforth

> *"We scan it. We explain it. We show you what it costs you."*

ScoutAgent 2.0 is a Claude-powered infrastructure assessment tool that connects to a client's Linux server, runs a comprehensive security and operational audit, and produces a board-ready PDF report — all in under 10 minutes, with no client-side software required.

---

## 🔐 Trust Layer — Powered by Gatekeeper

ScoutAgent 2.0 works with **[Gatekeeper](https://github.com/Calo0420/Gatekeeper)** — an AI trust gateway that monitors and certifies every scan session.

When deployed with Gatekeeper:
- Client approves the exact scope before ScoutAgent enters
- Every file access is logged and monitored in real time
- Unauthorized access attempts are blocked automatically
- A cryptographically signed audit report is generated on exit

> *Gatekeeper is what makes ScoutAgent enterprise-deployable.*

---

## What It Does

| Phase | What Happens |
|---|---|
| **Connect** | Agent SSHs into the target server (read-only, no changes made) |
| **Scan** | Runs parallel assessments across security, network, automation, and AI readiness |
| **Score** | Produces a severity-weighted health score (0–100) with letter grade |
| **Report** | Generates a full executive PDF report with risk register, roadmap, and cost estimates |
| **Present** | Live dashboard with animated topology visualization for client-facing demos |

---

## Accelerators Covered

| ID | Name | What It Detects |
|---|---|---|
| **A1** | Linux Fast Track | OS health, open ports, user accounts, uptime, disk, patch status |
| **A2** | Linux Hardening Sprint | CIS Benchmark Level 1 (10 controls), SELinux/AppArmor, auditd, umask |
| **A3** | Network Health Check | Live host discovery, risky open ports (Telnet, RDP, MongoDB, Redis) via nmap |
| **A5** | VMware Cost Optimizer | Powered-off VMs, oversized VMs, unmanaged snapshots via vCenter API |
| **A7** | AI Stack Assessment | GPU detection, CUDA, ML frameworks, model serving platforms, vector DBs |
| **A8** | Automation & IaC | Ansible, Terraform, Jenkins, CI/CD pipeline maturity |

---

## Dashboard

The live web dashboard runs on port `7070` and provides:

- **Real-time topology canvas** — animated network map with pulsing data-stream beams, accelerator info cards, and per-check progress overlay while scanning
- **Severity-weighted health score** — 0–100 with letter grade (A through F)
- **Presenter mode** — fullscreen with floating control bar for client meetings
- **Auto-demo sequence** — guided walkthrough from worst-case to best-practice scenarios
- **Self-service settings panel** — configure target host, SSH credentials, subnet, vCenter, API keys, and deploy mode entirely from the browser — no terminal required
- **SSH key paste** — paste a private key directly into the UI; server normalises and saves it with correct permissions
- **Test connection** — verify SSH connectivity to the target before scanning
- **PDF report download** — one-click branded report delivery; button only appears once the real scan is confirmed complete

---

## Quick Start

### Prerequisites
- Debian or Ubuntu Linux server
- Root or sudo access
- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

### Install

```bash
git clone https://github.com/Calo0420/ScoutAgent2.0.git /opt/ScoutAgent2.0
cd /opt/ScoutAgent2.0
cp .env.example .env
nano .env          # add your API key and client info
bash install.sh
```

The installer handles everything: system packages, Python venv, dependencies, self-scan SSH key, hostile lab containers, and UI server startup.

### Access the Dashboard

```
http://<server-ip>:7070
```

---

## Running a Scan

### From the Dashboard (recommended)

1. Open `http://<server-ip>:7070`
2. Click the **⚙ gear icon** → enter operator password → configure target
3. Paste SSH private key or enter key file path → click **TEST CONNECTION**
4. Click **▶ RUN SCAN** — the canvas animates while the agent works
5. When scan completes, the results modal opens and **↓ DOWNLOAD REPORT** appears

### From the Terminal

```bash
cd /opt/ScoutAgent2.0
export $(grep -v '^#' .env | xargs)

# Self-scan (agent scans the machine it runs on)
.venv/bin/python agent.py \
  --client "Client Name" \
  --host localhost \
  --user root \
  --key /root/.ssh/scout_local_key

# Remote server scan
.venv/bin/python agent.py \
  --client "Client Name" \
  --host 10.0.0.10 \
  --user admin \
  --key ~/.ssh/client_key \
  --port 22 \
  --subnet 10.0.0.0/24

# With VMware vCenter
.venv/bin/python agent.py \
  --host 10.0.0.10 --user admin --key ~/.ssh/key \
  --vcenter vc.client.local \
  --vc-user administrator@vsphere.local \
  --vc-pass YourPassword
```

---

## Environment Configuration

Copy `.env.example` to `.env`:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...
OPERATOR_PASSWORD=your-secure-password

# Deployment mode: claude | bedrock | ollama | venice
DEPLOY_MODE=claude

# Client info (appears in reports and dashboard)
CLIENT_NAME=Acme Corp
TARGET_HOST=192.168.1.100

# Set true to run with mock data (no real scan needed)
DEMO_MODE=false

# Venice AI via Agent Zero (required when DEPLOY_MODE=venice)
VENICE_API_KEY=sk-a0-...
VENICE_MODEL=llama-3.3-70b
```

### Deploy Modes

| Mode | Description | When to Use |
|---|---|---|
| `claude` | Direct Anthropic API | Default — fast, full features |
| `bedrock` | AWS Bedrock (Claude) | Client requires data to stay in their AWS account |
| `ollama` | Local LLM via Ollama | Air-gapped / fully on-prem environments |
| `venice` | Venice AI via Agent Zero | Open-source models (Llama, Mistral, etc.) via Agent Zero key |

---

## Project Structure

```
ScoutAgent2.0/
├── agent.py                  # Main orchestration agent (Claude API)
├── install.sh                # One-command installer
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
│
├── tools/
│   ├── linux_scout.py        # A1/A2/A8 — Linux, CIS, Automation
│   ├── network_scout.py      # A3 — Network health via nmap
│   ├── vmware_scout.py       # A5 — VMware vCenter via pyVmomi
│   ├── ai_stack_scout.py     # A7 — GPU, ML frameworks, model serving
│   └── mock_tools.py         # Demo mode mock data
│
├── ui/
│   ├── index.html            # Dashboard (single-file, zero build step)
│   └── server.py             # FastAPI server (port 7070)
│
├── docs/
│   ├── manual_client_it.html # Client IT Team manual
│   └── manual_sales.html     # Sales Playbook
│
├── hostile-lab/
│   └── docker-compose.yml    # Demo misconfiguration environment
│
└── reports/                  # Generated scan reports (gitignored)
```

---

## Hostile Lab

The hostile lab spins up deliberately misconfigured services so every finding shown in a demo is **100% real** — not simulated.

```bash
cd /opt/ScoutAgent2.0/hostile-lab
docker compose up -d
```

| Container | Port | Finding Triggered |
|---|---|---|
| `scout-mongo` | 27017 | MongoDB exposed — no authentication |
| `scout-redis` | 6379 | Redis exposed — no authentication |
| `scout-telnet` | 23 | Telnet active — plaintext credentials |

Combined with native server misconfigurations (root SSH, no MAC enforcement, exposed RDP), this produces a fully authentic HIGH RISK scan result for live demonstrations.

---

## Report Output

After each scan, two files are written to `reports/`:

| File | Format | Contents |
|---|---|---|
| `<scan_id>.md` | Markdown | Full report source |
| `<scan_id>.json` | JSON | Structured findings for dashboard |

The report includes:

- Executive Summary with top 3 prioritized recommendations
- Server Inventory table
- Risk Heat Map and Risk Register
- CIS Benchmark audit (10 controls with pass/fail)
- Breach cost avoidance estimates and 3-year TCO comparison
- License and OS support comparison
- 30/60/90-day Migration Roadmap

Download as a branded PDF directly from the dashboard after scan completion.

---

## Dashboard Keyboard Shortcuts

| Key | Action |
|---|---|
| `SPACE` | Run / Reset scan |
| `F` | Toggle fullscreen |
| `P` | Toggle presenter bar |
| `1` – `6` | Toggle individual assessment modules |
| `N` | Worst Case scenario |
| `C` | Best Practice scenario |
| `ESC` | Close modal / end demo |

---

## Included Manuals

| Manual | URL | Audience |
|---|---|---|
| Client IT Team | `/manual/client-it` | Technical stakeholders, sysadmins |
| Sales Playbook | `/manual/sales` | Account executives, pre-sales engineers |

---

## Security Notes

- **Read-only** — the agent never modifies the target system
- **No software installed on client** — scan runs entirely from the operator's side
- **API key stays local** — never transmitted to the client environment
- **Reports stored locally** — never uploaded to third-party services
- The hostile lab is intentionally insecure — **never run in production**

---

## 👥 Team

| Name | Role |
|------|------|
| Oscar Reyes Luna | Creator · Builder · Everforth Innovation Labs |
| Juan Alonso | Creator · Accelerators Implementation · Everforth Innovation Labs |

---

## License

Proprietary — Everforth / Apex Systems. Internal use only.

---

<div align="center">
  <sub>Built with Claude Sonnet 4.6 &nbsp;·&nbsp; Everforth AI Infrastructure Practice &nbsp;·&nbsp; 2026</sub>
</div>
