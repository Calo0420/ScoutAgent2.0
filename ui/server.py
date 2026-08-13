#!/usr/bin/env python3
"""
Scouter 2.0 — API + static file server
Serves the UI on / and exposes /api/latest for live scan results.
Run: uvicorn server:app --host 0.0.0.0 --port 7070
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import paramiko
import requests

from fastapi import FastAPI, Body
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

REPORTS_DIR = Path(__file__).parent.parent / "reports"
DOCS_DIR    = Path(__file__).parent.parent / "docs"
UI_DIR      = Path(__file__).parent
ENV_PATH    = Path(__file__).parent.parent / ".env"
AGENT_PATH  = Path(__file__).parent.parent / "agent.py"
PYTHON_PATH = (
    Path(__file__).parent.parent / ".venv" / "Scripts" / "python.exe"
    if sys.platform == "win32"
    else Path(__file__).parent.parent / ".venv" / "bin" / "python3"
)
ROOT_DIR    = Path(__file__).parent.parent

_scan_lock = threading.Lock()
_scan_proc = None
_process_started_at = time.time()

DEFAULT_OPERATOR_PASSWORD = "scouter2"

app = FastAPI()


# ── Settings helpers ──────────────────────────────────────────────────────────

def read_env() -> dict:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                env[k.strip()] = v.strip()
    return env


def write_env(updates: dict):
    lines = []
    updated_keys = set()
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                k = stripped.partition('=')[0].strip()
                if k in updates:
                    lines.append(f"{k}={updates[k]}")
                    updated_keys.add(k)
                else:
                    lines.append(line)
            else:
                lines.append(line)
    for k, v in updates.items():
        if k not in updated_keys:
            lines.append(f"{k}={v}")
    ENV_PATH.write_text('\n'.join(lines) + '\n')


def _get_git_version() -> dict:
    """Best-effort git commit info — never raises, always returns something."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT_DIR), capture_output=True, text=True, timeout=3
        ).stdout.strip() or "unknown"
        commit_date = subprocess.run(
            ["git", "log", "-1", "--format=%ai"],
            cwd=str(ROOT_DIR), capture_output=True, text=True, timeout=3
        ).stdout.strip() or "unknown"
        return {"commit": commit, "commit_date": commit_date}
    except Exception:
        return {"commit": "unknown", "commit_date": "unknown"}


@app.get("/api/version")
def api_version():
    """
    Version + health snapshot. The first thing a real IT specialist checks
    before trusting a tool — what's actually running, how long has it been
    up, and is the trust layer (Gatekeeper) even reachable right now.
    Every sub-check is best-effort and time-boxed so this endpoint itself
    can never hang or crash the server.
    """
    env = read_env()
    git_info = _get_git_version()
    uptime_seconds = round(time.time() - _process_started_at)

    gatekeeper_enabled = env.get("GATEKEEPER_ENABLED", "true").lower() == "true"
    gatekeeper_url = env.get("GATEKEEPER_URL", "http://localhost:8001")
    gatekeeper_status = "disabled"
    gatekeeper_latency_ms = None
    if gatekeeper_enabled:
        try:
            t0 = time.time()
            resp = requests.get(f"{gatekeeper_url}/", timeout=3)
            gatekeeper_latency_ms = round((time.time() - t0) * 1000)
            gatekeeper_status = "reachable" if resp.status_code < 500 else "error"
        except requests.exceptions.RequestException:
            gatekeeper_status = "unreachable"

    return JSONResponse({
        "service": "ScoutAgent",
        "commit": git_info["commit"],
        "commit_date": git_info["commit_date"],
        "deploy_mode": env.get("DEPLOY_MODE", "claude"),
        "uptime_seconds": uptime_seconds,
        "scan_currently_running": bool(_scan_proc and _scan_proc.poll() is None),
        "gatekeeper": {
            "enabled": gatekeeper_enabled,
            "session_gating": env.get("GATEKEEPER_SESSION", "false").lower() == "true",
            "url": gatekeeper_url,
            "status": gatekeeper_status,
            "latency_ms": gatekeeper_latency_ms,
        },
    })


@app.post("/api/settings/auth")
def auth_settings(payload: dict = Body(...)):
    env = read_env()
    password = env.get("OPERATOR_PASSWORD", DEFAULT_OPERATOR_PASSWORD)
    if payload.get("password") == password:
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "Invalid password"}, status_code=401)


