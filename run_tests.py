#!/usr/bin/env python3
"""
cyberScope QA test runner
-------------------------
Repeatedly runs the team's integrity-check script, times each run, records
whether the device was flagged, and writes everything to a CSV file.

Typical use (run this ON the Raspberry Pi, over your SSH connection):

    # 100 runs with nothing tampered with -> measures FALSE POSITIVES
    python3 run_tests.py --condition clean --runs 100

    # 20 runs with a USB stick plugged in -> measures DETECTION / FALSE NEGATIVES
    python3 run_tests.py --condition usb-tamper --runs 20 --expect flagged

Results append to results.csv so every test session builds one dataset.
"""

import argparse
import csv
import os
import shlex
import shutil
import statistics
import subprocess
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# CONFIG - the only part you should need to edit once their script exists
# ---------------------------------------------------------------------------

# The command that runs ONE integrity check. Replace with the team's real one.
# Examples:  ["python3", "/home/pi/cyberscope/check.py"]
#            ["node", "/home/pi/cyberscope/i2map.js"]
DEFAULT_CHECK_COMMAND = ["python3", "check.py"]

# How do we know if a run said "compromised"?
#   "exit_code" -> script exits 0 when the device is OK, non-zero when flagged
#   "keyword"   -> we search the script's printed output for the words below
VERDICT_MODE = "exit_code"

FLAGGED_KEYWORDS = ["mismatch", "compromised", "malicious", "rejected", "fail"]
OK_KEYWORDS = ["match", "verified", "accepted", "ok", "pass"]

# ---------------------------------------------------------------------------


def decide_verdict(exit_code, output):
    """Return 'ok', 'flagged', or 'unclear' for a single run."""
    if VERDICT_MODE == "exit_code":
        return "ok" if exit_code == 0 else "flagged"

    text = output.lower()
    if any(word in text for word in FLAGGED_KEYWORDS):
        return "flagged"
    if any(word in text for word in OK_KEYWORDS):
        return "ok"
    return "unclear"


def run_once(command, measure_memory):
    """Run the check script once. Returns (verdict, seconds, peak_kb, exit_code, output)."""
    full_command = list(command)
    peak_kb = ""

    # /usr/bin/time -v gives us peak memory for free on Linux (so, on the Pi).
    use_time_tool = measure_memory and shutil.which("/usr/bin/time") is not None
    if use_time_tool:
        full_command = ["/usr/bin/time", "-v"] + full_command

    start = time.perf_counter()
    result = subprocess.run(
        full_command,
        capture_output=True,
        text=True,
    )
    seconds = time.perf_counter() - start

    output = (result.stdout or "") + (result.stderr or "")

    if use_time_tool:
        for line in output.splitlines():
            if "Maximum resident set size" in line:
                peak_kb = line.strip().split()[-1]
                break

    verdict = decide_verdict(result.returncode, output)
    return verdict, seconds, peak_kb, result.returncode, output


def summarise(rows, condition, expect):
    """Print the numbers that actually go in your report."""
    if not rows:
        print("No runs recorded.")
        return

    total = len(rows)
    flagged = sum(1 for r in rows if r["verdict"] == "flagged")
    ok = sum(1 for r in rows if r["verdict"] == "ok")
    unclear = sum(1 for r in rows if r["verdict"] == "unclear")
    times = [float(r["seconds"]) for r in rows]

    print()
    print("=" * 58)
    print(f"  SUMMARY - condition: {condition}   runs: {total}")
    print("=" * 58)
    print(f"  Device reported OK       : {ok}")
    print(f"  Device reported FLAGGED  : {flagged}")
    if unclear:
        print(f"  Unclear (couldn't tell)  : {unclear}  <-- check your VERDICT_MODE")

    if expect == "ok":
        # Nothing was tampered with, so any flag is a wrong alarm.
        print(f"\n  FALSE POSITIVE RATE      : {flagged / total * 100:.1f}%  "
              f"({flagged} wrong alarms in {total} clean runs)")
    else:
        # Something WAS tampered with, so any 'ok' is a miss.
        print(f"\n  DETECTION RATE           : {flagged / total * 100:.1f}%  "
              f"(caught {flagged} of {total})")
        print(f"  FALSE NEGATIVE RATE      : {ok / total * 100:.1f}%  "
              f"(missed {ok} of {total})")

    print(f"\n  Time per check - average : {statistics.mean(times):.2f} s")
    print(f"  Time per check - fastest : {min(times):.2f} s")
    print(f"  Time per check - slowest : {max(times):.2f} s")
    if total > 1:
        print(f"  Time per check - std dev : {statistics.stdev(times):.2f} s")

    peaks = [int(r["peak_kb"]) for r in rows if r["peak_kb"]]
    if peaks:
        print(f"\n  Peak memory - average    : {statistics.mean(peaks) / 1024:.1f} MB")
        print(f"  Peak memory - highest    : {max(peaks) / 1024:.1f} MB")
    print("=" * 58)


def main():
    parser = argparse.ArgumentParser(description="Run the integrity check many times and log results.")
    parser.add_argument("--runs", type=int, default=100,
                        help="how many times to run the check (default 100)")
    parser.add_argument("--condition", default="clean",
                        help="label for this test session, e.g. clean, usb-tamper, config-tamper")
    parser.add_argument("--expect", choices=["ok", "flagged"], default="ok",
                        help="what SHOULD happen: 'ok' for clean runs, 'flagged' for tamper runs")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="seconds to wait between runs (default 1)")
    parser.add_argument("--out", default="results.csv",
                        help="CSV file to append results to (default results.csv)")
    parser.add_argument("--no-memory", action="store_true",
                        help="skip peak-memory measurement")
    parser.add_argument("--command", default=None,
                        help='the check command, quoted, e.g. --command "python3 check.py --flag"')
    args = parser.parse_args()

    command = shlex.split(args.command) if args.command else DEFAULT_CHECK_COMMAND
    measure_memory = not args.no_memory

    print(f"Command   : {' '.join(command)}")
    print(f"Condition : {args.condition}   (expecting every run to be '{args.expect}')")
    print(f"Runs      : {args.runs}\n")

    fields = ["timestamp", "condition", "run", "verdict", "expected",
              "seconds", "peak_kb", "exit_code", "output_snippet"]
    new_file = not os.path.exists(args.out)

    rows = []
    with open(args.out, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if new_file:
            writer.writeheader()

        for i in range(1, args.runs + 1):
            verdict, seconds, peak_kb, exit_code, output = run_once(command, measure_memory)

            row = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "condition": args.condition,
                "run": i,
                "verdict": verdict,
                "expected": args.expect,
                "seconds": f"{seconds:.3f}",
                "peak_kb": peak_kb,
                "exit_code": exit_code,
                "output_snippet": output.strip().replace("\n", " | ")[:200],
            }
            writer.writerow(row)
            handle.flush()          # write as we go, so a crash doesn't lose data
            rows.append(row)

            unexpected = "" if verdict == args.expect else "   <-- UNEXPECTED"
            print(f"  run {i:>4}/{args.runs}   {verdict:<8} {seconds:>6.2f}s{unexpected}")

            if i < args.runs:
                time.sleep(args.delay)

    summarise(rows, args.condition, args.expect)
    print(f"\nRaw data appended to: {os.path.abspath(args.out)}")


if __name__ == "__main__":
    main()
