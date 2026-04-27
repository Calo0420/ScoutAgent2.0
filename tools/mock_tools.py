"""
Mock Tools — Demo Mode
======================
Returns realistic fake data for demos without real infrastructure.
Activated automatically when DEMO_MODE=true in environment.
Mirrors the exact output schema of every real tool.
"""
from datetime import datetime, timedelta
import random


def mock_scan_linux_environment(host: str, **kwargs) -> dict:
    return {
        "host":          host,
        "scanned_at":    datetime.utcnow().isoformat(),
        "os":            "Red Hat Enterprise Linux 8.6 (Ootpa)",
        "kernel":        "4.18.0-372.9.1.el8.x86_64",
        "uptime":        "up 97 days, 14 hours",
        "cpu_cores":     "8",
        "ram_gb":        "32",
        "disk_usage":    "78% used of 500G",
        "logged_users":  "admin\njdoe\nsvc_backup",
        "last_5_logins": (
            "admin    2026-04-24 09:12:33\n"
            "jdoe     2026-04-23 17:45:01\n"
            "UNKNOWN  2026-04-22 03:17:44\n"
            "admin    2026-04-21 08:30:15\n"
            "root     2026-04-20 22:11:09"
        ),
        "open_ports":    "22\n80\n443\n3306\n8080",
        "pkg_count":     "1247",
        "last_reboot":   (datetime.now() - timedelta(days=97)).strftime("%Y-%m-%d %H:%M"),
        "last_patch":    (datetime.now() - timedelta(days=74)).strftime("%Y-%m-%d") + " kernel-4.18.0-372.9.1",
        "cron_jobs":     "7",
        "failed_logins": "143",
    }


def mock_check_cis_benchmarks(host: str, **kwargs) -> dict:
    controls = [
        {"control": "SSH: PermitRootLogin disabled",  "passed": False, "found": "yes",       "remediation": "Set PermitRootLogin no in sshd_config"},
        {"control": "SSH: Password auth disabled",    "passed": False, "found": "yes",       "remediation": "Set PasswordAuthentication no"},
        {"control": "SSH: Protocol 2 only",           "passed": True,  "found": "2",         "remediation": "OK"},
        {"control": "Firewall active",                "passed": True,  "found": "running",   "remediation": "OK"},
        {"control": "SELinux enforcing",              "passed": False, "found": "permissive","remediation": "Set SELINUX=enforcing in /etc/selinux/config"},
        {"control": "No empty/default passwords",     "passed": True,  "found": "0",         "remediation": "OK"},
        {"control": "IP forwarding disabled",         "passed": True,  "found": "= 0",       "remediation": "OK"},
        {"control": "ICMP redirects disabled",        "passed": False, "found": "= 1",       "remediation": "sysctl -w net.ipv4.conf.all.accept_redirects=0"},
        {"control": "Restrictive umask set",          "passed": False, "found": "022",       "remediation": "Set umask 027 in /etc/profile"},
        {"control": "auditd enabled",                 "passed": False, "found": "disabled",  "remediation": "systemctl enable auditd && systemctl start auditd"},
    ]
    passed = sum(1 for c in controls if c["passed"])
    return {
        "host":       host,
        "controls":   controls,
        "score":      f"{passed}/10",
        "pct":        passed * 10,
        "risk_level": "HIGH",
    }


def mock_audit_automation_maturity(host: str, **kwargs) -> dict:
    return {
        "host": host,
        "tools_detected": {
            "git":    "git version 2.39.3",
            "docker": "Docker version 24.0.5",
        },
        "maturity_level": "LOW",
    }


def mock_scan_vmware_environment(**kwargs) -> dict:
    return {
        "vcenter":           "vc.demo-client.local",
        "total_vms":         47,
        "total_vcpu":        312,
        "total_ram_gb":      1248.0,
        "powered_off_vms": [
            {"name": "OLD-WEB-01",  "vcpu": 4,  "ram_gb": 16.0},
            {"name": "TEST-DB-03",  "vcpu": 8,  "ram_gb": 32.0},
            {"name": "DECOM-APP-07","vcpu": 4,  "ram_gb": 8.0},
            {"name": "LEGACY-FS-02","vcpu": 2,  "ram_gb": 8.0},
            {"name": "OLD-PROXY-01","vcpu": 2,  "ram_gb": 4.0},
        ],
        "oversized_vms": [
            {"name": "PROD-APP-02", "vcpu": 16, "cpu_usage_mhz": 180, "ram_gb": 64.0, "suggestion": "Downsize to 8 vCPU"},
            {"name": "PROD-APP-04", "vcpu": 12, "cpu_usage_mhz": 95,  "ram_gb": 48.0, "suggestion": "Downsize to 6 vCPU"},
            {"name": "DEV-BUILD-01","vcpu": 8,  "cpu_usage_mhz": 60,  "ram_gb": 32.0, "suggestion": "Downsize to 4 vCPU"},
        ],
        "vms_with_snapshots":       ["PROD-DB-01", "PROD-APP-01", "STAGING-WEB-02"],
        "recoverable_licenses":     8,
        "estimated_savings_usd_yr": 1600,
    }


def mock_scan_network_health(**kwargs) -> dict:
    return {
        "subnet":      "10.10.0.0/24",
        "live_hosts":  23,
        "hosts": [
            {"ip": "10.10.0.5",  "open_risky_ports": [{"port": 23,    "risk": "Telnet (plaintext)"}],      "avg_latency_ms": "1.2"},
            {"ip": "10.10.0.12", "open_risky_ports": [{"port": 3306,  "risk": "MySQL exposed"}],           "avg_latency_ms": "0.8"},
            {"ip": "10.10.0.18", "open_risky_ports": [{"port": 27017, "risk": "MongoDB exposed (no auth)"}],"avg_latency_ms": "1.1"},
            {"ip": "10.10.0.22", "open_risky_ports": [{"port": 3389,  "risk": "RDP exposed"}],             "avg_latency_ms": "2.4"},
            {"ip": "10.10.0.31", "open_risky_ports": [{"port": 6379,  "risk": "Redis exposed (no auth)"}], "avg_latency_ms": "0.9"},
        ],
        "risks": [
            {"host": "10.10.0.5",  "port": 23,    "label": "Telnet (plaintext)"},
            {"host": "10.10.0.12", "port": 3306,  "label": "MySQL exposed"},
            {"host": "10.10.0.18", "port": 27017, "label": "MongoDB exposed (no auth)"},
            {"host": "10.10.0.22", "port": 3389,  "label": "RDP exposed"},
            {"host": "10.10.0.31", "port": 6379,  "label": "Redis exposed (no auth)"},
        ],
        "risk_rating": "HIGH",
        "summary":     "23 live hosts | 5 risky open ports found",
    }


def mock_assess_ai_stack(host: str, **kwargs) -> dict:
    return {
        "host": host,
        "gpu":  {},
        "containers": {
            "docker": "Docker version 24.0.5",
        },
        "model_serving":    {},
        "vector_databases": {},
        "ml_frameworks": {
            "scikit_learn": "1.3.0",
        },
        "data_pipelines": {},
        "security_gaps": [
            "Potential AI API endpoints exposed without confirmed auth: 0.0.0.0:8080",
        ],
        "ai_readiness": "EARLY_STAGE",
        "summary": "GPU: NO | Model Serving: NO | Vector DB: NO | ML Frameworks: 1 detected | Readiness: EARLY_STAGE",
    }