@app.get("/api/settings")
def get_settings():
    env = read_env()
    return JSONResponse({
        "deploy_mode":        env.get("DEPLOY_MODE", "claude"),
        "demo_mode":          env.get("DEMO_MODE", "false") == "true",
        "client_name":        env.get("CLIENT_NAME", ""),
        "target_host":        env.get("TARGET_HOST", ""),
        "ssh_user":           env.get("SSH_USER", "root"),
        "ssh_key":            env.get("SSH_KEY", ""),
        "ssh_port":           int(env.get("SSH_PORT", "22") or "22"),
        "ssh_password_set":   bool(env.get("SSH_PASSWORD", "").strip()),
        "subnet":             env.get("SUBNET", ""),
        "vcenter_host":       env.get("VCENTER_HOST", ""),
        "vcenter_user":       env.get("VCENTER_USER", ""),
        "include_vmware":     bool(env.get("VCENTER_HOST", "").strip()),
        "api_key_set":        bool(env.get("ANTHROPIC_API_KEY", "").strip()),
        "venice_api_key_set": bool(env.get("VENICE_API_KEY", "").strip()),
        "venice_model":       env.get("VENICE_MODEL", "llama-3.3-70b"),
    })


@app.post("/api/settings")
def save_settings(payload: dict = Body(...)):
    env = read_env()
    password = env.get("OPERATOR_PASSWORD", DEFAULT_OPERATOR_PASSWORD)
    if payload.get("password") != password:
        return JSONResponse({"ok": False, "error": "Invalid password"}, status_code=401)
    updates = {}
    if "deploy_mode"  in payload: updates["DEPLOY_MODE"]  = payload["deploy_mode"]
    if "demo_mode"    in payload: updates["DEMO_MODE"]    = "true" if payload["demo_mode"] else "false"
    if "client_name"  in payload: updates["CLIENT_NAME"]  = payload["client_name"]
    if "target_host"  in payload: updates["TARGET_HOST"]  = payload["target_host"]
    if "ssh_user"     in payload: updates["SSH_USER"]     = payload["ssh_user"]
    if "ssh_key"      in payload: updates["SSH_KEY"]      = payload["ssh_key"]
    if "ssh_port"      in payload: updates["SSH_PORT"]      = str(payload["ssh_port"])
    if "ssh_password"  in payload: updates["SSH_PASSWORD"]  = payload["ssh_password"]
    if "subnet"        in payload: updates["SUBNET"]        = payload["subnet"]
    if "vcenter_host"  in payload: updates["VCENTER_HOST"]  = payload["vcenter_host"]
    if "vcenter_user"  in payload: updates["VCENTER_USER"]  = payload["vcenter_user"]
    if payload.get("vcenter_pass"):    updates["VCENTER_PASS"]      = payload["vcenter_pass"]
    if payload.get("api_key"):         updates["ANTHROPIC_API_KEY"] = payload["api_key"]
    if payload.get("venice_api_key"):  updates["VENICE_API_KEY"]    = payload["venice_api_key"]
    if payload.get("venice_model"):    updates["VENICE_MODEL"]       = payload["venice_model"]
    if payload.get("new_password"):    updates["OPERATOR_PASSWORD"]  = payload["new_password"]
    write_env(updates)
    return JSONResponse({"ok": True})


@app.post("/api/settings/ssh-key")
def save_ssh_key(payload: dict = Body(...)):
    """Accepts pasted private key content, writes it to /root/.ssh/ with correct permissions."""
    key_content = payload.get("key_content", "").strip()
    key_name    = payload.get("key_name", "scout_client_key").strip().replace("/", "_").replace(" ", "_")
    if not key_content:
        return JSONResponse({"ok": False, "error": "No key content provided"}, status_code=400)
    if not key_content.startswith("-----BEGIN"):
        return JSONResponse({"ok": False, "error": "Does not look like a valid private key"}, status_code=400)
    # Normalize — browsers often collapse line breaks in textareas.
    # Re-wrap the base64 body at 70 chars so OpenSSH accepts it.
    lines   = key_content.replace("\r", "").split("\n")
    header  = next((l for l in lines if l.startswith("-----BEGIN")), "")
    footer  = next((l for l in lines if l.startswith("-----END")), "")
    body    = "".join(l for l in lines if not l.startswith("-----"))
    wrapped = "\n".join(body[i:i+70] for i in range(0, len(body), 70))
    key_content = f"{header}\n{wrapped}\n{footer}\n"
    ssh_dir  = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    key_path = ssh_dir / key_name
    key_path.write_text(key_content)
    try:
        key_path.chmod(0o600)  # no-op on Windows, correct on Linux/macOS
    except NotImplementedError:
        pass
    write_env({"SSH_KEY": str(key_path)})
    return JSONResponse({"ok": True, "path": str(key_path)})


