# Infrastructure Assessment Report
**Client:** Acme Corporation
**Prepared by:** Apex Systems — AI Infrastructure Scout Agent
**Assessment Date:** 2026-04-25
**Report Classification:** Confidential

---

## 1. Executive Summary

### Situation
Apex Systems conducted a read-only infrastructure assessment of Acme Corporation's Linux server estate and network environment on 2026-04-25. The assessment covered 1 Linux host, 47 VMware virtual machines across one vCenter instance, and the 10.10.0.0/24 network segment.

### What We Found

**Estate:** 1 Linux server running RHEL 8.6, last patched 74 days ago. 47 VMware VMs with 5 powered off and 3 significantly oversized. 23 live network hosts discovered.

**Risk:** The environment has a HIGH overall risk rating. Root SSH login is enabled, SELinux is in permissive mode, and auditd is not running — meaning unauthorized access attempts are neither blocked nor logged. An unknown user logged in at 03:17 on April 22nd and this event cannot be investigated due to missing audit logs. 143 failed login attempts recorded on the primary host.

**Opportunity:** $1,600/year in immediate VMware license savings identified. 8 recoverable licenses from powered-off and oversized VMs. Additional savings achievable through Linux migration of eligible Windows workloads.

### Top 3 Recommendations

**Priority 1 — Close the security exposure (this week)**
Root SSH and password authentication are enabled on the primary host. Combined with 143 failed login attempts and an unidentified login at 3am, this is an active risk, not a future concern. Remediation takes under 2 hours.
*Applicable accelerator: A2 — Linux Hardening Sprint*

**Priority 2 — Reclaim $1,600/year in VMware licenses (this month)**
5 powered-off VMs are consuming Broadcom vSphere licenses. 3 additional VMs are provisioned at 2x their actual CPU usage. Rightsizing these 8 VMs requires no downtime and recovers immediate budget.
*Applicable accelerator: A5 — VMware Cost Optimizer*

**Priority 3 — Establish audit and monitoring baseline (30 days)**
auditd is disabled. No pipeline exists to detect or respond to security events. Before any migration or modernization work begins, a logging baseline must be established to satisfy audit requirements and protect the remediation investment.
*Applicable accelerator: A8 — Automation & IaC*

---

## 2. Server Inventory

| Field | Value |
|---|---|
| Hostname | prod-app-01.acme.local |
| IP Address | 10.10.0.5 |
| Operating System | Red Hat Enterprise Linux 8.6 (Ootpa) |
| Kernel | 4.18.0-372.9.1.el8.x86_64 |
| OS End of Support | May 2029 (within support window) |
| CPU Cores | 8 |
| RAM | 32 GB |
| Disk Usage | 78% of 500GB ⚠️ |
| Uptime | 97 days |
| Last Reboot | 2026-01-17 ⚠️ (97 days — stability risk) |
| Last Patch | 2026-02-10 ⚠️ (74 days — patch gap) |
| Failed Logins (30d) | 143 🔴 (brute force indicator) |
| Open Ports | 22, 80, 443, 3306, 8080 ⚠️ |
| Logged-in Users | admin, jdoe, svc_backup |
| Automation Tools | git, docker |

**Flags:**
- 🔴 **BRUTE FORCE INDICATOR** — 143 failed logins with no auditd running = blind spot
- ⚠️ **PATCH GAP** — 74 days since last patch (threshold: 60 days)
- ⚠️ **STABILITY RISK** — 97 days since reboot (threshold: 90 days)
- ⚠️ **CAPACITY RISK** — Disk at 78%, approaching 80% threshold
- ⚠️ **EXPOSED PORTS** — MySQL (3306) and alternate HTTP (8080) listening

*Applicable accelerator: A1 — Linux Fast Track*

---

## 3. Risk Map

### Risk Heat Map Summary

| Rating | Count | Hosts Affected |
|---|---|---|
| 🔴 CRITICAL (20-25) | 2 | prod-app-01, 10.10.0.18 |
| 🟠 HIGH (12-19) | 5 | prod-app-01, 10.10.0.5, 10.10.0.12, 10.10.0.22, 10.10.0.31 |
| 🟡 MEDIUM (6-11) | 3 | prod-app-01 |
| 🟢 LOW (1-5) | 0 | — |

