#!/usr/bin/env python3
"""
Scouter 2.0 — API + static file server
Serves the UI on / and exposes /api/latest for live scan results.
Run: uvicorn server:app --host 0.0.0.0 --port 7070
"""
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

REPORTS_DIR = Path(__file__).parent.parent / "reports"
DOCS_DIR    = Path(__file__).parent.parent / "docs"
UI_DIR      = Path(__file__).parent

app = FastAPI()


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