@app.post("/api/test-connection")
def test_connection(payload: dict = Body(...)):
    """Tries an SSH connection with current settings and returns success/failure."""
    host     = payload.get("host", "").strip()
    user     = payload.get("user", "root").strip()
    key_path = payload.get("key_path", "").strip()
    password = payload.get("password", "").strip()
    port     = int(payload.get("port", 22) or 22)
    if not host:
        return JSONResponse({"ok": False, "error": "No target host configured"})
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = {"hostname": host, "username": user, "port": port, "timeout": 10}
        if key_path:
            kwargs["key_filename"] = key_path
        elif password:
            kwargs["password"] = password
        client.connect(**kwargs)
        _, stdout, _ = client.exec_command("uname -srm && hostname")
        result = stdout.read().decode().strip()
        client.close()
        return JSONResponse({"ok": True, "message": result or "Connected successfully"})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


@app.post("/api/run")
def run_scan():
    global _scan_proc
    env = read_env()
    with _scan_lock:
        if _scan_proc and _scan_proc.poll() is None:
            return JSONResponse({"ok": False, "error": "Scan already running"}, status_code=409)

        demo_mode    = env.get("DEMO_MODE", "false").lower() == "true"
        client_name  = env.get("CLIENT_NAME", "Client") or "Client"
        target_host  = env.get("TARGET_HOST", "")
        ssh_user     = env.get("SSH_USER", "root") or "root"
        ssh_key      = env.get("SSH_KEY", "")
        ssh_port     = env.get("SSH_PORT", "22") or "22"
        ssh_password = env.get("SSH_PASSWORD", "")
        subnet       = env.get("SUBNET", "")
        vcenter_host = env.get("VCENTER_HOST", "")
        vcenter_user = env.get("VCENTER_USER", "")
        vcenter_pass = env.get("VCENTER_PASS", "")

        cmd = [str(PYTHON_PATH), str(AGENT_PATH), "--client", client_name]
        if demo_mode or not target_host:
            cmd.append("--demo")
        else:
            cmd += ["--host", target_host, "--user", ssh_user, "--port", ssh_port]
            if ssh_key:
                cmd += ["--key", ssh_key]
            elif ssh_password:
                cmd += ["--password", ssh_password]
            if subnet:
                cmd += ["--subnet", subnet]
            if vcenter_host and vcenter_user:
                cmd += ["--vcenter", vcenter_host, "--vc-user", vcenter_user]
                if vcenter_pass:
                    cmd += ["--vc-pass", vcenter_pass]

        env_vars = os.environ.copy()
        env_vars["ANTHROPIC_API_KEY"] = env.get("ANTHROPIC_API_KEY", "")
        env_vars["DEPLOY_MODE"]       = env.get("DEPLOY_MODE", "claude")
        env_vars["VENICE_API_KEY"]    = env.get("VENICE_API_KEY", "")
        env_vars["VENICE_MODEL"]      = env.get("VENICE_MODEL", "llama-3.3-70b")
        env_vars["GATEKEEPER_ENABLED"] = env.get("GATEKEEPER_ENABLED", "true")
        env_vars["GATEKEEPER_URL"]     = env.get("GATEKEEPER_URL", "http://localhost:8001")
        env_vars["GATEKEEPER_SESSION"] = env.get("GATEKEEPER_SESSION", "false")

        _scan_proc = subprocess.Popen(cmd, cwd=str(ROOT_DIR), env=env_vars)

    return JSONResponse({"ok": True, "message": "Scan started"})


@app.get("/api/run/status")
def run_status():
    global _scan_proc
    if _scan_proc is None:
        return JSONResponse({"running": False, "status": "idle"})
    poll = _scan_proc.poll()
    if poll is None:
        return JSONResponse({"running": True, "status": "scanning"})
    return JSONResponse({"running": False, "status": "complete" if poll == 0 else "error", "exit_code": poll})



