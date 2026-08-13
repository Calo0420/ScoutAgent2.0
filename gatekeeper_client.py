"""
gatekeeper_client.py
ScoutAgent 2.0 — Gatekeeper Integration
Handles all communication between ScoutAgent and the Gatekeeper AI Trust Gateway.
"""

import os
import time
import json

import requests

GATEKEEPER_URL     = os.getenv("GATEKEEPER_URL", "http://localhost:8001")
GATEKEEPER_ENABLED = os.getenv("GATEKEEPER_ENABLED", "true").lower() == "true"

AGENT_ID   = "scout-001"
AGENT_NAME = "ScoutAgent"

REQUESTED_SCOPE = [
    "scan_linux_environment",
    "check_cis_benchmarks",
    "audit_automation_maturity",
    "scan_network_health",
    "assess_ai_stack",
    "scan_vmware_environment",
    "scan_windows_environment",
    "check_windows_security",
    "generate_executive_report",
]

_session_id = None
_token      = None

_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "reports", "gatekeeper_state.json")


def _write_state(status: str) -> None:
    """Write a small status file so the Scout UI can show live Gatekeeper sync."""
    try:
        os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
        with open(_STATE_FILE, "w") as f:
            json.dump({"enabled": True, "status": status,
                       "session_id": _session_id, "url": GATEKEEPER_URL,
                       "ts": time.time()}, f)
    except Exception:
        pass


def register_session() -> str:
    """
    Register ScoutAgent with Gatekeeper and wait for human approval.
    Returns the session_id once approved.
    """
    global _session_id, _token

    if not GATEKEEPER_ENABLED:
        print("[Gatekeeper] Disabled — running without trust gateway.")
        return None

    print(f"\n[Gatekeeper] Registering ScoutAgent with Gatekeeper at {GATEKEEPER_URL}...")

    resp = requests.post(f"{GATEKEEPER_URL}/session/start", json={
        "agent_id":        AGENT_ID,
        "agent_name":      AGENT_NAME,
        "requested_scope": REQUESTED_SCOPE,
    }, timeout=10)
    resp.raise_for_status()
    data        = resp.json()
    _session_id = data["session_id"]
    _write_state("pending_approval")

    print(f"[Gatekeeper] Session created: {_session_id}")
    print(f"[Gatekeeper] Waiting for human approval...")
    print(f"[Gatekeeper] Approve at: {GATEKEEPER_URL}/session/approve-ui/{_session_id}")
    print(f"[Gatekeeper] Or via the Gatekeeper dashboard at: {GATEKEEPER_URL}")

    while True:
        check = requests.get(f"{GATEKEEPER_URL}/session/{_session_id}/status", timeout=5)
        if check.status_code == 200:
            status_data = check.json()
            if status_data.get("status") == "active":
                _token = status_data.get("token", f"GK-{_session_id}-TOKEN")
                print(f"[Gatekeeper] Session approved! Token: {_token}")
                _write_state("active")
                return _session_id
        time.sleep(2)


def request_access(resource: str, action: str = "execute") -> bool:
    """
    Ask Gatekeeper for permission to access a resource (tool).
    Returns True if allowed, False if blocked.
    """
    if not GATEKEEPER_ENABLED or not _session_id:
        return True

    try:
        resp = requests.post(f"{GATEKEEPER_URL}/access/request", json={
            "session_id": _session_id,
            "token":      _token,
            "resource":   resource,
            "action":     action,
        }, timeout=30)  # generous: a blocked attempt triggers Bedrock analysis server-side
        resp.raise_for_status()
        data    = resp.json()
        allowed = data.get("allowed", False)

        if allowed:
            print(f"[Gatekeeper] ALLOWED: {resource}")
        else:
            print(f"[Gatekeeper] BLOCKED: {resource} — {data.get('reason', 'Outside approved scope')}")
            analysis = data.get("ai_analysis")
            if analysis:
                print(f"[Gatekeeper] Risk Level: {analysis.get('risk_level')}")
                print(f"[Gatekeeper] {analysis.get('risk_explanation')}")

        return allowed

    except Exception as e:
        print(f"[Gatekeeper] Connection error — DENYING by default (fail-closed): {e}")
        return False


def close_session() -> dict:
    """
    Close the ScoutAgent session and trigger Gatekeeper PDF audit report.
    """
    if not GATEKEEPER_ENABLED or not _session_id:
        return {}

    try:
        resp = requests.post(f"{GATEKEEPER_URL}/session/exit", json={
            "session_id": _session_id,
            "token":      _token,
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"\n[Gatekeeper] Session closed.")
        print(f"[Gatekeeper] Total requests: {data.get('total_requests', 0)}")
        print(f"[Gatekeeper] Blocked: {data.get('blocked', 0)}")
        print(f"[Gatekeeper] Audit report: {GATEKEEPER_URL}{data.get('pdf_url', '')}")
        _write_state("closed")
        return data
    except Exception as e:
        print(f"[Gatekeeper] Could not close session: {e}")
        return {}
