"""
Windows Scout Tools — covers A1 (Fast Track) + A2 (Hardening Sprint) for Windows
Connects via WinRM using PowerShell. Zero writes to client environment.
Requires: pip install pywinrm
"""
import json
from datetime import datetime

try:
    import winrm
    WINRM_AVAILABLE = True
except ImportError:
    WINRM_AVAILABLE = False


def _ps_run(session, script):
    """Execute a PowerShell command and return stdout."""
    result = session.run_ps(script)
    if result.status_code == 0:
        return result.std_out.decode("utf-8", errors="replace").strip()
    return f"ERROR: {result.std_err.decode('utf-8', errors='replace').strip()}"


def scan_windows_environment(
    host: str,
    username: str,
    password: str,
    port: int = 5985,
    use_ssl: bool = False
) -> dict:
    """
    A1 — Windows Fast Track: rapid environment snapshot via WinRM.
    Returns OS info, CPU/RAM/disk, uptime, users, open ports, patch status.
    Read-only. No changes made to the target system.

    Prerequisites on target:
      - WinRM enabled: winrm quickconfig
      - Allow basic auth: Set-Item WSMan:\\localhost\\Service\\Auth\\Basic $true
      - Firewall: port 5985 (HTTP) or 5986 (HTTPS)
    """
    if not WINRM_AVAILABLE:
        return {
            "error": "pywinrm not installed. Run: pip install pywinrm",
            "host": host,
            "scanned_at": datetime.utcnow().isoformat(),
        }

    try:
        protocol = "https" if use_ssl else "http"
        session = winrm.Session(
            f"{protocol}://{host}:{port}/wsman",
            auth=(username, password),
            transport="basic",
            server_cert_validation="ignore" if use_ssl else "ignore"
        )

        findings = {
            "host": host,
            "scanned_at": datetime.utcnow().isoformat(),
            "os": _ps_run(session, "(Get-WmiObject Win32_OperatingSystem).Caption"),
            "os_version": _ps_run(session, "[System.Environment]::OSVersion.Version.ToString()"),
            "os_build": _ps_run(session, "(Get-WmiObject Win32_OperatingSystem).BuildNumber"),
            "kernel": _ps_run(session, "(Get-WmiObject Win32_OperatingSystem).Version"),
            "uptime": _ps_run(session, """
                $os = Get-WmiObject Win32_OperatingSystem
                $uptime = (Get-Date) - $os.ConvertToDateTime($os.LastBootUpTime)
                "$([int]$uptime.TotalDays)d $($uptime.Hours)h $($uptime.Minutes)m"
            """),
            "last_reboot": _ps_run(session, """
                $os = Get-WmiObject Win32_OperatingSystem
                $os.ConvertToDateTime($os.LastBootUpTime).ToString("yyyy-MM-dd HH:mm:ss")
            """),
            "cpu_cores": _ps_run(session, "(Get-WmiObject Win32_Processor | Measure-Object NumberOfCores -Sum).Sum"),
            "cpu_name": _ps_run(session, "(Get-WmiObject Win32_Processor | Select-Object -First 1).Name"),
            "ram_gb": _ps_run(session, "[math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)"),
            "disk_usage": _ps_run(session, """
                Get-WmiObject Win32_LogicalDisk -Filter "DriveType=3" |
                ForEach-Object {
                    $used = [math]::Round(($_.Size - $_.FreeSpace) / 1GB, 1)
                    $total = [math]::Round($_.Size / 1GB, 1)
                    $pct = [math]::Round((($_.Size - $_.FreeSpace) / $_.Size) * 100, 0)
                    "$($_.DeviceID) ${used}GB used of ${total}GB ($pct%)"
                } | Out-String
            """),
            "logged_users": _ps_run(session, "query user 2>$null | Select-Object -Skip 1 | ForEach-Object { $_.Substring(1,20).Trim() } | Where-Object { $_ }"),
            "local_admins": _ps_run(session, """
                $group = [ADSI]"WinNT://./Administrators,group"
                $group.Members() | ForEach-Object { $_.GetType().InvokeMember("Name","GetProperty",$null,$_,$null) }
            """),
            "open_ports": _ps_run(session, """
                netstat -an | Where-Object { $_ -match "LISTENING" } |
                ForEach-Object { ($_ -split '\s+')[2] } |
                ForEach-Object { ($_ -split ':')[-1] } |
                Sort-Object { [int]$_ } -Unique | Out-String
            """),
            "last_patch": _ps_run(session, """
                $patches = Get-WmiObject Win32_QuickFixEngineering | Sort-Object InstalledOn -Descending
                if ($patches) { "$($patches[0].HotFixID) installed $($patches[0].InstalledOn)" }
                else { "No patches found" }
            """),
            "pending_updates": _ps_run(session, """
                try {
                    $updateSession = New-Object -ComObject Microsoft.Update.Session
                    $updateSearcher = $updateSession.CreateUpdateSearcher()
                    $updates = $updateSearcher.Search("IsInstalled=0 and IsHidden=0")
                    "$($updates.Updates.Count) updates pending"
                } catch { "Unable to query Windows Update" }
            """),
            "running_services": _ps_run(session, "(Get-Service | Where-Object Status -eq 'Running').Count"),
            "installed_software_count": _ps_run(session, """
                (Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* 2>$null).Count +
                (Get-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* 2>$null).Count
            """),
        }

        return findings

    except Exception as e:
        return {
            "error": str(e),
            "host": host,
            "scanned_at": datetime.utcnow().isoformat(),
            "connection_tip": "Ensure WinRM is enabled: winrm quickconfig && Set-Item WSMan:\\localhost\\Service\\Auth\\Basic $true"
        }


