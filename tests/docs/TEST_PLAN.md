# CyberScope Security Test Plan

## Objective

Validate that unchanged stable Raspberry Pi/Linux state produces the trusted I2Map while controlled software, configuration, network, and USB changes produce an explained mismatch. Demonstrate detection classification, evidence collection, and restoration suitable for the capstone portfolio.

## Authorised Scope

- Owned university Raspberry Pi laboratory devices
- Project-owned Raspberry Pi emulation
- Local development Linux VM
- Framework resources beneath `.cyberscope-test-resources/`
- Explicit simulation state supplied by this project

External networks, public devices, third-party systems, production resources, persistence, malware, destructive operations, and irreversible changes are excluded.

## Entry Criteria

1. Written authorisation and target identity are recorded.
2. Important target data is backed up.
3. Python 3.11+ is available and tests pass.
4. Output and controlled-resource directories are writable.
5. The operator confirms whether the environment is Pi, VM, or generic Linux.
6. For physical USB testing, a known disposable test device is available.

## Common Procedure

1. Run `system-info` and retain the environment evidence.
2. Determine the current scenario-specific value before modification.
3. Capture original bytes/metadata or physical inventory.
4. Collect monitored baseline parameters and calculate the baseline SHA-256 I2Map.
5. Perform the smallest controlled action, or use an explicitly labelled simulation.
6. Collect runtime parameters and calculate the runtime I2Map.
7. Compare state recursively and record changed dotted paths.
8. Classify detection as true positive, false negative, unexpected change, true negative, or false positive.
9. Save baseline, runtime, diff, result, and reports.
10. Restore from the captured original state in `finally` where the framework mutated a resource.
11. Verify restoration independently and retain any error.

## Modes

Normal mode is limited to controlled project files. Simulation verifies before/after detection logic without claiming a physical event. Dry-run records intended actions and returns `SKIPPED`. Real-test is an explicit opt-in and still skips scenarios whose real mutation is unsupported. Interactive mode pauses for a manual USB insertion/removal.

## Oracle and Classification

- **True positive / PASS:** intended path changed, runtime I2Map changed, mismatch was detected, and evidence explains it.
- **False negative / FAIL:** tampering occurred but the I2Map remained equal or was classified trusted.
- **Unexpected change / FAIL:** a mismatch occurred but did not include the intended path.
- **True negative:** no tampering and I2Maps match.
- **False positive:** no tampering and I2Maps differ.
- **SKIPPED:** deliberate dry-run or unsupported precondition.
- **ERROR:** unexpected lifecycle/evidence failure or failed restoration.

## Stability Validation

Run `python3 main.py test stability --iterations 100`. Iteration one is the trusted comparison sample. Record matches, mismatches, false-positive rate, and paths for every mismatch. Investigate legitimate background changes before adjusting monitored parameters; do not simply suppress a failing measurement.

## Manual USB Procedure

For USB-001, start the interactive test, allow baseline collection, insert the authorised test USB device when prompted, and press Enter. For USB-002, begin with the disposable trusted device attached, start the test, remove it when prompted, and press Enter. When prompted again, re-establish the original physical arrangement; the framework recollects the USB inventory and records whether restoration matches the baseline.

## Evidence Handling

Do not edit generated evidence. Copy the complete run directory into the project evidence store and record test ID, target asset label, operator, date/time, environment, commit, and anomalies in the portfolio. JSON is authoritative structured output; the paired text report is the human-readable summary. Do not collect environment variables, credentials, Wi-Fi keys, or secret file contents.

## Exit Criteria

- All automated tests and safe smoke commands pass.
- Stability is run for the agreed number of iterations on the target.
- At least one controlled software/configuration true positive is demonstrated.
- USB addition/removal is either physically demonstrated or clearly labelled as simulated.
- Network scenarios are simulated unless a separate safe reversible procedure is authorised.
- Every controlled mutation is restored and verified.
- Failures, unsupported fields, false positives/negatives, and limitations remain in the report.
