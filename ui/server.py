#!/usr/bin/env python3
"""
Scouter 2.0 — API + static file server
Serves the UI on / and exposes /api/latest for live scan results.
Run: uvicorn server:app --host 0.0.0.0 --port 7070
"""
import json
import os
import subprocess
import threading
from pathlib import Path

import paramiko

from fastapi import FastAPI, Body
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

REPORTS_DIR = Path(__file__).parent.parent / "reports"
DOCS_DIR    = Path(__file__).parent.parent / "docs"
UI_DIR      = Path(__file__).parent
ENV_PATH    = Path(__file__).parent.parent / ".env"
AGENT_PATH  = Path(__file__).parent.parent / "agent.py"
PYTHON_PATH = Path(__file__).parent.parent / ".venv" / "bin" / "python3"
ROOT_DIR    = Path(__file__).parent.parent

_scan_lock = threading.Lock()
_scan_proc = None

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
    ssh_dir  = Path("/root/.ssh")
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    key_path = ssh_dir / key_name
    key_path.write_text(key_content)
    key_path.chmod(0o600)
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
            return JSONResponse({"error": "Report file not found"}, status_code=404)

        md_text = md_file.read_text()
        body_html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
        <style>
          body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px;
                 color: #1a2330; margin: 40px 50px; line-height: 1.6; }}
          h1 {{ color: #44546A; font-size: 22px; border-bottom: 2px solid #44546A; padding-bottom: 6px; }}
          h2 {{ color: #44546A; font-size: 16px; margin-top: 28px; }}
          h3 {{ color: #828A91; font-size: 14px; }}
          table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 12px; }}
          th {{ background: #44546A; color: #fff; padding: 6px 10px; text-align: left; }}
          td {{ padding: 5px 10px; border-bottom: 1px solid #ddd; }}
          tr:nth-child(even) {{ background: #f5f7f9; }}
          code, pre {{ background: #f0f4f8; padding: 2px 6px; border-radius: 3px;
                       font-family: monospace; font-size: 11px; }}
          pre {{ padding: 10px; overflow-x: auto; }}
          blockquote {{ border-left: 3px solid #828A91; margin: 8px 0;
                        padding: 4px 12px; color: #828A91; background: #f5f7f9; }}
          hr {{ border: none; border-top: 1px solid #ddd; margin: 20px 0; }}
          @page {{ margin: 2cm; size: A4; }}
        </style></head><body>{body_html}</body></html>"""

        pdf_bytes = HTML(string=html).write_pdf()
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


@app.get("/")
def index():
    return FileResponse(UI_DIR / "index.html")


# Serve any other static assets from ui/
app.mount("/", StaticFiles(directory=str(UI_DIR)), name="static")