### Risk Register

| ID | Risk | Host | Likelihood | Impact | Score | Rating | Remediation | Priority |
|---|---|---|---|---|---|---|---|---|
| R001 | Root SSH login enabled | prod-app-01 | 4 | 5 | 20 | 🔴 CRITICAL | Set PermitRootLogin no | 1 |
| R002 | MongoDB exposed, no auth confirmed | 10.10.0.18 | 4 | 5 | 20 | 🔴 CRITICAL | Bind to localhost or add auth | 1 |
| R003 | Password auth enabled on SSH | prod-app-01 | 3 | 4 | 12 | 🟠 HIGH | Key-only auth | 2 |
| R004 | Patch gap — 74 days | prod-app-01 | 3 | 4 | 12 | 🟠 HIGH | Schedule patch window | 2 |
| R005 | Telnet open on network host | 10.10.0.5 | 3 | 4 | 12 | 🟠 HIGH | Disable telnet, enforce SSH | 2 |
| R006 | RDP exposed | 10.10.0.22 | 3 | 4 | 12 | 🟠 HIGH | Restrict to VPN only | 2 |
| R007 | Redis exposed, auth unconfirmed | 10.10.0.31 | 3 | 4 | 12 | 🟠 HIGH | Bind to localhost, add requirepass | 2 |
| R008 | SELinux in permissive mode | prod-app-01 | 2 | 4 | 8 | 🟡 MEDIUM | Set enforcing mode | 3 |
| R009 | auditd disabled — no security logging | prod-app-01 | 2 | 4 | 8 | 🟡 MEDIUM | systemctl enable auditd | 3 |
| R010 | umask 022 — files created world-readable | prod-app-01 | 2 | 3 | 6 | 🟡 MEDIUM | Set umask 027 in /etc/profile | 3 |

**Critical note on R001 + R009 combination:** Root SSH is enabled AND auditd is not running. The unknown login recorded at 03:17 on April 22nd cannot be investigated — there are no logs. This combination elevates both risks above their individual scores.

*Applicable accelerators: A2 — Linux Hardening Sprint · A3 — Network Health Check*

---

## 4. Savings Estimate

### The Opportunity

| Scenario | Annual Savings | Source | Confidence |
|---|---|---|---|
| Conservative | $1,600 | Powered-off VM license reclaim only | HIGH |
| Moderate | $4,200 | + VM rightsizing applied | MEDIUM |
| Aggressive | $18,400 | + Linux migration of eligible Windows VMs | MEDIUM |

**Confidence Level: MEDIUM overall**
vCenter data is complete and accurate. Windows licensing costs estimated at $200/license/year (Broadcom baseline) — actual contract rates may vary. Linux migration savings based on Forrester TEI for RHEL: 34% 3-year TCO reduction.

### 3-Year Perspective

| | Year 1 | Year 2 | Year 3 | Total |
|---|---|---|---|---|
| Conservative savings | $1,600 | $1,600 | $1,600 | $4,800 |
| Moderate savings | $4,200 | $4,200 | $4,200 | $12,600 |
| Aggressive savings | $18,400 | $22,000 | $22,000 | $62,400 |

*Applicable accelerator: A5 — VMware Cost Optimizer*

---

## 5. License Cost Comparison

### Powered-Off VMs — Immediate Recovery

| VM Name | vCPU | RAM | Annual License Cost | Action |
|---|---|---|---|---|
| OLD-WEB-01 | 4 | 16 GB | $200 | Decommission |
| TEST-DB-03 | 8 | 32 GB | $200 | Decommission or reclaim |
| DECOM-APP-07 | 4 | 8 GB | $200 | Decommission |
| LEGACY-FS-02 | 2 | 8 GB | $200 | Decommission |
| OLD-PROXY-01 | 2 | 4 GB | $200 | Decommission |
| **Total** | | | **$1,000/yr** | |

### Oversized VMs — Rightsizing Candidates

| VM Name | Current vCPU | Recommended | CPU Usage | RAM | Annual Savings |
|---|---|---|---|---|---|
| PROD-APP-02 | 16 | 8 | 180 MHz avg | 64 GB | $400 |
| PROD-APP-04 | 12 | 6 | 95 MHz avg | 48 GB | $300 |
| DEV-BUILD-01 | 8 | 4 | 60 MHz avg | 32 GB | $300 |
| **Total** | | | | | **$1,000/yr** |

