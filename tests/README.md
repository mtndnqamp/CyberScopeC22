# CyberScope IoT Device Integrity Attestation — Security Testing

CyberScope Security is the Python testing component for a university IoT integrity-attestation capstone. It demonstrates a complete evidence chain:

> trusted state → controlled or simulated tampering → changed parameter → changed SHA-256 I2Map → detection decision → restoration → report

It is intended only for Raspberry Pis, emulated Pis, Linux VMs, and other systems you own or are explicitly authorised to test. It does not scan networks, exploit devices, install persistence, implement malware, or build the blockchain component.

## Architecture

The CLI selects a scenario from a registry. `BaseSecurityTest` owns the safety lifecycle and calls a device-state provider, integrity provider, recursive comparison engine, evidence writer, restoration hook, and report writer. Built-in Linux/Raspberry Pi collectors and canonical SHA-256 work independently. The provider protocols in `cyberscope/integrity/providers.py` allow team-owned collection or I2Map code to replace the built-ins later.

Monitored state contains stable values that participate in the I2Map. Diagnostic state records useful but volatile observations, such as instantaneous CPU utilisation, without creating false positives. Optional measurements always state whether they are supported and why they are unavailable.

## Installation

Requirements:

- Python 3.11 or newer
- Linux for full collection; simulation tests also work in restricted Linux VMs
- Optional host commands: `ip`, `iwgetid`, `lsusb`, `dpkg-query`, `systemd-detect-virt`

There are no third-party Python runtime dependencies and no system-Python modifications:

```bash
cd ~/Desktop/cyberscope_security
python3 main.py --help
python3 -m unittest discover -s unit_tests -v
```

If using the development worktree before integration, substitute `.worktrees/implementation` as the directory.

## Supported Platforms

Environment detection reports `RASPBERRY_PI`, `LINUX_VM`, `GENERIC_LINUX`, or `UNKNOWN`. It uses device-tree, CPU, operating-system, architecture, and virtualisation evidence—never hostname alone. Missing Pi voltage, serial, GPIO, SPI/I2C, JTAG, Wi-Fi, or USB information is reported as unsupported rather than causing a crash.

## Raspberry Pi Setup

1. Use a dedicated laboratory Pi and back up important files.
2. Run as an ordinary user for collection and simulation.
3. Confirm the `output/` directory is writable.
4. Create a baseline before inserting the test USB device.
5. Use `--interactive` only while physically present to perform and reverse the requested peripheral step.
6. Use `--real-test` only for a scenario that explicitly reports real mode as supported. This release does not automatically spoof MAC addresses, rewrite DNS/routes, change ownership, or enable debugging interfaces.

## VM and Simulation Setup

Simulation is the recommended development mode when hardware is missing:

```bash
python3 main.py test run USB-001 --simulation
python3 main.py test NET-001 --simulation
python3 main.py test network --simulation
python3 main.py test all --simulation
```

Reports explicitly say `environment_mode = simulation`. A simulation proves hashing, comparison, classification, evidence, and reporting logic; it does not claim that physical tampering occurred.

## Baselines

```bash
python3 main.py system-info
python3 main.py baseline create
python3 main.py baseline show
python3 main.py baseline compare
```

`baseline create` stores timestamped state and `latest.json` under `output/baselines/`. Each baseline stores the provider ID and verifies its own digest when loaded. `baseline compare` returns exit code 0 for an unchanged I2Map and 1 for a mismatch, printing dotted changed paths and before/after values.

Package inventories may legitimately change after system maintenance. Create a new trusted baseline only after independently verifying that the change was authorised.

## Running Tests

The Makefile shortcuts can be run from the project root:

```bash
make networktest
make softwaretest
make usbtest
make configurationtest
make securitytest
make test
make stabilitytest ITERATIONS=100
```

Category and full security shortcuts use simulation mode so they are safe on a VM. `make test` runs both the Python unit-test suite and all 16 simulated security scenarios.

