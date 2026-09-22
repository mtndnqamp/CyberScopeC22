# CyberScope Security Testing Framework Design

## Purpose

CyberScope Security is a Python 3 framework for demonstrating integrity-attestation behavior in an authorised Raspberry Pi, emulated Raspberry Pi, or generic Linux laboratory environment. It records a trusted device state, applies a controlled and reversible change, recollects the state, explains every changed parameter, evaluates whether the I2Map changed as expected, restores the environment, and saves report-ready evidence.

This repository contains the security-testing component only. It does not implement a blockchain. A narrow provider interface allows a team-owned I2Map implementation or remote attestation service to replace the built-in canonical SHA-256 implementation later.

## Scope and Delivery Strategy

The first complete release covers the requested MVP and the named SW, NET, USB, and CFG scenarios. Implementation is incremental, but the finished CLI exposes baseline management, system information, scenario discovery and execution, stability testing, evidence collection, and report browsing.

The framework uses only the Python standard library at runtime. Tests use `unittest`, avoiding an external dependency on laboratory devices that may not have internet access. A `requirements.txt` is retained and documents that no third-party runtime packages are required.

## Architectural Approach

The framework is adapter-based:

1. A `DeviceStateProvider` protocol supplies a normalised state document.
2. The built-in provider composes focused software, hardware, network, configuration, USB, and environment collectors.
3. An `IntegrityProvider` protocol calculates an I2Map from monitored stable state.
4. The built-in provider uses canonical JSON and SHA-256. A future adapter can call the team's implementation without changing tests, reports, or attack scenarios.
5. A reusable `BaseSecurityTest` owns the safe lifecycle. Scenario classes supply prechecks, controlled mutation, expected paths, restoration, and optional simulation state.
6. Evidence and reporting consume provider-neutral result models.

This structure keeps the security-testing component independently demonstrable while preventing lock-in to assumptions about unfinished team interfaces.

## Package Structure

```text
cyberscope_security/
├── main.py                         # executable compatibility entry point
├── cyberscope/
│   ├── __init__.py
│   ├── cli.py                      # argparse commands and display
│   ├── config.py                   # paths and safe defaults
│   ├── models.py                   # enums and typed result records
│   ├── collectors/
│   │   ├── common.py               # supported/unsupported measurement helpers
│   │   ├── software.py             # OS, package, Python, monitored-file state
│   │   ├── hardware.py             # CPU, memory, serial, interfaces
│   │   ├── network.py              # hostname, addresses, routes, DNS, wireless
│   │   ├── usb.py                  # sysfs and lsusb parsing/inventory
│   │   ├── configuration.py        # user and controlled file metadata
│   │   └── state.py                # collector composition
│   ├── integrity/
│   │   ├── providers.py            # provider protocols and built-in adapter
│   │   ├── hashing.py              # canonicalisation and SHA-256
│   │   ├── comparison.py           # recursive path-aware diffing
│   │   └── baseline.py             # validated persistence and lookup
│   ├── scenarios/
│   │   ├── base.py                 # lifecycle, restoration, classification
│   │   ├── software.py             # SW-001 through SW-004
│   │   ├── network.py              # NET-001 through NET-005
│   │   ├── usb.py                  # USB-001 and USB-002
│   │   ├── configuration.py        # CFG-001 through CFG-005
│   │   ├── stability.py            # unchanged-state false-positive test
│   │   └── registry.py             # stable test discovery
│   ├── reporting/
│   │   ├── evidence.py             # atomic per-run artifacts
│   │   ├── report.py               # JSON and human-readable reports
│   │   └── log.py                  # redacted file/console logging
│   └── utils/
│       ├── commands.py             # argument-array subprocess wrapper
│       ├── environment.py          # Pi/VM/Linux detection
│       ├── files.py                # atomic writes, hashes, metadata
│       └── permissions.py          # capability and real-test guards
├── unit_tests/                     # standard-library automated tests
├── docs/
│   ├── THREAT_MODEL.md
│   ├── TEST_PLAN.md
│   └── TEST_CASES.md
├── output/                         # runtime output, ignored except placeholders
├── requirements.txt
├── pyproject.toml
└── README.md
```

## State and Measurement Model

The collected document has a versioned top-level schema:

