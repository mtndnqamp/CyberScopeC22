#!/usr/bin/env python3
"""Check a device's integrity map against its trusted baseline and alert on mismatch.

    python3 integrity_check.py --set-baseline
    python3 integrity_check.py
    python3 integrity_check.py --exclude cpu_utilization_percent,cpu_usage

Exit codes: 0 verified, 1 flagged, 2 check incomplete.
"""

import argparse
import json
import os
import sys

from i2map_hashing import build_integrity_map, find_diff, verify
from pi_device_params import get_device_parameters

DEVICE_ID = "device-01"
BASELINE_FILE = "baseline.json"

# Parameters that change on their own between runs, with no tampering involved.
VOLATILE_PARAMS = (
    "cpu_utilization_percent",
    "cpu_usage",
    "memory_usage",
    "cpu_clock_frequency_mhz",
    "process_group_id",
    "process_title",
)


def build_current_map(excluded=()):
    """Build an integrity map of the device now, skipping any excluded parameters."""
    params = [(name, value) for name, value in get_device_parameters() if name not in excluded]
    return build_integrity_map(params)


def load_baseline(device_id=DEVICE_ID):
    """Return the trusted baseline map, or None if there isn't one."""
    # TODO: fetch from the chain once the contract read call exists
    if not os.path.exists(BASELINE_FILE):
        return None
    with open(BASELINE_FILE) as handle:
        return json.load(handle)


def save_baseline(integrity_map, device_id=DEVICE_ID):
    """Store a map as the trusted baseline."""
    # TODO: register on the chain once the contract write call exists
    with open(BASELINE_FILE, "w") as handle:
        json.dump(integrity_map, handle, indent=2)


def raise_alert(message):
    """Send a mismatch alert without letting a failed send stop the check."""
    try:
        from Aleting import send_discord_alert
        send_discord_alert(message, severity="critical", source="cyberscope")
    except Exception as error:
        print(f"[warning] alert not sent: {error}")


def check(excluded=(), alert_on_mismatch=True):
    """Compare the device's current map to its baseline.

    Returns (verdict, details) where verdict is verified, flagged or unknown.
    """
    baseline = load_baseline()
    if baseline is None:
        return "unknown", {"reason": "no baseline available"}

    current = build_current_map(excluded)

    if verify(current, baseline["root_hash"]):
        return "verified", {"root_hash": current["root_hash"]}

    difference = find_diff(current, baseline)
    if alert_on_mismatch:
        raise_alert(f"Integrity mismatch on {DEVICE_ID}: {difference}")
    return "flagged", difference


def main():
    parser = argparse.ArgumentParser(description="Check device integrity against its baseline.")
    parser.add_argument("--set-baseline", action="store_true", help="store the current state as trusted")
    parser.add_argument("--exclude", default="", help="comma separated parameters to leave out of the hash")
    parser.add_argument("--exclude-volatile", action="store_true", help="leave out the known self-changing parameters")
    parser.add_argument("--no-alert", action="store_true", help="suppress the mismatch alert")
    args = parser.parse_args()

    excluded = tuple(name for name in args.exclude.split(",") if name)
    if args.exclude_volatile:
        excluded += VOLATILE_PARAMS

    if args.set_baseline:
        baseline = build_current_map(excluded)
        save_baseline(baseline)
        print(f"BASELINE SET - {baseline['root_hash'][:16]}... ({len(baseline['param_values'])} parameters)")
        if excluded:
            print(f"   excluded: {', '.join(excluded)}")
        return 0

    verdict, details = check(excluded, alert_on_mismatch=not args.no_alert)

    if verdict == "verified":
        print(f"MATCH - device verified ({details['root_hash'][:16]}...)")
        return 0

    if verdict == "flagged":
        print("MISMATCH - device flagged")
        for key in ("changed", "added", "removed"):
            if details.get(key):
                print(f"   {key}: {', '.join(details[key])}")
        return 1

    print(f"UNKNOWN - {details['reason']}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