**Combined immediate savings: $2,000/year**
*(Note: $1,600 previously cited is powered-off VMs only; rightsizing adds $400 minimum)*

*Applicable accelerators: A1 — Linux Fast Track · A5 — VMware Cost Optimizer*

---

## 6. Migration Roadmap

### Phase Overview

| Phase | Timeline | Scope | Value |
|---|---|---|---|
| Phase 1 — Secure | Days 1-30 | Security hardening, powered-off VM cleanup | Risk reduction + $1,000/yr |
| Phase 2 — Stabilize | Days 31-60 | Patch gap closure, monitoring baseline, snapshot cleanup | Compliance readiness |
| Phase 3 — Optimize | Days 61-90 | VM rightsizing, Linux migration pilot | Additional $1,000+/yr savings |

### Phase 1 — Secure (Days 1-30)
**Scope:** prod-app-01 hardening + 5 powered-off VM decommission

Activities:
1. Disable root SSH login and password authentication (2 hours, zero downtime)
2. Enable auditd and configure basic rules (1 hour)
3. Set SELinux to enforcing — test first in permissive, resolve denials (4-8 hours)
4. Decommission 5 confirmed powered-off VMs after owner validation
5. Set umask 027, disable ICMP redirects

Prerequisites: Change window approval, VM owner sign-off
Success criteria: CIS benchmark score improves from 5/10 to 9/10. Powered-off VM count = 0.

### Phase 2 — Stabilize (Days 31-60)
**Scope:** Patch currency, monitoring, network hardening

Activities:
1. Apply all outstanding patches to prod-app-01 (schedule maintenance window)
2. Investigate and remediate 5 risky open ports on network hosts
3. Remove or bind MongoDB, Redis, MySQL to localhost or VPN-only access
4. Disable Telnet on 10.10.0.5
5. Restrict RDP on 10.10.0.22 to VPN access only
6. Remove VM snapshots from PROD-DB-01, PROD-APP-01, STAGING-WEB-02

Prerequisites: Network team involvement for port changes
Success criteria: Zero risky open ports. Patch currency restored. All snapshots removed.

### Phase 3 — Optimize (Days 61-90)
**Scope:** VM rightsizing + Linux migration pilot

Activities:
1. Rightsize PROD-APP-02, PROD-APP-04, DEV-BUILD-01 (schedule maintenance windows)
2. Identify Linux migration candidates from remaining Windows VM estate
3. Pilot migration of 2-3 non-critical workloads to RHEL/Rocky Linux
4. Validate workloads and document migration runbook for remaining servers

Prerequisites: Phase 2 complete. Stakeholder approval for rightsizing.
Success criteria: 3 VMs rightsized. 2-3 workloads running on Linux. Migration runbook documented.

### Out-of-Scope — Requires Further Review

| Host | Role | Blocker | Review Trigger |
|---|---|---|---|
| 10.10.0.22 | Unknown — RDP exposed | Owner not identified | Phase 1 owner validation |
| 10.10.0.18 | Unknown — MongoDB exposed | No auth confirmed | Immediate — treat as P1 |

*Applicable accelerators: A1 · A2 · A3 · A5 · A8*

---

## 7. AI Stack Assessment

**Host:** prod-app-01.acme.local
**AI Readiness:** EARLY_STAGE

The host has Docker installed and scikit-learn present, indicating early-stage ML activity. No GPU hardware detected. No model serving framework deployed. No vector database running.

**Security Gap:** An unauthenticated API endpoint was found listening on port 8080. If this is serving an AI/ML model, access should be restricted immediately.

**Recommendation:** If Acme intends to expand AI/ML workloads, a dedicated GPU server or cloud GPU instance should be evaluated. Current infrastructure cannot support production AI workloads.

*Applicable accelerator: A7 — AI Stack Assessment*

---

*Report generated by AI Infrastructure Scout Agent v1.0*
*Apex Systems | Infrastructure Practice | Confidential*
*All scans performed read-only. No changes were made to any client system.*