```json
{
  "schema_version": 1,
  "environment": {},
  "software": {},
  "hardware": {},
  "network": {},
  "configuration": {},
  "usb": {}
}
```

Every parameter that may be unavailable is represented as a measurement object:

```json
{"supported": true, "value": "example", "reason": null}
```

or:

```json
{
  "supported": false,
  "value": null,
  "reason": "Parameter unavailable in virtualised environment"
}
```

Collectors never raise merely because optional hardware, a command, or a Linux pseudo-file is absent. Permission failures and unexpected parsing failures are preserved as unsupported reasons and warnings. Secret-bearing values are excluded or redacted.

State is divided by policy rather than by separate output files:

- `monitored`: stable values included in the I2Map.
- `diagnostic`: useful evidence excluded from the I2Map by default.

Timestamps, process IDs, CPU utilisation, current CPU frequency, runtime command duration, and temporary paths are diagnostic. OS release, kernel, architecture, inventories, hostname, interface assignments, routes, DNS, wireless identity, USB identity, monitored-file hashes/metadata, memory size, and stable hardware identity are monitored where supported. Lists are normalised into deterministic order and unordered command output is parsed before hashing.

## Integrity and Comparison

The built-in integrity provider recursively normalises supported values, removes explicitly volatile or unmonitored fields, serialises with `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, encodes UTF-8, and hashes with SHA-256.

The same unchanged monitored state must produce the same digest regardless of dictionary insertion order. Baseline files include collection time and metadata outside the exact `monitored_state` payload so persistence timestamps do not alter the hash.

The comparison engine produces typed differences with dotted paths, kinds (`added`, `removed`, `changed`), and before/after values. Sensitive paths are redacted before reports are written. A hash mismatch is never the only explanation when state inputs are available.

## Baseline Persistence

`baseline create` writes a timestamped JSON document atomically under `output/baselines` and updates a small `latest.json` copy only after the timestamped artifact succeeds. A baseline includes schema version, creation time, environment summary, provider identity, monitored state, diagnostic state, and digest.

`baseline show` uses the latest baseline by default or a validated path/name. `baseline compare` collects a new state and reports both digest equality and parameter differences. Loading rejects malformed JSON, unsupported schema versions, missing required fields, and stored digests that do not match the stored monitored state.

## Security-Test Lifecycle

`BaseSecurityTest.run()` is final orchestration logic with this sequence:

1. Validate mode and preconditions.
2. Create the evidence directory and log.
3. Capture the original scenario-specific resource state.
4. Collect baseline device state and calculate its digest.
5. Execute the real controlled action, simulate an explicit before/after state, or record dry-run intent.
6. Collect runtime state and calculate its digest.
7. Diff the states and classify detection.
8. Save baseline, runtime, diff, commands, and preliminary result evidence.
9. Restore the original state from `finally` when a real mutation was attempted.
10. Verify restoration independently and update the final result.
11. Generate JSON and text reports.

Scenario code cannot bypass the lifecycle. Restore methods are idempotent. Original bytes, modes, and existence state are captured before file mutation. Real host changes capture and validate the current value before executing an argument-array command.

## Modes and Safety Policy

- **Normal:** perform only mutations confined to the framework-controlled workspace.
- **Simulation:** use labelled synthetic before/after state and never claim a physical attack occurred.
- **Dry-run:** perform prechecks and describe actions, but make no mutation; result is `SKIPPED`, not a fabricated pass.
- **Real test:** permits specifically implemented host mutations after explicit `--real-test`; it does not weaken scenario-specific guards.
- **Interactive:** pauses only for an operator-controlled physical step such as USB insertion/removal.

The framework never uses `shell=True`, accepts arbitrary command fragments, scans external networks, connects to wireless networks, creates persistence, installs packages into system Python, modifies important application resources, or automatically enables JTAG/debug interfaces. Hostname, MAC, ownership, DNS, and interface mutations are simulated unless both the scenario supports a reversible method and `--real-test` is supplied. Actions that could disconnect the active test host remain simulation-only in the first release.

User input is constrained to registry IDs, positive iteration counts, known modes, and paths confined to configured output/test roots. Subprocess calls have timeouts, bounded captured output, argument arrays, and an audit record.

## Scenario Coverage

### Software

- **SW-001:** change `application.conf` from `mode=normal` to `mode=compromised`, detect content hash change, restore bytes.
- **SW-002:** model an isolated virtual-environment package inventory addition. Simulation is the safe default; an optional controlled venv fixture never changes system Python.
- **SW-003:** add a harmless comment to controlled `sensor_app.py`, detect source hash change, restore bytes.
- **SW-004:** create a harmless executable in the controlled directory, detect file/inventory addition, then remove it.

### Network

- **NET-001:** simulate hostname change by default; real mode uses an available reversible hostname tool, restores, and verifies.
- **NET-002:** simulate resolver state transition without overwriting `/etc/resolv.conf`.
- **NET-003:** simulate interface/IP/subnet/gateway change to avoid disconnecting the test host.
- **NET-004:** compare current wireless SSID when available; skip physical mode when no wireless interface exists and never connect automatically.
- **NET-005:** simulate MAC change by default; physical collection detects operator-made changes but the framework does not automatically spoof an active interface.

### USB

- **USB-001:** record baseline inventory, prompt for insertion in interactive physical mode, and classify newly added stable device identities as `UNAUTHORISED_DEVICE_DETECTED`.
- **USB-002:** record baseline inventory, prompt for removal, and identify trusted device identities that disappeared.

Simulation uses labelled deterministic USB fixtures. Physical inventory prefers `/sys/bus/usb/devices` and enriches from `lsusb` only if available. Bus/address values are diagnostic; vendor, product, manufacturer, product name, and serial form stable identities where available.

### Configuration

- **CFG-001:** modify one field in a controlled configuration file and restore it.
- **CFG-002:** change a controlled file from `0644` to `0600`, detect mode plus metadata, and restore it.
- **CFG-003:** simulate ownership change unless an isolated authorised real environment and reversible ownership capability are available.
- **CFG-004:** exercise the shared hostname transition but report it under configuration threat mapping.
- **CFG-005:** collect SPI/I2C state where supported; simulate an enabled-state change and never enable JTAG or debug interfaces automatically.

Each registry entry exposes ID, name, category, description, threat, preconditions, expected changed paths, expected I2Map behavior, supported modes, and safety notes.

## Result Classification

Result records use `PASS`, `FAIL`, `SKIPPED`, or `ERROR` and separately record detection semantics:

- True positive: tampering occurred, expected path changed, digest changed, and mismatch was detected (`PASS`).
- False negative: tampering occurred but the digest did not change or mismatch was not detected (`FAIL`).
- Unexpected change: digest changed but expected paths did not; report all differences (`FAIL`).
- True negative: no tampering and digest remains equal (stability match).
- False positive: no tampering but digest differs (stability mismatch).
- Skipped: unsupported precondition, deliberate dry-run, or cancelled interactive step.
- Error: unexpected collector, lifecycle, comparison, evidence, or restoration failure.

A restoration failure is always prominent. It changes a would-be pass to `ERROR`, preserving the detection result as a separate field so evidence remains analytically useful.

Every result contains the requested test metadata, original values, tampering action, expected and actual changes, both hashes, integrity match, detection, classification, timestamps, errors, restoration state, environment mode, and evidence locations.

## Stability Testing

`test stability --iterations N` validates `N` as a positive bounded integer, collects the selected monitored state repeatedly, hashes each sample, compares it to iteration one, and reports matching iterations, mismatching iterations, changed paths per mismatch, and false-positive rate. The default is 100. There is no artificial success threshold: every mismatch is evidence and produces a non-zero CLI status.

## Evidence, Logging, and Reports

Every execution uses a collision-resistant directory named from test ID, UTC-safe local timestamp, and a short run identifier. Atomic JSON writes prevent partially valid evidence. Core artifacts are:

- `baseline.json`
- `runtime.json`
- `diff.json`
- `commands.log`
- `result.json`
- `run.log`

Reports are written as `<TEST-ID>_<timestamp>_<run-id>.json` and `.txt`. The text format begins with “CyberScope Security Test Report” and presents the requested fields for capstone use. Report list/show commands select only validated files beneath the reports directory.

Logging supports DEBUG, INFO, WARNING, and ERROR. PASS is rendered as an INFO message with an explicit result field rather than introducing a custom logging level. Command logs record executable and arguments, return code, duration, and redacted/truncated output; they never record environment variables or secret file contents.

## CLI Contract

The root command is `python main.py` and supports:

```text
system-info
baseline create
baseline show [name]
baseline compare [name]
test list
test software [mode options]
test network [mode options]
test usb [--interactive | --simulation]
test configuration [mode options]
test run TEST-ID [mode options]
test all [mode options]
test stability [--iterations N]
report list
report show TEST-ID-OR-FILENAME
```

Mode options are mutually validated: `--simulation`, `--dry-run`, `--real-test`, and scenario-specific `--interactive`. Human output is concise, while complete detail is preserved in evidence. Exit status is 0 for successful informational commands and all requested tests passing, 1 for FAIL/ERROR or stability mismatches, and 2 for invalid CLI use.

## Environment Detection

Detection uses `/proc/device-tree/model`, Raspberry Pi identifiers from `/proc/cpuinfo`, `systemd-detect-virt` when available, known hypervisor markers, `platform.system()`, and `platform.machine()`. Precedence is `RASPBERRY_PI`, `LINUX_VM`, `GENERIC_LINUX`, then `UNKNOWN`; hostname is never evidence. Raw clues are included for auditability without being part of the environment label alone.

## Documentation and Threat Mapping

`docs/THREAT_MODEL.md` covers T01–T08 with asset, actor, vector, affected parameter, control, expected behavior, and associated test IDs. `docs/TEST_PLAN.md` defines setup, authorised scope, entry/exit criteria, execution procedure, evidence handling, and limitations. `docs/TEST_CASES.md` provides the requested summary table and detailed cases for every named ID.

The README explains purpose, architecture, installation, platforms, Raspberry Pi and VM setup, baseline commands, test execution, reports, extension through adapters/scenarios, safety/restoration, and limitations.

## Automated Verification

Unit and integration-style tests use temporary directories, injected state providers, injected command runners, and simulated scenarios. They cover:

- deterministic canonical hashing and volatile-field exclusion;
- baseline atomic save/load and malformed/tampered baseline rejection;
- recursive dictionary/list diffing;
- software, network, hardware, configuration, and USB collection/parsing;
- unsupported parameter representation;
- environment detection fixtures;
- report and evidence creation;
- lifecycle restoration on success and exceptions;
- PASS/FAIL/SKIPPED/ERROR and true-positive/false-positive/false-negative classification;
- scenario behavior and registry completeness;
- CLI parsing and representative commands;
- repeated stability calculations.

After unit tests, smoke verification runs `system-info`, baseline create/compare, each simulation scenario, all-tests dry-run, a short stability run, report list/show, static compilation with `compileall`, and a search proving no `shell=True` is used.

## Integration Contract

The future team adapter implements:

```python
class DeviceStateProvider(Protocol):
    def collect(self) -> CollectedState: ...

class IntegrityProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    def digest(self, monitored_state: Mapping[str, object]) -> str: ...
```

`CollectedState` holds monitored and diagnostic mappings. Providers must return JSON-compatible, deterministic monitored values and explain unsupported fields. A remote provider adapter may request a hash, but must not send diagnostic or secret-bearing fields by default. Provider metadata is stored in baselines so comparisons cannot silently mix incompatible algorithms.

## Known Limitations

VMs cannot expose all Raspberry Pi voltage, serial, GPIO, JTAG, SPI/I2C, wireless, or USB information. Installed package collectors are distribution-dependent. Package inventories can change due to legitimate administration and may be expensive. CPU utilisation/frequency are intentionally diagnostic. Physical USB tests require operator timing. Real hostname changes can affect services and therefore require explicit opt-in. DNS, route, active-interface, MAC, ownership, SPI/I2C, and JTAG mutation are simulation-first or collection-only. SHA-256 attestation detects observed state changes but does not identify intent, guarantee collector integrity, provide a hardware root of trust, or prevent an attacker with sufficient privilege from falsifying measurements.

## Acceptance Criteria

Completion requires all requested files and commands to exist, all automated tests and smoke checks to pass, no uncontrolled host mutation during verification, and generated evidence demonstrating:

1. unchanged monitored state produces equal I2Maps;
2. simulated or controlled tampering changes the expected parameter and I2Map;
3. diffs explain the mismatch;
4. result classification is correct;
5. restoration succeeds for controlled real file changes;
6. physical-only limitations are explicit rather than represented as successful attacks;
7. every named threat and test is documented and discoverable.