def _pdf_heat_map(html: str) -> str:
    """Replace ASCII heat map code block with a color-coded 5x5 HTML table."""
    pattern = re.compile(r'<pre><code>(IMPACT.*?)</code></pre>', re.DOTALL | re.IGNORECASE)

    def _color(lik, imp):
        s = lik * imp
        if s >= 20: return '#c0392b', '#fff'
        if s >= 12: return '#e67e22', '#fff'
        if s >= 6:  return '#f1c40f', '#333'
        return '#27ae60', '#fff'

    impact_hdrs  = ['Low (1)', 'Med (2)', 'High (3)', 'V.High (4)', 'Critical (5)']
    lik_labels   = ['5 — Very High', '4 — High', '3 — Medium', '2 — Low', '1 — Minimal']
    lik_values   = [5, 4, 3, 2, 1]

    def build(m):
        data_lines = [l for l in m.group(1).split('\n') if '|' in l]
        out = ['<table class="heat-map-tbl"><thead><tr>',
               '<th style="background:#2c3e50;color:#fff;padding:6px 8px;font-size:11px;">Likelihood ↓ / Impact →</th>']
        for h in impact_hdrs:
            out.append(f'<th style="background:#2c3e50;color:#fff;padding:6px 8px;font-size:11px;text-align:center;">{h}</th>')
        out.append('</tr></thead><tbody>')
        for i, line in enumerate(data_lines[:5]):
            lik = lik_values[i] if i < 5 else 1
            cells = [p.strip() for p in line.split('|')[1:6]]
            while len(cells) < 5: cells.append('')
            out.append(f'<tr><th style="background:#34495e;color:#fff;padding:6px 8px;font-size:10px;text-align:right;white-space:nowrap;">{lik_labels[i]}</th>')
            for j, txt in enumerate(cells):
                bg, fg = _color(lik, j + 1)
                out.append(f'<td style="background:{bg};color:{fg};text-align:center;padding:7px 5px;font-size:10px;word-break:break-word;">{txt if txt else "&nbsp;"}</td>')
            out.append('</tr>')
        out.append('</tbody></table>')
        return '\n'.join(out)

    return pattern.sub(build, html, count=1)


def _pdf_risk_register(html: str) -> str:
    """Tag the Risk Register table so CSS column widths apply."""
    return re.sub(
        r'(Risk Register</h[23]>.*?)<table(?!\s+class)',
        r'\1<table class="risk-register"',
        html, count=1, flags=re.DOTALL | re.IGNORECASE
    )



def _pdf_normalize_emoji(html: str) -> str:
    """Replace emoji with DejaVu-renderable HTML spans (EC2 has no emoji font)."""
    _EMOJI = [
        ('🚫', '<span style="color:#c0392b;font-weight:bold">✗</span>'),
        ('🔴', '<span style="color:#c0392b;font-weight:bold">●</span>'),
        ('🟠', '<span style="color:#e67e22;font-weight:bold">●</span>'),
        ('🟡', '<span style="color:#e6b400;font-weight:bold">●</span>'),
        ('🟢', '<span style="color:#27ae60;font-weight:bold">●</span>'),
        ('🟣', '<span style="color:#8e44ad;font-weight:bold">●</span>'),
        ('🔵', '<span style="color:#2980b9;font-weight:bold">●</span>'),
        ('✅',     '<span style="color:#27ae60;font-weight:bold">✓</span>'),
        ('❌',     '<span style="color:#c0392b;font-weight:bold">✗</span>'),
        ('⚠️', '<span style="color:#e67e22;font-weight:bold">▲</span>'),
        ('⚠',     '<span style="color:#e67e22;font-weight:bold">▲</span>'),
        ('🌐', '<span style="color:#2980b9">●</span>'),
        ('📌', '►'),
        ('🗓️', ''), ('🗓', ''),
        ('🛡️', ''), ('🛡', ''),
        ('🔒', ''), ('🔧', ''), ('🧠', ''),
        ('📊', ''), ('📋', ''), ('📱', ''),
        ('🤖', ''), ('🤝', ''), ('💰', ''),
        ('🖥️', ''), ('🖥', ''),
        ('🎯', ''), ('⭐', ''),
    ]
    for emoji, repl in _EMOJI:
        html = html.replace(emoji, repl)
    return html

def _pdf_postprocess(html: str) -> str:
    html = _pdf_normalize_emoji(html)
    html = _pdf_heat_map(html)
    html = _pdf_risk_register(html)
    return html

