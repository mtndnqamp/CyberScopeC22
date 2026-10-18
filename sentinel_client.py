"""Send CyberScope verifier events to Microsoft Sentinel (Log Analytics) via the Logs Ingestion API.

DRAFT - not yet tested against a real Azure tenant. Uses plain `requests` (no Azure SDK).

Configuration (environment variables or Edge_Node/.env). If any required value is missing,
Sentinel forwarding is silently disabled and the verifier carries on as before.

    SENTINEL_TENANT_ID       Entra ID tenant (directory) ID
    SENTINEL_CLIENT_ID       App registration (client) ID
    SENTINEL_CLIENT_SECRET   App registration client secret
    SENTINEL_DCE_URL         Data collection endpoint "Logs ingestion" URL, e.g. https://xxx.ingest.monitor.azure.com
    SENTINEL_DCR_ID          Data collection rule immutable ID (starts with "dcr-")
    SENTINEL_STREAM          Stream name, default "Custom-CyberScope_CL"

Azure side (see chat instructions): a custom table CyberScope_CL in the Sentinel workspace with
columns   TimeGenerated (datetime), DeviceId (string), Status (string), Severity (string),
          BaselineHash (string), CurrentHash (string), Message (string), Verifier (string)
and a DCR whose stream Custom-CyberScope_CL has the same columns. The app registration needs
the "Monitoring Metrics Publisher" role on the DCR.
"""

import os
import time
from datetime import datetime, timezone

import requests

SCOPE = "https://monitor.azure.com/.default"
API_VERSION = "2023-01-01"
REQUIRED = ("SENTINEL_TENANT_ID", "SENTINEL_CLIENT_ID", "SENTINEL_CLIENT_SECRET",
            "SENTINEL_DCE_URL", "SENTINEL_DCR_ID")

_token = {"value": None, "expires": 0.0}


def enabled():
    return all(os.getenv(name) for name in REQUIRED)


def _login_base():
    # Overridable only so the flow can be tested against a local stub.
    return os.getenv("SENTINEL_LOGIN_URL", "https://login.microsoftonline.com").rstrip("/")


def _get_token(timeout=10):
    if _token["value"] and time.time() < _token["expires"] - 60:
        return _token["value"]
    response = requests.post(
        f"{_login_base()}/{os.environ['SENTINEL_TENANT_ID']}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["SENTINEL_CLIENT_ID"],
            "client_secret": os.environ["SENTINEL_CLIENT_SECRET"],
            "scope": SCOPE,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()
    _token["value"] = body["access_token"]
    _token["expires"] = time.time() + int(body.get("expires_in", 3600))
    return _token["value"]


def send_event(device_id, status, message, baseline_hash=None, current_hash=None,
               severity="Informational", retries=3, timeout=10):
    """Post one event to Sentinel. Returns True on success, False if disabled or failed."""
    if not enabled():
        return False

    record = [{
        "TimeGenerated": datetime.now(timezone.utc).isoformat(),
        "DeviceId": device_id,
        "Status": status,
        "Severity": severity,
        "BaselineHash": baseline_hash or "",
        "CurrentHash": current_hash or "",
        "Message": message,
        "Verifier": "cyberscope-verifier",
    }]
    stream = os.getenv("SENTINEL_STREAM", "Custom-CyberScope_CL")
    url = (f"{os.environ['SENTINEL_DCE_URL'].rstrip('/')}/dataCollectionRules/"
           f"{os.environ['SENTINEL_DCR_ID']}/streams/{stream}?api-version={API_VERSION}")

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(
                url, json=record, timeout=timeout,
                headers={"Authorization": f"Bearer {_get_token()}"},
            )
            if response.status_code in (200, 204):
                return True
            if response.status_code == 401:
                _token["value"] = None  # force a fresh token on retry
            print(f"[sentinel] attempt {attempt}/{retries}: HTTP {response.status_code} {response.text[:200]}")
        except requests.RequestException as error:
            print(f"[sentinel] attempt {attempt}/{retries} failed: {error}")
        time.sleep(min(2 ** attempt, 5))
    return False