```bash
python3 main.py test list
python3 main.py test software
python3 main.py test configuration
python3 main.py test usb --interactive
python3 main.py test run SW-001
python3 main.py test run USB-001 --simulation
python3 main.py test USB-001 --simulation
python3 main.py test all --dry-run
```

Modes:

- Normal mode performs only framework-confined file mutations; unsafe host changes skip.
- `--simulation` uses explicit synthetic after-state values.
- `--simulate` is accepted as a shorter alias for `--simulation`.
- `--dry-run` records intent and performs no mutation; the result is `SKIPPED`.
- `--real-test` opts into a scenario's guarded real implementation but never bypasses its safety checks.
- `--interactive` waits for an operator-controlled USB step and never inserts/removes a device itself.

Results are `PASS`, `FAIL`, `SKIPPED`, or `ERROR`. A normal tampering pass requires the expected parameter to change, the I2Map to change, and the mismatch to be detected. `FALSE_NEGATIVE` means tampering occurred but the digest remained equal. `UNEXPECTED_CHANGE` means the expected path was not observed. Restoration failure changes the overall result to `ERROR` even when detection worked.

## Stability and False Positives

```bash
python3 main.py test stability --iterations 100
```

Iteration one becomes the comparison baseline. The summary records matching and mismatching iterations, every hash, differences for each mismatch, and `false_positive_rate = mismatching_iterations / iterations`. Any mismatch returns exit code 1; the framework does not hide instability behind a threshold.

## Reports and Evidence

```bash
python3 main.py report list
python3 main.py report show USB-001
```

Each scenario execution creates:

```text
output/evidence/<TEST-ID>_<timestamp>_<run-id>/
├── baseline.json
├── runtime.json       # omitted when no runtime collection occurred
├── diff.json
└── result.json
```

JSON and text reports are stored under `output/reports/`. The text report is ready to cite or screenshot for a capstone portfolio; the JSON preserves structured evidence for analysis. Generated paths include a random run ID to avoid collisions.

## Adding a Security Test

1. Subclass `BaseSecurityTest` or the controlled-file helper.
2. Provide immutable `ScenarioMetadata` with ID, category, threat, preconditions, expected paths, and I2Map behavior.
3. Implement only scenario-specific capture, preparation, tampering/simulation, restoration, and verification.
4. Add the scenario to `build_registry()`.
5. Write a test using a temporary directory or injected provider and prove it fails before implementation.
6. Verify dry-run, simulation honesty, error handling, and restoration.

To integrate the team I2Map, implement `DeviceStateProvider.collect()` and/or `IntegrityProvider.digest()` and inject the adapters into `ScenarioContext`. Preserve deterministic, JSON-compatible monitored values and use a distinct provider ID.

## Safety and Restoration

Controlled files are confined beneath `.cyberscope-test-resources/`. Before a normal mutation, the framework captures existence, bytes, and mode. The lifecycle attempts restoration from `finally`, verifies the result independently, and records failure prominently. Never point controlled tests at production resources.

USB physical tests prompt the operator to restore the original arrangement and then recollect the inventory to verify it. Network, MAC, DNS, route, ownership, and SPI/I2C changes are simulation-first because automatic mutation could disconnect or damage the laboratory host.

## Known Limitations

- Software attestation cannot provide a hardware root of trust or stop a privileged attacker from falsifying collector output.
- SHA-256 identifies state inequality, not intent or exploitability.
- Installed package output varies by distribution and legitimate administration.
- VMs often omit Pi hardware, wireless, and USB details.
- CPU utilisation/frequency are diagnostic because they are volatile.
- Physical USB results depend on stable identity fields exposed by the device and kernel.
- DNS, interface, route, MAC, ownership, SPI/I2C, and JTAG mutation are not automatically performed.
- The built-in provider is a reference adapter; compare its schema with the team-owned attestation implementation before integration.

See [THREAT_MODEL.md](docs/THREAT_MODEL.md), [TEST_PLAN.md](docs/TEST_PLAN.md), and [TEST_CASES.md](docs/TEST_CASES.md) for report-ready project documentation.