@app.get("/api/report/latest")
def download_latest_report():
    """Convert latest scan report to PDF and serve for download."""
    latest_json = REPORTS_DIR / "latest.json"
    if not latest_json.exists():
        return JSONResponse({"error": "No scan report available"}, status_code=404)
    try:
        import markdown
        from weasyprint import HTML, CSS
        from fastapi.responses import Response

        data = json.loads(latest_json.read_text())
        scan_id = data.get("scan_id", "report")
        md_file = REPORTS_DIR / f"{scan_id}.md"
        if not md_file.exists():
            status = data.get("status", "")
            if status == "scanning":
                return JSONResponse({"error": "Scan still in progress — report not ready yet. Wait for the scan to complete."}, status_code=404)
            return JSONResponse({"error": f"Report file not found for scan {scan_id}"}, status_code=404)

        md_text = md_file.read_text()
        body_html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
        body_html = _pdf_postprocess(body_html)

        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
        <style>
          body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px;
                 color: #1a2330; margin: 40px 50px; line-height: 1.6; }}
          h1 {{ color: #44546A; font-size: 22px; border-bottom: 2px solid #44546A; padding-bottom: 6px; }}
          h2 {{ color: #44546A; font-size: 16px; margin-top: 28px; }}
          h3 {{ color: #828A91; font-size: 14px; }}
          table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 12px; }}
          th {{ background: #44546A; color: #fff; padding: 6px 10px; text-align: left; }}
          td {{ padding: 5px 10px; border-bottom: 1px solid #ddd; word-break: break-word; overflow-wrap: break-word; }}
          tr:nth-child(even) {{ background: #f5f7f9; }}
          code, pre {{ background: #f0f4f8; padding: 2px 6px; border-radius: 3px;
                       font-family: monospace; font-size: 11px; }}
          pre {{ padding: 10px; white-space: pre-wrap; word-wrap: break-word; overflow-wrap: break-word; }}
          blockquote {{ border-left: 3px solid #828A91; margin: 8px 0;
                        padding: 4px 12px; color: #828A91; background: #f5f7f9; }}
          hr {{ border: none; border-top: 1px solid #ddd; margin: 20px 0; }}
          @page {{ margin: 2cm; size: A4; }}
          .heat-map-tbl {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
          .heat-map-tbl th, .heat-map-tbl td {{ border: 1px solid #aaa; }}
          .risk-register {{ table-layout: fixed; width: 100%; }}
          .risk-register th:nth-child(1), .risk-register td:nth-child(1) {{ width: 4%; }}
          .risk-register th:nth-child(2), .risk-register td:nth-child(2) {{ width: 40%; word-break: break-word; overflow-wrap: break-word; }}
          .risk-register th:nth-child(3), .risk-register td:nth-child(3) {{ width: 13%; word-break: break-word; }}
          .risk-register th:nth-child(4), .risk-register td:nth-child(4) {{ width: 9%; text-align: center; }}
          .risk-register th:nth-child(5), .risk-register td:nth-child(5) {{ width: 9%; text-align: center; word-break: break-word; }}
          .risk-register th:nth-child(6), .risk-register td:nth-child(6) {{ width: 9%; text-align: center; }}
          .risk-register th:nth-child(7), .risk-register td:nth-child(7) {{ width: 16%; text-align: left; word-break: break-word; overflow-wrap: break-word; }}
          td code {{ white-space: normal; word-break: break-all; }}
        </style></head><body>
        <img src="everforth_logo.png" style="height:46px;display:block;margin:0 0 18px 0"/>
        {body_html}</body></html>"""

        pdf_bytes = HTML(string=html, base_url=UI_DIR.as_uri() + "/").write_pdf()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={scan_id}.pdf"}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/latest")
def get_latest():
    latest = REPORTS_DIR / "latest.json"
    if not latest.exists():
        return JSONResponse({"status": "no_scan", "message": "No scan results yet. Run the Scout Agent first."}, status_code=404)
    try:
        return JSONResponse(json.loads(latest.read_text()))
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/scans")
def list_scans():
    """Returns a list of all completed scan reports."""
    scans = sorted(REPORTS_DIR.glob("*.json"), reverse=True)
    results = []
    for f in scans:
        if f.name in ("latest.json", "latest.json.tmp"):
            continue
        try:
            data = json.loads(f.read_text())
            results.append({
                "file":       f.name,
                "scan_id":    data.get("scan_id", f.stem),
                "client":     data.get("client", ""),
                "scanned_at": data.get("scanned_at", ""),
                "status":     data.get("status", ""),
            })
        except Exception:
            pass
    return JSONResponse(results)


@app.get("/manual/client-it")
def manual_client_it():
    """Serves the Client IT Team manual."""
    return FileResponse(DOCS_DIR / "manual_client_it.html", media_type="text/html")


@app.get("/manual/sales")
def manual_sales():
    """Serves the Sales Playbook manual."""
    return FileResponse(DOCS_DIR / "manual_sales.html", media_type="text/html")


@app.get("/api/gatekeeper")
def gatekeeper_status():
    """Live Gatekeeper session state for the Scout UI sync indicator."""
    p = ROOT_DIR / "reports" / "gatekeeper_state.json"
    if not p.exists():
        return JSONResponse({"enabled": False})
    try:
        return JSONResponse(json.loads(p.read_text()))
    except Exception:
        return JSONResponse({"enabled": False})


@app.get("/")
def index():
    return FileResponse(UI_DIR / "index.html")


# Serve any other static assets from ui/
app.mount("/", StaticFiles(directory=str(UI_DIR)), name="static")
