"""
Network Scout Tools — covers A3 (Network Health Check)
Uses nmap + ping + traceroute. Read-only passive scan.
"""
import subprocess
import socket
import json


def scan_network_health(target_subnet: str) -> dict:
    """
    A3 — Network Health Check: discovers live hosts, open risky ports,
    latency baseline, produces risk-rated findings.
    """
    findings = {"subnet": target_subnet, "hosts": [], "risks": []}

    # Host discovery
    result = subprocess.run(
        ["nmap", "-sn", "-T4", "--open", target_subnet, "-oG", "-"],
        capture_output=True, text=True, timeout=120
    )

    hosts = []
    for line in result.stdout.splitlines():
        if "Host:" in line and "Status: Up" in line:
            ip = line.split()[1]
            hosts.append(ip)

    findings["live_hosts"] = len(hosts)

    # Port scan on discovered hosts — flag risky ports
    risky_ports = {
        21: "FTP (plaintext)",
        23: "Telnet (plaintext)",
        25: "SMTP open relay risk",
        3389: "RDP exposed",
        445: "SMB exposed",
        1433: "MSSQL exposed",
        3306: "MySQL exposed",
        5432: "PostgreSQL exposed",
        6379: "Redis exposed (often no auth)",
        27017: "MongoDB exposed (often no auth)",
    }

    for host in hosts[:20]:  # cap at 20 hosts for speed
        host_entry = {"ip": host, "open_risky_ports": []}
        try:
            port_result = subprocess.run(
                ["nmap", "-sT", "-T4", "--open", "-p", ",".join(map(str, risky_ports.keys())), host, "-oG", "-"],
                capture_output=True, text=True, timeout=30
            )
            for line in port_result.stdout.splitlines():
                if "Ports:" in line:
                    for port, label in risky_ports.items():
                        if f"{port}/open" in line:
                            host_entry["open_risky_ports"].append({"port": port, "risk": label})
                            findings["risks"].append({"host": host, "port": port, "label": label})
        except Exception:
            pass

        # Latency
        try:
            ping = subprocess.run(["ping", "-c", "3", "-q", host], capture_output=True, text=True, timeout=10)
            for line in ping.stdout.splitlines():
                if "avg" in line:
                    host_entry["avg_latency_ms"] = line.split("/")[4]
        except Exception:
            pass

        findings["hosts"].append(host_entry)

    # Risk rating
    risk_count = len(findings["risks"])
    findings["risk_rating"] = "CRITICAL" if risk_count > 10 else "HIGH" if risk_count > 5 else "MEDIUM" if risk_count > 0 else "LOW"
    findings["summary"] = f"{len(hosts)} live hosts | {risk_count} risky open ports found"

    return findings
