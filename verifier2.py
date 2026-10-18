#!/usr/bin/env python3
"""CyberScope verifier: compare the on-chain current hash with the originally published baseline.

    python3 verifier.py                  # check every 30 seconds, alert on deviation
    python3 verifier.py --once           # single check; exit 0 = match, 1 = deviation, 2 = incomplete
    python3 verifier.py --live           # also recompute this device's hash locally and compare

Every check is also forwarded to Microsoft Sentinel when the SENTINEL_* settings are
configured (see sentinel_client.py).

An alert (Discord, via AlertingTest/Aleting.py) is sent when a deviation first appears, again if
the deviating hash changes, and a recovery notice when it matches again. If the producer has
written state/ files on this machine, the alert also names which parameters changed.
"""

import argparse
import os
import sys
import time
from datetime import datetime

import chain_client as cc


def log(msg):
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def send_alert(message, severity):
    try:
        from Aleting import send_discord_alert
        if not send_discord_alert(message, severity=severity, source="cyberscope-verifier"):
            log("warning: alert was not accepted by Discord")
    except Exception as error:
        log(f"warning: alert not sent: {error}")


def send_sentinel(device_id, verdict, message, hashes):
    """Forward every check result to Microsoft Sentinel (no-op unless configured)."""
    import sentinel_client
    if not sentinel_client.enabled():
        return
    status, severity = {"ok": ("OK", "Informational"),
                        "deviation": ("DEVIATION", "High")}.get(verdict, ("INCOMPLETE", "Medium"))
    sentinel_client.send_event(device_id, status, message, hashes.get("baseline"),
                               hashes.get("current"), severity)


def describe_diff(current_map):
    """Name changed parameters if we hold the baseline map locally (producer on same host)."""
    from i2map_hashing import find_diff
    baseline_map = cc.load_json("baseline_map.json")
    if not baseline_map or not current_map:
        return ""
    diff = find_diff(current_map, baseline_map)
    parts = [f"{k}: {', '.join(v)}" for k, v in diff.items() if v]
    return " | " + "; ".join(parts) if parts else ""


def check(contract, device_id, live, excluded):
    """Return (verdict, message, fingerprint, hashes). verdict: ok | deviation | incomplete."""
    baseline, _ = cc.read_hash(contract, cc.baseline_id(device_id))
    if baseline is None:
        return "incomplete", "no baseline published on chain yet", None, {}

    current, _ = cc.read_hash(contract, cc.current_id(device_id))
    if current is None:
        return "incomplete", "no current hash published on chain yet", None, {"baseline": baseline}

    if current != baseline:
        detail = describe_diff(cc.load_json("current_map.json"))
        return "deviation", (f"{device_id}: on-chain hash deviates from baseline. "
                             f"baseline={baseline[:16]}... current={current[:16]}...{detail}"), current, \
                {"baseline": baseline, "current": current}

    if live:
        local_map = cc.build_map(excluded)
        if local_map["root_hash"] != baseline:
            detail = describe_diff(local_map)
            return "deviation", (f"{device_id}: live device state deviates from baseline "
                                 f"(chain still reports a match). local={local_map['root_hash'][:16]}...{detail}"), \
                   "live:" + local_map["root_hash"], {"baseline": baseline, "current": local_map["root_hash"]}

    return "ok", f"match ({baseline[:16]}...)", None, {"baseline": baseline, "current": current}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--interval", type=int, default=30, help="seconds between checks (default 30)")
    p.add_argument("--device-id", default=os.getenv("DEVICE_ID", cc.DEFAULT_DEVICE_ID))
    p.add_argument("--once", action="store_true", help="check once and exit")
    p.add_argument("--live", action="store_true", help="also recompute this device's hash locally")
    p.add_argument("--exclude", default="", help="extra parameters to leave out (must match the producer; --live only)")
    p.add_argument("--include-volatile", action="store_true", help="must match the producer (--live only)")
    args = p.parse_args()

    excluded = cc.parse_excludes(args.exclude, args.include_volatile)
    _, contract, _ = cc.connect(need_key=False)
    log(f"verifying device={args.device_id} contract={contract.address}")

    alerted = None  # fingerprint of the deviation we last alerted on
    while True:
        started = time.monotonic()
        try:
            verdict, message, fingerprint, hashes = check(contract, args.device_id, args.live, excluded)
        except Exception as error:
            verdict, message, fingerprint, hashes = "incomplete", f"check failed: {error}", None, {}

        try:
            send_sentinel(args.device_id, verdict, message, hashes)
        except Exception as error:  # never let SIEM forwarding break the verifier
            log(f"warning: sentinel forwarding failed: {error}")

        if verdict == "deviation":
            log(f"DEVIATION - {message}")
            if fingerprint != alerted:
                send_alert(message, "critical")
                alerted = fingerprint
        else:
            log(f"{'OK' if verdict == 'ok' else 'INCOMPLETE'} - {message}")
            if verdict == "ok" and alerted is not None:
                send_alert(f"{args.device_id}: integrity restored, hash matches baseline again", "info")
                alerted = None

        if args.once:
            return {"ok": 0, "deviation": 1}.get(verdict, 2)
        time.sleep(max(0, args.interval - (time.monotonic() - started)))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
