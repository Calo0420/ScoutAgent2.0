#!/usr/bin/env python3
"""
Scouter 2.0 — API + static file server
Serves the UI on / and exposes /api/latest for live scan results.
Run: uvicorn server:app --host 0.0.0.0 --port 7070
"""
import json
from pathlib import Path

from fastapi import FastAPI, Body
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

REPORTS_DIR = Path(__file__).parent.parent / "reports"
DOCS_DIR    = Path(__file__).parent.parent / "docs"
UI_DIR      = Path(__file__).parent
ENV_PATH    = Path(__file__).parent.parent / ".env"

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
        "deploy_mode":  env.get("DEPLOY_MODE", "claude"),
        "demo_mode":    env.get("DEMO_MODE", "false") == "true",
        "client_name":  env.get("CLIENT_NAME", ""),
        "target_host":  env.get("TARGET_HOST", ""),
        "api_key_set":  bool(env.get("ANTHROPIC_API_KEY", "").strip()),
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
    if payload.get("api_key"):    updates["ANTHROPIC_API_KEY"] = payload["api_key"]
    if payload.get("new_password"): updates["OPERATOR_PASSWORD"] = payload["new_password"]
    write_env(updates)
    return JSONResponse({"ok": True})


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
