# Scouter 2.0 — AI Infrastructure Scout Agent

> One command. One agent. Client-ready infrastructure assessment in minutes.

**Powered by Claude (Anthropic) · Covers 6 of 11 Apex Accelerators · Three deployment modes**

---

## What It Does

Scouter 2.0 is an autonomous AI agent that replaces weeks of manual infrastructure consulting work with a single CLI command. Point it at a client environment — a Linux server, a VMware vCenter, a network subnet, or all three — and it returns a structured, executive-ready report covering security posture, cost savings, and a migration roadmap.

No agents to manage. No dashboards to configure. One Python file, one command.

---

## Accelerators Covered

| ID | Accelerator | What Scout Does |
|----|-------------|-----------------|
| A1 | Linux Fast Track | SSH scan: OS, kernel, CPU/RAM/disk, uptime, users, open ports, last patch, last reboot |
| A2 | Linux Hardening Sprint | CIS Benchmark Level 1 spot checks — pass/fail per control with remediation steps |
| A3 | Network Health Check | Subnet discovery, risky open port detection (Telnet, RDP, MongoDB, Redis), latency baseline |
| A5 | VMware Cost Optimizer | vCenter inventory, powered-off VMs, oversized VMs, snapshot waste, dollar savings estimate |
| A7 | AI Stack Assessment | GPU/CUDA detection, model serving frameworks, vector databases, ML frameworks, security gaps |
| A8 | Automation & IaC | Detects Ansible, Terraform, Puppet, Chef, Salt, Docker, Jenkins — maturity rating |

**6 accelerators. One tool.**

---

## Report Output

Every run produces a Markdown executive report saved to `reports/<client>_<timestamp>.md`.

The report contains 6 structured sections:

1. **Executive Summary** — situation, top findings, top 3 recommendations (CIO-readable in under 5 minutes)
2. **Server Inventory** — full asset table with OS, CPU, RAM, end-of-support dates, risk flags
3. **Risk Map** — heat map + risk register (likelihood × impact scoring per finding)
4. **Savings Estimate** — annual savings, 3-year TCO comparison, break-even, confidence level
5. **License Cost Comparison** — current vs Linux/alternative, per-server cost detail
6. **Migration Roadmap** — concrete 30/60/90-day phases with scope and success criteria

Each section ends with the applicable accelerator reference.

See [`docs/SAMPLE_REPORT.md`](docs/SAMPLE_REPORT.md) for a full example output.

---

## Quick Start

### Option 1 — Demo Mode (no real infrastructure needed)

The fastest way to see a full report. Uses realistic mock data.

```bash
git clone https://github.com/calo004200-dev/Scouter2.0.git
cd Scouter2.0
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...
python agent.py --demo --client "Acme Corp"
```

Report saved to `reports/acme_corp_<timestamp>.md`.

---

### Option 2 — Python Direct

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

# Scan a Linux host
python agent.py --client "Acme Corp" --host 10.0.0.5 --user admin --key ~/.ssh/id_rsa

# Scan vCenter
python agent.py --client "Acme Corp" --vcenter vc.acme.local --vc-user admin --vc-pass secret

# Scan a network subnet
python agent.py --client "Acme Corp" --subnet 10.0.0.0/24

# Full scan — all three at once
python agent.py --client "Acme Corp" \
  --host 10.0.0.5 --user admin --key ~/.ssh/id_rsa \
  --vcenter vc.acme.local --vc-user admin --vc-pass secret \
  --subnet 10.0.0.0/24
```

---

### Option 3 — Docker (recommended for client engagements)

```bash
docker build -t scouter:latest .

# Linux host scan
docker run --rm --network host \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -v $(pwd)/reports:/app/reports \
  scouter:latest \
  --client "Acme Corp" --host 10.0.0.5 --user admin --key /app/keys/id_rsa

# vCenter scan
docker run --rm --network host \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -v $(pwd)/reports:/app/reports \
  scouter:latest \
  --client "Acme Corp" --vcenter vc.acme.local --vc-user admin --vc-pass secret

# Network scan
docker run --rm --network host \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -v $(pwd)/reports:/app/reports \
  scouter:latest \
  --client "Acme Corp" --subnet 10.0.0.0/24
