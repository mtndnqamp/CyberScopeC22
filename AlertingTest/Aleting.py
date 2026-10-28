"""
Send an alert to a Discord channel via webhook.

Setup:
    1. In Discord: Server Settings -> Integrations -> Webhooks -> New Webhook
    2. Copy the webhook URL and paste it below (or set DISCORD_WEBHOOK_URL env var)
    3. pip install requests
    4. python discord_alert.py

Usage as a library:
    from discord_alert import send_discord_alert
    send_discord_alert("Disk usage above 90%", severity="high", source="disk-monitor")
"""

import os
import requests

# Prefer an environment variable so the URL isn't hardcoded/committed to source control.
WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL",
    "https://discord.com/api/webhooks/xx/xx",
)

# Discord embed side-bar colors (decimal) by severity
SEVERITY_COLORS = {
    "critical": 0xE74C3C,  # red
    "high": 0xE67E22,      # orange
    "medium": 0xF1C40F,    # yellow
    "low": 0x2ECC71,       # green
    "info": 0x3498DB,      # blue
}

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
    "info": "🔵",
}


def send_discord_alert(message, severity="info", source=None, retries=3, timeout=5):
    """
    Send an alert to Discord via webhook.

    Args:
        message: The alert text.
        severity: One of 'critical', 'high', 'medium', 'low', 'info'.
        source: Optional string identifying where the alert came from.
        retries: Number of attempts before giving up.
        timeout: Per-request timeout in seconds.

    Returns:
        True if Discord accepted the message, False otherwise.
    """
    severity = severity.lower()
    color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["info"])
    emoji = SEVERITY_EMOJI.get(severity, "⚪")

    embed = {
        "title": f"{emoji} {severity.upper()} Alert",
        "description": message,
        "color": color,
        "fields": [],
        "timestamp": None,  # Discord fills this in as "now" if omitted; set explicitly below
    }

    import datetime
    embed["timestamp"] = datetime.datetime.utcnow().isoformat()

    if source:
        embed["fields"].append({"name": "Source", "value": source, "inline": True})

    payload = {"embeds": [embed]}

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(WEBHOOK_URL, json=payload, timeout=timeout)
            # Discord returns 204 No Content on success
            if response.status_code in (200, 204):
                return True
            print(f"Discord webhook returned {response.status_code}: {response.text}")
        except requests.RequestException as e:
            print(f"Attempt {attempt}/{retries} failed: {e}")
    return False


if __name__ == "__main__":
    ok = send_discord_alert(
        "Suspicious login detected from 10.0.0.5",
        severity="high",
        source="my-python-script",
    )
    print("Alert sent." if ok else "Alert failed to send.")
