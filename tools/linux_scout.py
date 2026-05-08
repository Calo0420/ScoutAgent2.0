"""
Linux Scout Tools — covers A1 (Fast Track) + A2 (Hardening Sprint)
Runs read-only commands over SSH. Zero writes to client environment.
"""
import paramiko
import json
from datetime import datetime


def _ssh_run(client, cmd):
    _, stdout, stderr = client.exec_command(cmd, timeout=15)
    return stdout.read().decode().strip()


def scan_linux_environment(host: str, username: str, key_path: str = None, password: str = None, port: int = 22) -> dict:
    """
    A1 — Linux Fast Track: rapid environment snapshot.
    Returns OS info, CPU/RAM/disk, uptime, users, open ports, installed packages count.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {"hostname": host, "username": username, "port": port, "timeout": 10}
    if key_path:
        connect_kwargs["key_filename"] = key_path
    else:
        connect_kwargs["password"] = password

    client.connect(**connect_kwargs)

    findings = {
        "host":          host,
        "scanned_at":    datetime.utcnow().isoformat(),
        "os":            _ssh_run(client, "cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'"),
        "kernel":        _ssh_run(client, "uname -r"),
        "uptime":        _ssh_run(client, "uptime -p"),
        "cpu_cores":     _ssh_run(client, "nproc"),
        "ram_gb":        _ssh_run(client, "free -g | awk '/^Mem/{print $2}'"),
        "disk_usage":    _ssh_run(client, "df -h / | awk 'NR==2{print $5\" used of \"$2}'"),
        "logged_users":  _ssh_run(client, "who | awk '{print $1}' | sort -u"),
        "last_5_logins": _ssh_run(client, "last -n 5 --time-format iso | head -5"),
        "open_ports":    _ssh_run(client, "ss -tlnp | awk 'NR>1{print $4}' | cut -d: -f2 | sort -un"),
        "pkg_count":     _ssh_run(client, "rpm -qa 2>/dev/null | wc -l || dpkg -l 2>/dev/null | grep ^ii | wc -l"),
        "last_reboot":   _ssh_run(client, "who -b | awk '{print $3, $4}'"),
        "last_patch":    _ssh_run(client, "rpm -qa --last 2>/dev/null | head -1 || grep ' install ' /var/log/dpkg.log 2>/dev/null | tail -1"),
        "cron_jobs":     _ssh_run(client, "crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$' | wc -l"),
        "failed_logins": _ssh_run(client, "grep 'Failed password' /var/log/auth.log 2>/dev/null | wc -l || grep 'Failed password' /var/log/secure 2>/dev/null | wc -l"),
    }

    client.close()
    return findings


def check_cis_benchmarks(host: str, username: str, key_path: str = None, password: str = None, port: int = 22) -> dict:
    """
    A2 — Linux Hardening Sprint: CIS Benchmark Level 1 spot checks.
    Returns pass/fail per control with remediation hint.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {"hostname": host, "username": username, "port": port, "timeout": 10}
    if key_path:
        connect_kwargs["key_filename"] = key_path
    else:
        connect_kwargs["password"] = password

    client.connect(**connect_kwargs)

    def check(cmd, expected, label, remediation):
        result = _ssh_run(client, cmd)
        passed = expected.lower() in result.lower() if expected else bool(result)
        return {"control": label, "passed": passed, "found": result, "remediation": remediation if not passed else "OK"}

    controls = [
        check("grep -E '^PermitRootLogin' /etc/ssh/sshd_config",          "no",          "SSH: PermitRootLogin disabled",       "Set PermitRootLogin no in sshd_config"),
        check("grep -E '^PasswordAuthentication' /etc/ssh/sshd_config",   "no",          "SSH: Password auth disabled",         "Set PasswordAuthentication no, use keys only"),
        check("grep -E '^Protocol' /etc/ssh/sshd_config",                 "2",           "SSH: Protocol 2 only",                "Set Protocol 2 in sshd_config"),
        check("ufw status 2>/dev/null || firewall-cmd --state 2>/dev/null","active|running","Firewall active",                  "Enable ufw or firewalld"),
        check("grep -E '^SELINUX=' /etc/selinux/config 2>/dev/null",      "enforcing",   "SELinux enforcing",                   "Set SELINUX=enforcing in /etc/selinux/config"),
        check("grep -c '^[^:]*:[^!*]' /etc/shadow",                       "",            "No empty/default passwords",         "Lock accounts: passwd -l <user>"),
        check("sysctl net.ipv4.ip_forward",                                "= 0",        "IP forwarding disabled",              "sysctl -w net.ipv4.ip_forward=0"),
        check("sysctl net.ipv4.conf.all.accept_redirects",                 "= 0",        "ICMP redirects disabled",             "sysctl -w net.ipv4.conf.all.accept_redirects=0"),
        check("grep -E '^umask' /etc/profile",                             "027",        "Restrictive umask set",               "Set umask 027 in /etc/profile"),
        check("systemctl is-enabled auditd 2>/dev/null",                   "enabled",    "auditd enabled",                      "systemctl enable auditd && systemctl start auditd"),
    ]

    passed = sum(1 for c in controls if c["passed"])
    client.close()

    return {
        "host":        host,
        "controls":    controls,
        "score":       f"{passed}/{len(controls)}",
        "pct":         round(passed / len(controls) * 100),
        "risk_level":  "LOW" if passed >= 8 else "MEDIUM" if passed >= 5 else "HIGH",
    }


def audit_automation_maturity(host: str, username: str, key_path: str = None, password: str = None, port: int = 22) -> dict:
    """
    A8 — Automation & IaC: checks for automation tooling presence and config drift indicators.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {"hostname": host, "username": username, "port": port, "timeout": 10}
    if key_path:
        connect_kwargs["key_filename"] = key_path
    else:
        connect_kwargs["password"] = password

    client.connect(**connect_kwargs)

    tools = {
        "ansible":   _ssh_run(client, "ansible --version 2>/dev/null | head -1"),
        "terraform":  _ssh_run(client, "terraform version 2>/dev/null | head -1"),
        "puppet":     _ssh_run(client, "puppet --version 2>/dev/null"),
        "chef":       _ssh_run(client, "chef-client --version 2>/dev/null"),
        "salt":       _ssh_run(client, "salt --version 2>/dev/null"),
        "git":        _ssh_run(client, "git --version 2>/dev/null"),
        "docker":     _ssh_run(client, "docker --version 2>/dev/null"),
        "podman":     _ssh_run(client, "podman --version 2>/dev/null"),
        "jenkins":    _ssh_run(client, "systemctl is-active jenkins 2>/dev/null"),
    }

    detected = {k: v for k, v in tools.items() if v}
    maturity  = "HIGH" if len(detected) >= 4 else "MEDIUM" if len(detected) >= 2 else "LOW"

    client.close()
    return {"host": host, "tools_detected": detected, "maturity_level": maturity}