```

---

## CLI Reference

| Flag | Description |
|------|-------------|
| `--client` | Client name for the report (default: "Client") |
| `--host` | Linux host IP or hostname |
| `--user` | SSH username |
| `--key` | Path to SSH private key (preferred) |
| `--password` | SSH password (fallback if no key) |
| `--vcenter` | vCenter hostname or IP |
| `--vc-user` | vCenter username |
| `--vc-pass` | vCenter password |
| `--subnet` | Network subnet in CIDR notation (e.g. `10.0.0.0/24`) |
| `--demo` | Run with mock data — no real infrastructure required |

---

## Deployment Modes

Controlled by the `DEPLOY_MODE` environment variable. Three backends supported:

| Mode | Backend | Data Leaves Client? | Use Case |
|------|---------|---------------------|----------|
| `claude` | Anthropic API (default) | Encrypted, Anthropic policy | Standard commercial clients |
| `bedrock` | AWS Bedrock | Never — stays in client AWS account | HIPAA, SOC2, regulated clients |
| `ollama` | Local LLM server | Never — fully air-gapped | Government, classified environments |

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

### Ollama (air-gap / on-prem)
```bash
DEPLOY_MODE=ollama
OLLAMA_BASE_URL=http://gpu-server.internal:11434/v1
OLLAMA_MODEL=llama3
```

Copy `.env.example` to `.env` and fill in your values.

---

## Architecture

```
CLI command
     |
agent.py  (Claude — routes and reasons about what to scan)
     |
     +-- scan_linux_environment()    SSH read-only   (A1)
     +-- check_cis_benchmarks()      SSH read-only   (A2)
     +-- scan_network_health()       nmap passive    (A3)
     +-- scan_vmware_environment()   pyVmomi HTTPS   (A5)
     +-- assess_ai_stack()           SSH read-only   (A7)
     +-- audit_automation_maturity() SSH read-only   (A8)
     |
generate_executive_report()
     |
reports/<client>_<timestamp>.md
```

Claude acts as the reasoning layer. It receives the user request, decides which tools are applicable based on the credentials provided, calls them in sequence, correlates findings across scans, and synthesizes everything into the structured report. No hardcoded scan order — the agent reasons about it.

If a tool fails (unreachable host, auth error, timeout), the agent continues with remaining scans and notes the failure in the report.

---

## Security

- **Read-only** — zero writes, zero config changes to any client system
- **No persistence** — findings exist only in the local report output
- **Credentials via env vars only** — never baked into the image or code
- **SSH keys preferred** — password auth supported but not recommended
- **Bedrock mode** — zero data reaches Anthropic infrastructure
- **Ollama mode** — zero data leaves the physical facility

---

## Project Structure

```
Scouter2.0/
├── agent.py                   # Main agent — Claude brain + tool loop
├── tools/
│   ├── linux_scout.py         # A1, A2, A8 — SSH-based scans
│   ├── vmware_scout.py        # A5 — vCenter inventory via pyVmomi
│   ├── network_scout.py       # A3 — nmap network discovery
│   ├── ai_stack_scout.py      # A7 — AI/ML stack assessment
│   └── mock_tools.py          # Demo mode — realistic mock data
├── docs/
│   ├── TECHNICAL.md           # Architecture and tool reference
│   ├── DELIVERY.md            # Report structure and QA checklist
│   └── SAMPLE_REPORT.md       # Example output from a full scan
├── reports/                   # Generated reports land here (gitignored)
├── .env.example               # Environment variable reference
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Requirements

- Python 3.12+ or Docker
- `ANTHROPIC_API_KEY` (or AWS/Ollama credentials for alternate backends)
- Network access to target hosts (SSH port 22, vCenter port 443)
- `nmap` installed (included in the Docker image)

```
anthropic>=0.25.0    # Claude API + Bedrock client
paramiko>=3.4.0      # SSH transport
pyVmomi>=8.0.2       # VMware vCenter API
python-dotenv>=1.0.0 # Environment config
openai>=1.0.0        # Required only for DEPLOY_MODE=ollama
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/TECHNICAL.md`](docs/TECHNICAL.md) | Full architecture, tool specs, deployment guide |
| [`docs/DELIVERY.md`](docs/DELIVERY.md) | Report structure, QA checklist, delivery standards |
| [`docs/SAMPLE_REPORT.md`](docs/SAMPLE_REPORT.md) | Full example report from a demo run |
| [`.env.example`](.env.example) | All environment variables with documentation |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built by [calo004200-dev](https://github.com/calo004200-dev)*
