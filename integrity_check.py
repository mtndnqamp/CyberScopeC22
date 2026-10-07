#!/usr/bin/env python3
"""CyberScope baseline registration and checking. Exit: 0 match, 1 mismatch, 2 incomplete."""
import argparse
import json
import sys
from pathlib import Path

from i2map_hashing import build_integrity_map, find_diff, verify, get_device_parameters

DEVICE_ID = "device-01"
BASELINE_FILE = Path(__file__).with_name("baseline.json")
DEFAULT_EXCLUDED = ("cpu_utilization_percent", "cpu_usage")
# Optional teammate policy; use only after deciding which observations belong in integrity.
VOLATILE_PARAMS = DEFAULT_EXCLUDED + ("memory_usage", "cpu_clock_frequency_mhz", "process_group_id", "process_title")


def build_current_map(excluded=(), params_file=None):
    if params_file:
        raw = json.loads(Path(params_file).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Sample parameter file must be a JSON object")
        params = list(raw.items())
    else:
        params = get_device_parameters()
    return build_integrity_map([(name, value) for name, value in params if name not in excluded])


def load_baseline(device_id=DEVICE_ID, baseline_file=BASELINE_FILE):
    path = Path(baseline_file)
    if not path.exists():
        return None
    baseline = json.loads(path.read_text(encoding="utf-8"))
    if baseline.get("schema_version") != 1 or baseline.get("device_id") != device_id:
        raise ValueError("Baseline schema/device does not match; register a new baseline")
    if baseline.get("hash_format") != "canonical-json-sha256-v1":
        raise ValueError("Unsupported baseline hash format")
    if not isinstance(baseline.get("param_values"), dict):
        raise ValueError("Invalid baseline parameter map")
    excluded = baseline.get("excluded")
    if not isinstance(excluded, list) or not all(isinstance(x, str) for x in excluded):
        raise ValueError("Invalid baseline exclusion policy")
    calculated = build_integrity_map(list(baseline["param_values"].items()))["root_hash"]
    if calculated != baseline.get("root_hash"):
        raise ValueError("Baseline values do not match its saved hash")
    return baseline


def save_baseline(integrity_map, device_id=DEVICE_ID, baseline_file=BASELINE_FILE,
                  excluded=DEFAULT_EXCLUDED, backend="blockchain", client=None, sample=False):
    baseline = dict(integrity_map, schema_version=1, device_id=device_id,
                    hash_format="canonical-json-sha256-v1", excluded=sorted(set(excluded)),
                    backend=backend, sample=sample)
    if backend == "blockchain":
        if client is None:
            from Edge_Node.app_connect import BlockchainClient
            client = BlockchainClient()
        client.store_baseline_hash(device_id, baseline["root_hash"])
        if client.get_baseline_hash(device_id) != baseline["root_hash"]:
            raise ValueError("Blockchain readback did not match registered hash")
    path = Path(baseline_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    pending.replace(path)


def raise_alert(message):
    try:
        from AlertingTest.Aleting import send_discord_alert
        return send_discord_alert(message, severity="high", source="CyberScope")
    except Exception as error:
        print(f"[warning] alert not sent: {type(error).__name__}")
        return False


def check(excluded=None, alert_on_mismatch=True, device_id=DEVICE_ID,
          baseline_file=BASELINE_FILE, backend="blockchain", client=None, params_file=None):
    baseline = load_baseline(device_id, baseline_file)
    if baseline is None:
        return "unknown", {"reason": "no baseline available"}
    if baseline["backend"] != backend or baseline["sample"] != bool(params_file):
        return "unknown", {"reason": "baseline backend or sample/device mode differs"}
    policy = baseline["excluded"]
    if excluded is not None and set(excluded) != set(policy):
        return "unknown", {"reason": "exclusions differ from baseline; use the stored policy"}
    trusted_hash = baseline["root_hash"]
    if backend == "blockchain":
        if client is None:
            from Edge_Node.app_connect import BlockchainClient
            client = BlockchainClient()
        trusted_hash = client.get_baseline_hash(device_id)
        if trusted_hash != baseline["root_hash"]:
            return "unknown", {"reason": "local baseline does not match blockchain reference"}
    current = build_current_map(policy, params_file)
    if verify(current, trusted_hash):
        return "verified", {"root_hash": current["root_hash"]}
    difference = find_diff(current, baseline)
    if alert_on_mismatch:
        difference["alert_sent"] = raise_alert(f"Integrity mismatch on {device_id}: {difference}. Monitored state changed; investigate the cause.")
    return "flagged", difference


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set-baseline", action="store_true")
    parser.add_argument("--backend", choices=["local", "blockchain"], default="blockchain")
    parser.add_argument("--device-id", default=DEVICE_ID)
    parser.add_argument("--baseline-file", type=Path, default=BASELINE_FILE)
    parser.add_argument("--params-file", type=Path, help="JSON sample parameters; does not attest the host")
    parser.add_argument("--exclude", default=None, help="comma-separated exclusions; baseline policy reused when omitted")
    parser.add_argument("--exclude-volatile", action="store_true", help="optional broader teammate exclusion policy")
    parser.add_argument("--no-alert", action="store_true")
    args = parser.parse_args(argv)
    excluded = None if args.exclude is None else tuple(x.strip() for x in args.exclude.split(",") if x.strip())
    if args.exclude_volatile:
        excluded = tuple(set(excluded or ()) | set(VOLATILE_PARAMS))
    mode = "SAMPLE" if args.params_file else "DEVICE"
    print(f"Mode: {mode}; baseline source: {args.backend}")
    if sys.platform == "win32" and not args.params_file:
        print("Windows collection is partial: Linux/Pi fields require validation on Linux/Pi.")
    try:
        if args.set_baseline:
            excluded = DEFAULT_EXCLUDED if excluded is None else excluded
            baseline = build_current_map(excluded, args.params_file)
            save_baseline(baseline, args.device_id, args.baseline_file, excluded, args.backend, sample=bool(args.params_file))
            print(f"BASELINE SET - {baseline['root_hash']} ({len(baseline['param_values'])} parameters)")
            print("Excluded: " + ", ".join(excluded))
            return 0
        verdict, details = check(excluded, not args.no_alert, args.device_id,
                                 args.baseline_file, args.backend, params_file=args.params_file)
        if verdict == "verified":
            print("MATCH - monitored state unchanged")
            return 0
        if verdict == "flagged":
            print("MISMATCH - monitored state changed; investigate")
            for key in ("changed", "added", "removed"):
                print(f"{key}: {', '.join(details[key])}")
            if "alert_sent" in details:
                print(f"Alert sent: {details['alert_sent']}")
            return 1
        print("UNKNOWN - " + details["reason"])
        return 2
    except Exception as error:
        # Configuration and dependency errors must not be counted as tamper detections.
        print(f"UNKNOWN - check incomplete ({type(error).__name__})")
        return 2

if __name__ == "__main__":
    sys.exit(main())