def check_windows_security(
    host: str,
    username: str,
    password: str,
    port: int = 5985,
    use_ssl: bool = False
) -> dict:
    """
    A2 — Windows Hardening: Security configuration checks.
    Checks firewall, RDP, password policy, audit logging, patch gaps.
    Read-only. No changes made to the target system.
    """
    if not WINRM_AVAILABLE:
        return {
            "error": "pywinrm not installed. Run: pip install pywinrm",
            "host": host,
            "scanned_at": datetime.utcnow().isoformat(),
        }

    try:
        protocol = "https" if use_ssl else "http"
        session = winrm.Session(
            f"{protocol}://{host}:{port}/wsman",
            auth=(username, password),
            transport="basic",
            server_cert_validation="ignore"
        )

        checks = {}

        # Firewall status
        fw_raw = _ps_run(session, """
            $profiles = Get-NetFirewallProfile
            $profiles | ForEach-Object { "$($_.Name): $($_.Enabled)" } | Out-String
        """)
        checks["firewall_enabled"] = "False" not in fw_raw
        checks["firewall_detail"] = fw_raw.strip()

        # RDP exposed
        rdp_raw = _ps_run(session, """
            $rdp = Get-ItemProperty "HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server" -Name "fDenyTSConnections" 2>$null
            if ($rdp.fDenyTSConnections -eq 0) { "RDP ENABLED" } else { "RDP DISABLED" }
        """)
        checks["rdp_enabled"] = "RDP ENABLED" in rdp_raw
        checks["rdp_status"] = rdp_raw.strip()

        # Windows Defender
        defender_raw = _ps_run(session, """
            try {
                $av = Get-MpComputerStatus 2>$null
                "RealTime: $($av.RealTimeProtectionEnabled), Sigs updated: $($av.AntivirusSignatureLastUpdated)"
            } catch { "Defender status unavailable" }
        """)
        checks["defender_realtime"] = "True" in defender_raw
        checks["defender_detail"] = defender_raw.strip()

        # Password policy
        pass_policy = _ps_run(session, "net accounts 2>$null | Select-String 'Minimum password length|Maximum password age|Password history' | Out-String")
        checks["password_policy"] = pass_policy.strip()

        # Audit policy
        audit_raw = _ps_run(session, "auditpol /get /category:'Logon/Logoff' 2>$null | Select-String 'Logon|Logoff' | Out-String")
        checks["audit_policy"] = audit_raw.strip()

        # Failed login attempts (last 24h)
        failed_logins = _ps_run(session, """
            try {
                $events = Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4625; StartTime=(Get-Date).AddHours(-24)} -ErrorAction SilentlyContinue
                if ($events) { "$($events.Count) failed login attempts in last 24h" } else { "0 failed login attempts in last 24h" }
            } catch { "Unable to query Security log (may need admin)" }
        """)
        checks["failed_logins_24h"] = failed_logins.strip()

        # UAC status
        uac_raw = _ps_run(session, """
            $uac = Get-ItemProperty HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System -Name EnableLUA 2>$null
            if ($uac.EnableLUA -eq 1) { "UAC ENABLED" } else { "UAC DISABLED" }
        """)
        checks["uac_enabled"] = "UAC ENABLED" in uac_raw
        checks["uac_status"] = uac_raw.strip()

        # Auto-logon (security risk)
        autologon = _ps_run(session, """
            $al = Get-ItemProperty "HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon" -Name AutoAdminLogon 2>$null
            if ($al.AutoAdminLogon -eq "1") { "AUTO-LOGON ENABLED (HIGH RISK)" } else { "Auto-logon disabled" }
        """)
        checks["auto_logon"] = autologon.strip()

        # SMB v1 (EternalBlue risk)
        smb1_raw = _ps_run(session, """
            try {
                $smb = Get-WindowsOptionalFeature -Online -FeatureName SMB1Protocol 2>$null
                if ($smb.State -eq "Enabled") { "SMBv1 ENABLED (HIGH RISK)" } else { "SMBv1 disabled" }
            } catch {
                $smb = Get-SmbServerConfiguration 2>$null
                if ($smb.EnableSMB1Protocol) { "SMBv1 ENABLED (HIGH RISK)" } else { "SMBv1 disabled" }
            }
        """)
        checks["smb_v1"] = smb1_raw.strip()

        # Score
        score = 0
        if checks.get("firewall_enabled"): score += 1
        if not checks.get("rdp_enabled"): score += 1
        if checks.get("defender_realtime"): score += 1
        if checks.get("uac_enabled"): score += 1
        if "AUTO-LOGON ENABLED" not in checks.get("auto_logon", ""): score += 1
        if "SMBv1 ENABLED" not in checks.get("smb_v1", ""): score += 1

        checks["cis_score"] = f"{score}/6"
        checks["risk_level"] = "LOW" if score >= 5 else "MEDIUM" if score >= 3 else "HIGH"
        checks["host"] = host
        checks["scanned_at"] = datetime.utcnow().isoformat()

        return checks

    except Exception as e:
        return {
            "error": str(e),
            "host": host,
            "scanned_at": datetime.utcnow().isoformat(),
        }
