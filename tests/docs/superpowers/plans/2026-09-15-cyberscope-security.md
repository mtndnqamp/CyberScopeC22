# CyberScope Security Testing Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe, modular Python framework that baselines Linux/Raspberry Pi device state, exercises controlled or simulated tampering scenarios, detects and explains I2Map changes, restores controlled mutations, and generates capstone evidence.

**Architecture:** Provider protocols isolate device collection and integrity calculation from the test runner. A lifecycle-owned scenario base class coordinates capture, mutation, comparison, evidence, restoration, and reports; built-in collectors and canonical SHA-256 make the project independently runnable while adapters permit later team integration.

**Tech Stack:** Python 3.11+ standard library, `argparse`, `dataclasses`, `hashlib`, `json`, `pathlib`, `subprocess`, `unittest`, Linux `/proc` and `/sys` interfaces.

**Spec:** `docs/superpowers/specs/2026-09-15-cyberscope-security-design.md`

## Global Constraints

- Implement the security framework entirely in Python 3; do not implement blockchain or Solidity.
- Runtime dependencies remain Python standard-library only.
- Never invoke subprocesses with `shell=True`; pass validated argument arrays and enforce timeouts.
- Never scan external networks, connect to arbitrary wireless networks, create persistence, produce malware, or perform irreversible changes.
- Simulations must set `environment_mode` to `simulation` and must not claim a physical attack occurred.
- Dry runs perform no mutation and return `SKIPPED` with an explicit reason.
- All real mutations save original state first, run within `try/finally`, restore, and independently verify restoration.
- Unsupported Raspberry Pi/VM measurements use `{"supported": false, "value": null, "reason": "..."}` rather than raising.
- Timestamps, PIDs, CPU utilisation, current CPU frequency, random values, and temporary paths are excluded from monitored hash input.
- Output includes JSON plus human-readable reports and per-run evidence directories.
- Tests cannot mutate real hostname, interfaces, DNS, MAC addresses, ownership, USB state, or Pi interface state.

---

## File Map

- `main.py`: thin executable entry point.
- `cyberscope/config.py`: configured project/output/test-resource paths and bounded defaults.
- `cyberscope/models.py`: measurement, state, difference, mode, result, and restoration types.
- `cyberscope/integrity/hashing.py`: JSON compatibility, canonicalisation, and SHA-256.
- `cyberscope/integrity/comparison.py`: deterministic recursive diff.
- `cyberscope/integrity/providers.py`: provider protocols and canonical adapter.
- `cyberscope/integrity/baseline.py`: validated atomic baseline repository.
- `cyberscope/utils/commands.py`: audited safe subprocess runner.
- `cyberscope/utils/environment.py`: environment classification.
- `cyberscope/utils/files.py`: atomic files, file hashes, and metadata.
- `cyberscope/utils/permissions.py`: real-test gating.
- `cyberscope/collectors/*.py`: focused software, hardware, network, USB, configuration, and aggregate collectors.
- `cyberscope/reporting/*.py`: logging, run evidence, JSON/text reports.
- `cyberscope/scenarios/base.py`: reusable lifecycle and classification.
- `cyberscope/scenarios/software.py`: SW-001 through SW-004.
- `cyberscope/scenarios/network.py`: NET-001 through NET-005.
- `cyberscope/scenarios/usb.py`: USB-001 and USB-002.
- `cyberscope/scenarios/configuration.py`: CFG-001 through CFG-005.
- `cyberscope/scenarios/stability.py`: repeated unchanged-state evaluation.
- `cyberscope/scenarios/registry.py`: metadata and scenario construction.
- `cyberscope/cli.py`: all command groups and exit behavior.
- `unit_tests/`: matching tests with fakes and temporary files.
- `README.md`, `docs/THREAT_MODEL.md`, `docs/TEST_PLAN.md`, `docs/TEST_CASES.md`: capstone documentation.

---

### Task 1: Project Foundation, Models, Hashing, and Diffs

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `main.py`
- Create: `cyberscope/__init__.py`
- Create: `cyberscope/config.py`
- Create: `cyberscope/models.py`
- Create: `cyberscope/integrity/__init__.py`
- Create: `cyberscope/integrity/hashing.py`
- Create: `cyberscope/integrity/comparison.py`
- Create: `cyberscope/integrity/providers.py`
- Create: `unit_tests/__init__.py`
- Create: `unit_tests/test_hashing.py`
- Create: `unit_tests/test_comparison.py`
- Create: `unit_tests/test_models.py`

**Interfaces:**
- Produces: `Measurement.supported_value(value)`, `Measurement.unsupported(reason)`, `CollectedState(monitored, diagnostic)`, `Difference(path, kind, before, after)`, `TestMode`, `ResultStatus`, `RestorationStatus`, `canonical_json(data) -> str`, `sha256_digest(data) -> str`, `diff_values(before, after) -> list[Difference]`, `CanonicalIntegrityProvider.digest(state) -> str`.
- Consumes: no project interfaces.

- [ ] **Step 1: Write failing integrity/model tests**

```python
def test_hash_is_deterministic_for_nested_key_order(self):
    left = {"software": {"kernel": "6", "os": "Linux"}, "usb": ["b", "a"]}
    right = {"usb": ["b", "a"], "software": {"os": "Linux", "kernel": "6"}}
    self.assertEqual(sha256_digest(left), sha256_digest(right))

def test_unsupported_measurement_has_required_shape(self):
    self.assertEqual(
        Measurement.unsupported("not a Pi").to_dict(),
        {"supported": False, "value": None, "reason": "not a Pi"},
    )
```

- [ ] **Step 2: Run tests and confirm import failures**

Run: `python3 -m unittest unit_tests.test_hashing unit_tests.test_models -v`

Expected: failure because `cyberscope.models` and `cyberscope.integrity.hashing` do not exist.

- [ ] **Step 3: Implement foundation types and canonical hashing**

Define frozen `Measurement` and `Difference` dataclasses, mutable `CollectedState`, string enums for modes/statuses, and JSON conversion helpers. Reject non-finite floats and non-JSON-compatible values. `canonical_json` must use sorted keys, compact separators, UTF-8-safe output, and preserve list order; collectors are responsible for sorting unordered inventories.

```python
def canonical_json(data: Mapping[str, object]) -> str:
    _validate_json_value(data)
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

def sha256_digest(data: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Write failing recursive-diff tests**

```python
def test_nested_diff_reports_changed_added_and_removed_paths(self):
    differences = diff_values(
        {"network": {"hostname": "pi", "dns": ["1.1.1.1"]}, "old": 1},
        {"network": {"hostname": "lab", "dns": ["1.1.1.1"]}, "new": 2},
    )
    self.assertEqual(
        [(d.path, d.kind) for d in differences],
        [("network.hostname", "changed"), ("new", "added"), ("old", "removed")],
    )
```

- [ ] **Step 5: Implement deterministic recursive diffing and provider protocols**

`diff_values` walks mapping keys in sorted union order, treats lists as atomic deterministic values, uses `<missing>` internally only for presence, and returns JSON-compatible before/after values. Define runtime-checkable protocols:

```python
class DeviceStateProvider(Protocol):
    def collect(self) -> CollectedState: ...

class IntegrityProvider(Protocol):
    @property
    def provider_id(self) -> str: ...
    def digest(self, monitored_state: Mapping[str, object]) -> str: ...
```

- [ ] **Step 6: Add project metadata and entry-point placeholder**

Set `requires-python = ">=3.11"`, configure unittest-compatible package discovery, list no runtime dependencies, ignore generated output and bytecode, and have `main.py` call `cyberscope.cli.main` only after Task 7 supplies it.

- [ ] **Step 7: Run focused and full tests**

Run: `python3 -m unittest unit_tests.test_hashing unit_tests.test_comparison unit_tests.test_models -v`

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add .gitignore pyproject.toml requirements.txt main.py cyberscope unit_tests
git commit -m "feat: add integrity state foundation"
```

---

### Task 2: Safe Utilities, Environment Detection, and Collectors

**Files:**
- Create: `cyberscope/utils/__init__.py`
- Create: `cyberscope/utils/commands.py`
- Create: `cyberscope/utils/environment.py`
- Create: `cyberscope/utils/files.py`
- Create: `cyberscope/utils/permissions.py`
- Create: `cyberscope/collectors/__init__.py`
- Create: `cyberscope/collectors/common.py`
- Create: `cyberscope/collectors/software.py`
- Create: `cyberscope/collectors/hardware.py`
- Create: `cyberscope/collectors/network.py`
- Create: `cyberscope/collectors/usb.py`
- Create: `cyberscope/collectors/configuration.py`
- Create: `cyberscope/collectors/state.py`
- Create: `unit_tests/test_commands.py`
- Create: `unit_tests/test_environment.py`
- Create: `unit_tests/test_collectors.py`
- Create: `unit_tests/test_usb.py`

**Interfaces:**
- Consumes: `Measurement`, `CollectedState`, `DeviceStateProvider`.
- Produces: `CommandRunner.run(argv, timeout) -> CommandResult`, `detect_environment(...) -> EnvironmentInfo`, `file_measurement(path) -> Measurement`, collector `collect_*()` functions, `LinuxDeviceStateProvider.collect() -> CollectedState`, `parse_lsusb(text) -> list[dict[str, object]]`.

- [ ] **Step 1: Write failing command and environment tests**

```python
def test_runner_rejects_string_command(self):
    with self.assertRaises(TypeError):
        CommandRunner().run("hostname")

def test_pi_model_has_precedence_over_virtualisation(self):
    info = detect_environment(model_text="Raspberry Pi 4 Model B", cpuinfo_text="", system="Linux", machine="aarch64", virtualisation="kvm")
    self.assertEqual(info.kind, "RASPBERRY_PI")
```

- [ ] **Step 2: Run tests and confirm failures**

Run: `python3 -m unittest unit_tests.test_commands unit_tests.test_environment -v`

- [ ] **Step 3: Implement safe utilities**

`CommandRunner` accepts a non-empty sequence of strings, resolves no shell syntax, limits output to 64 KiB, defaults to a 10-second timeout, returns status/stdout/stderr/duration, and converts missing commands/timeouts into structured results. `atomic_write_text` writes a sibling temporary file then `os.replace`s it. `file_measurement` returns existence, SHA-256, mode, owner UID/GID, and size. `require_real_test` returns an explanatory decision instead of escalating privileges.

- [ ] **Step 4: Implement environment detection**

Add injectable arguments for deterministic tests and a no-argument production path reading `/proc/device-tree/model` and `/proc/cpuinfo`. Use model/cpu Raspberry Pi evidence first, then `systemd-detect-virt`, then Linux, and never use hostname.

- [ ] **Step 5: Write failing collector and USB parser tests**

```python
def test_parse_lsusb_is_sorted_and_extracts_ids(self):
    rows = parse_lsusb("Bus 002 Device 003: ID 0781:5591 SanDisk Corp. Ultra\nBus 001 Device 002: ID 1d6b:0002 Linux Foundation")
    self.assertEqual(rows[0]["vendor_id"], "0781")
    self.assertEqual(rows[0]["product_id"], "5591")

def test_missing_optional_file_is_unsupported(self):
    value = read_optional_text(Path("/definitely/missing"), "not available")
    self.assertFalse(value.supported)
```

- [ ] **Step 6: Implement focused collectors**

Software collects OS release, kernel, platform, architecture, OS type, effective user/group summary, installed package inventory from the first available known manager, Python distribution inventory via `importlib.metadata`, and configured monitored files. Hardware collects stable CPU model/architecture, memory total, serial/model, interface availability, plus diagnostic CPU utilisation/frequency/voltage where supported. Network uses `socket`, `/sys/class/net`, `ip -j` where available, `/proc/net/route`, and resolver parsing. USB prefers sysfs and falls back to `lsusb`. Configuration collects hostname/effective identity and configured file metadata plus SPI/I2C evidence.

- [ ] **Step 7: Implement aggregate provider and stability policy**

`LinuxDeviceStateProvider` accepts controlled monitored paths and injected collectors. It places stable outputs under the six schema categories and volatile observations under diagnostic. Sort inventories by stable identity and keep timestamps outside collected monitored state.

- [ ] **Step 8: Run collector tests on fixtures and current host**

Run: `python3 -m unittest unit_tests.test_commands unit_tests.test_environment unit_tests.test_collectors unit_tests.test_usb -v`

Run: `python3 -c 'from cyberscope.collectors.state import LinuxDeviceStateProvider; print(LinuxDeviceStateProvider().collect().monitored.keys())'`

Expected: tests pass and command prints all category keys without crashing on the VM.

- [ ] **Step 9: Commit**

```bash
git add cyberscope/utils cyberscope/collectors unit_tests
git commit -m "feat: collect portable Linux and Pi state"
```

---

### Task 3: Validated Baselines, Evidence, Logging, and Reports

**Files:**
- Create: `cyberscope/integrity/baseline.py`
- Create: `cyberscope/reporting/__init__.py`
- Create: `cyberscope/reporting/log.py`
- Create: `cyberscope/reporting/evidence.py`
- Create: `cyberscope/reporting/report.py`
- Create: `unit_tests/test_baseline.py`
- Create: `unit_tests/test_evidence.py`
- Create: `unit_tests/test_report.py`

**Interfaces:**
- Consumes: `CollectedState`, `Difference`, `IntegrityProvider`, atomic file helpers.
- Produces: `BaselineRecord`, `BaselineRepository.create/load/latest/compare`, `EvidenceSession.create/write_json/append_command`, `ReportWriter.write(result) -> tuple[Path, Path]`.

- [ ] **Step 1: Write failing baseline round-trip and tamper tests**

```python
def test_saved_baseline_round_trips_and_verifies_digest(self):
    record = self.repository.create(CollectedState({"software": {"os": "Linux"}}, {}), self.integrity)
    loaded = self.repository.load(record.path.name, self.integrity)
    self.assertEqual(loaded.digest, record.digest)

def test_modified_baseline_is_rejected(self):
    # Rewrite monitored_state after create, then assert BaselineValidationError.
```

- [ ] **Step 2: Implement atomic validated baseline repository**

Names must match `baseline_YYYY-MM-DD_HHMMSS_<hex>.json` or `latest.json`; resolve and verify the result remains under the baseline root. Store schema, provider ID, state, digest, environment, and timestamp. Recalculate the digest at load and reject provider mismatch or malformed shape.

- [ ] **Step 3: Write failing evidence/report tests**

```python
def test_report_contains_required_headings(self):
    json_path, text_path = self.writer.write(sample_result())
    text = text_path.read_text()
    self.assertIn("CyberScope Security Test Report", text)
    self.assertIn("Changed Parameters:", text)
    self.assertIn("Restoration:", text)
```

- [ ] **Step 4: Implement evidence sessions and redacted logging**

Create run directory `<ID>_<YYYYMMDD_HHMMSS>_<8hex>`. Validate artifact filenames against a fixed allowlist. JSON output is indented, sorted, and atomic. Command audit records executable/args, status, duration, and bounded redacted output. Logger has console and per-run file handlers without duplicate handlers.

- [ ] **Step 5: Implement JSON and text reports**

The JSON report is the complete result mapping. Text includes test metadata, device/environment, threat, expectations, hashes, integrity match, dotted differences with before/after, detection, status, restoration, evidence, errors, and notes. Report lookup accepts test ID prefix or exact safe filename and rejects traversal.

- [ ] **Step 6: Run tests**

Run: `python3 -m unittest unit_tests.test_baseline unit_tests.test_evidence unit_tests.test_report -v`

Expected: all tests pass and temporary directories contain both formats.

- [ ] **Step 7: Commit**

```bash
git add cyberscope/integrity/baseline.py cyberscope/reporting unit_tests
git commit -m "feat: persist baselines and capstone evidence"
```

---

### Task 4: Safe Scenario Lifecycle and Result Classification

**Files:**
- Create: `cyberscope/scenarios/__init__.py`
- Create: `cyberscope/scenarios/base.py`
- Create: `unit_tests/test_scenario_base.py`
- Modify: `cyberscope/models.py`

**Interfaces:**
- Consumes: state/integrity providers, diffing, evidence, reports, enums.
- Produces: `ScenarioMetadata`, `SecurityTestResult`, `BaseSecurityTest.run(context) -> SecurityTestResult`, overridable `precheck/capture_original_state/tamper/simulate_runtime/restore/verify_restoration`, `classify_result(...)`.

- [ ] **Step 1: Write failing lifecycle tests with an in-memory fake scenario**

```python
def test_restoration_runs_when_runtime_collection_raises(self):
    scenario = ExplodingScenario(...)
    result = scenario.run(context)
    self.assertTrue(scenario.restore_called)
    self.assertEqual(result.status, ResultStatus.ERROR)

def test_expected_change_and_digest_mismatch_is_pass(self):
    result = PassingScenario(...).run(context)
    self.assertEqual(result.status, ResultStatus.PASS)
    self.assertEqual(result.detection_result, "TRUE_POSITIVE")
```

- [ ] **Step 2: Run tests and confirm failures**

Run: `python3 -m unittest unit_tests.test_scenario_base -v`

- [ ] **Step 3: Extend typed result model**

`SecurityTestResult` contains every field required by the prompt: ID/name/category/description/threat/preconditions/original values/action/expected paths and behavior/actual differences/original and runtime hash/detection/integrity match/status/start/end/errors/restoration/evidence/environment mode/notes. JSON conversion serialises enums and datetimes to strings.

- [ ] **Step 4: Implement the final lifecycle**

The base implementation owns evidence creation, state collection, digesting, diffing, classification, and reports. It uses one outer error boundary and a `finally` restoration block only when mutation began. Simulation obtains explicit runtime state from the scenario; dry-run never calls tamper. Evidence write failures are retained in errors and do not prevent restoration attempts.

- [ ] **Step 5: Implement classification truth table**

```text
tampered + expected path + digest mismatch + detected => PASS / TRUE_POSITIVE
tampered + digest equal                           => FAIL / FALSE_NEGATIVE
tampered + wrong path only                        => FAIL / UNEXPECTED_CHANGE
not tampered + digest equal                       => PASS / TRUE_NEGATIVE
not tampered + digest mismatch                    => FAIL / FALSE_POSITIVE
unsupported or dry-run                            => SKIPPED
unexpected exception or restoration failure       => ERROR
```

- [ ] **Step 6: Test success, skip, dry-run, false-negative, unexpected-change, exception, and restoration-failure paths**

Run: `python3 -m unittest unit_tests.test_scenario_base -v`

Expected: all lifecycle branches pass and restoration is proven on both normal and exception paths.

- [ ] **Step 7: Commit**

```bash
git add cyberscope/models.py cyberscope/scenarios unit_tests/test_scenario_base.py
git commit -m "feat: orchestrate safe tampering lifecycle"
```

---

### Task 5: Controlled Software and Configuration Scenarios

**Files:**
- Create: `cyberscope/scenarios/software.py`
- Create: `cyberscope/scenarios/configuration.py`
- Create: `unit_tests/test_software_scenarios.py`
- Create: `unit_tests/test_configuration_scenarios.py`

**Interfaces:**
- Consumes: `BaseSecurityTest`, scenario context, controlled root, file measurements.
- Produces: classes for SW-001–SW-004 and CFG-001–CFG-005 with metadata and expected dotted paths.

- [ ] **Step 1: Write failing controlled-file scenario tests**

```python
def test_sw001_changes_hash_and_restores_original_bytes(self):
    target = self.root / "application.conf"
    target.write_text("mode=normal\n")
    result = SoftwareConfigModification(...).run(self.context)
    self.assertEqual(result.status, ResultStatus.PASS)
    self.assertEqual(target.read_text(), "mode=normal\n")

def test_cfg002_restores_mode(self):
    target = self.root / "test_config.conf"
    target.write_text("enabled=true\n")
    target.chmod(0o644)
    result = ConfigurationPermissionChange(...).run(self.context)
    self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)
```

- [ ] **Step 2: Implement shared controlled-resource behavior**

Restrict target resolution beneath `config.test_resources_dir`. Capture existence, bytes, and mode before mutation. Restore absent files by unlinking only the exact validated controlled target; restore existing files atomically and reapply original mode. Verify hash/mode/existence after restoration.

- [ ] **Step 3: Implement SW scenarios**

SW-001 changes controlled application config; SW-002 uses a labelled synthetic venv inventory addition in simulation and a fixture directory in normal mode without invoking pip; SW-003 changes controlled Python source; SW-004 creates a harmless `#!/usr/bin/env python3` script with mode `0755`. All clean up exactly their controlled targets.

- [ ] **Step 4: Implement CFG scenarios**

CFG-001 changes controlled config content. CFG-002 changes mode `0644` to `0600`. CFG-003 is simulation-only ownership transition. CFG-004 reuses hostname state mutation logic through composition, not inheritance duplication. CFG-005 collects SPI/I2C and simulates the state change; real mutation is unsupported and skipped.

- [ ] **Step 5: Test all software/configuration modes and restoration**

Run: `python3 -m unittest unit_tests.test_software_scenarios unit_tests.test_configuration_scenarios -v`

Expected: controlled normal/simulation tests pass, dry runs skip without writes, and protected/out-of-root paths are rejected.

- [ ] **Step 6: Commit**

```bash
git add cyberscope/scenarios/software.py cyberscope/scenarios/configuration.py unit_tests
git commit -m "feat: add reversible software and configuration tests"
```

---

### Task 6: Network and USB Scenarios

**Files:**
- Create: `cyberscope/scenarios/network.py`
- Create: `cyberscope/scenarios/usb.py`
- Create: `unit_tests/test_network_scenarios.py`
- Create: `unit_tests/test_usb_scenarios.py`

**Interfaces:**
- Consumes: base lifecycle, network/USB collectors, command runner, modes.
- Produces: NET-001–NET-005 and USB-001–USB-002; `usb_identity(device)`, added/removed USB classification.

- [ ] **Step 1: Write failing network simulation tests**

```python
def test_net001_simulation_changes_hostname_without_host_command(self):
    result = HostnameChange(...).run(simulation_context)
    self.assertEqual(result.environment_mode, "simulation")
    self.assertIn("network.hostname.value", [d.path for d in result.actual_changes])
    self.command_runner.assert_not_called()
```

- [ ] **Step 2: Implement network scenarios with conservative real-mode guards**

NET-001 supports simulated change and an injected real hostname strategy that captures, sets, restores, and verifies only under `--real-test`. NET-002/003 simulate DNS/interface-route changes. NET-004 collects SSID and skips if unavailable; simulation changes a fixture SSID. NET-005 simulates MAC and permits collection-only physical validation, never automatic spoofing.

- [ ] **Step 3: Write failing USB addition/removal tests**

```python
def test_usb001_marks_added_device_unauthorised(self):
    result = UsbConnection(...fixtures...).run(simulation_context)
    self.assertEqual(result.detection_result, "UNAUTHORISED_DEVICE_DETECTED")
    self.assertEqual(result.status, ResultStatus.PASS)
```

- [ ] **Step 4: Implement USB scenarios**

Stable identity is vendor/product/serial where present, falling back to manufacturer/product with an explicit low-confidence note. Interactive mode captures baseline, prints the physical instruction, waits for Enter through injected input, then recollects. EOF/cancel returns SKIPPED. Simulation uses deterministic fixtures and labels evidence. USB-001 expects additions; USB-002 expects removals.

- [ ] **Step 5: Run network and USB tests**

Run: `python3 -m unittest unit_tests.test_network_scenarios unit_tests.test_usb_scenarios -v`

Expected: simulations pass, unavailable physical features skip, interactive input is faked, and no real network command executes.

- [ ] **Step 6: Commit**

```bash
git add cyberscope/scenarios/network.py cyberscope/scenarios/usb.py unit_tests
git commit -m "feat: add network and USB integrity tests"
```

---

### Task 7: Registry, Stability Analysis, and Complete CLI

**Files:**
- Create: `cyberscope/scenarios/registry.py`
- Create: `cyberscope/scenarios/stability.py`
- Create: `cyberscope/cli.py`
- Create: `unit_tests/test_registry.py`
- Create: `unit_tests/test_stability.py`
- Create: `unit_tests/test_cli.py`
- Modify: `main.py`

**Interfaces:**
- Consumes: all providers, scenarios, baseline/report repositories.
- Produces: `ScenarioRegistry.list/get/category`, `run_stability(provider, integrity, iterations)`, `build_parser()`, `main(argv=None) -> int`.

- [ ] **Step 1: Write failing registry and stability tests**

```python
def test_registry_contains_every_named_test(self):
    self.assertEqual(
        set(registry.ids()),
        {"SW-001", "SW-002", "SW-003", "SW-004", "NET-001", "NET-002", "NET-003", "NET-004", "NET-005", "USB-001", "USB-002", "CFG-001", "CFG-002", "CFG-003", "CFG-004", "CFG-005"},
    )

def test_stability_reports_false_positive_rate(self):
    summary = run_stability(sequence_provider([stable, stable, changed]), integrity, 3)
    self.assertEqual(summary.matching_iterations, 2)
    self.assertEqual(summary.mismatching_iterations, 1)
    self.assertAlmostEqual(summary.false_positive_rate, 1 / 3)
```

- [ ] **Step 2: Implement registry and stability analysis**

Registry ordering is ID-sorted and rejects unknown IDs with available choices. Stability validates `1 <= iterations <= 10000`, uses sample one as baseline while counting it as a match, stores mismatch differences, and never hides variation behind a threshold.

- [ ] **Step 3: Write failing parser and CLI service tests**

Test every requested command shape, mutually invalid modes, positive iterations, unknown test IDs, baseline round trip in a temporary output root, report selection, and aggregation exit status. Inject providers/paths/input rather than patching real host state.

- [ ] **Step 4: Implement all argparse commands**

Create subparsers for `system-info`, `baseline create/show/compare`, `test list/software/network/usb/configuration/run/all/stability`, and `report list/show`. Support both prompt examples `test usb --interactive` and `test run USB-001 --simulation`. Category commands run every registered category scenario. Summary output lists status, detection, changed paths, restoration, and evidence location.

- [ ] **Step 5: Implement exit-status aggregation and entry point**

Return 0 only when informational work succeeds and requested tests are PASS/SKIPPED without ERROR/FAIL; return 1 for any FAIL/ERROR or stability mismatch; argparse retains 2 for usage errors. `main.py` is a three-line entry point with `raise SystemExit(main())`.

- [ ] **Step 6: Run CLI tests and smoke help/list commands**

Run: `python3 -m unittest unit_tests.test_registry unit_tests.test_stability unit_tests.test_cli -v`

Run: `python3 main.py --help`

Run: `python3 main.py test list`

Expected: tests pass, help lists all command groups, and registry lists 16 scenario IDs.

- [ ] **Step 7: Commit**

```bash
git add main.py cyberscope/cli.py cyberscope/scenarios/registry.py cyberscope/scenarios/stability.py unit_tests
git commit -m "feat: expose security testing CLI and stability checks"
```

---

### Task 8: Capstone Documentation and End-to-End Verification

**Files:**
- Create: `README.md`
- Create: `docs/THREAT_MODEL.md`
- Create: `docs/TEST_PLAN.md`
- Create: `docs/TEST_CASES.md`
- Create: `output/baselines/.gitkeep`
- Create: `output/evidence/.gitkeep`
- Create: `output/logs/.gitkeep`
- Create: `output/reports/.gitkeep`
- Create: `unit_tests/test_documentation.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: final CLI behavior and scenario metadata.
- Produces: operator instructions, threat/test traceability, maintained output layout, executable smoke evidence.

- [ ] **Step 1: Write failing documentation coverage test**

```python
def test_threats_and_test_ids_are_documented(self):
    threat_text = Path("docs/THREAT_MODEL.md").read_text()
    case_text = Path("docs/TEST_CASES.md").read_text()
    for threat in [f"T{i:02d}" for i in range(1, 9)]:
        self.assertIn(threat, threat_text)
    for test_id in registry.ids():
        self.assertIn(test_id, case_text)
```

- [ ] **Step 2: Write the README**

Cover purpose, architecture, Python installation, supported platforms, Raspberry Pi setup, VM/simulation setup, baseline create/show/compare, each test command, stability semantics, reports/evidence, adding providers and scenarios, safety/restoration, exit statuses, and limitations. Include explicit examples and state that physical limitations are not successful simulated attacks.

- [ ] **Step 3: Write threat model and test plan**

For T01–T08 include asset, actor, vector, affected parameter, expected control, I2Map behavior, and mapped test IDs. Test plan includes authorised scope, exclusions, environment setup, entry/exit criteria, common workflow, true/false positive/negative meanings, evidence custody, restoration checks, manual USB instructions, and final validation checklist.

- [ ] **Step 4: Write test-case catalogue**

Start with `ID | Category | Attack | Expected Parameter | Expected Result`, include all 16 IDs, then give each case threat, preconditions, baseline/action/expected difference/mode/restoration/limitations. Document stability as an additional non-attack validation case.

- [ ] **Step 5: Run complete automated verification**

Run: `python3 -m unittest discover -s unit_tests -v`

Run: `python3 -m compileall -q cyberscope main.py`

Run: `rg -n 'shell\s*=\s*True|shell=True' --glob '*.py' .`

Expected: all tests pass, compilation succeeds, and search returns no matches.

- [ ] **Step 6: Run safe end-to-end smoke suite**

Run sequentially:

```bash
python3 main.py system-info
python3 main.py baseline create
python3 main.py baseline show
python3 main.py baseline compare
python3 main.py test run SW-001
python3 main.py test run CFG-002
python3 main.py test run USB-001 --simulation
python3 main.py test run NET-001 --simulation
python3 main.py test all --dry-run
python3 main.py test stability --iterations 3
python3 main.py report list
```

Expected: informational commands succeed; controlled-file and simulation tests PASS; all dry runs SKIP without mutation; stability has three matching iterations on selected stable state; reports and evidence contain the required artifacts.

- [ ] **Step 7: Audit generated evidence and restoration**

Inspect the latest SW-001 and CFG-002 `result.json`, both text reports, their diff files, and the controlled test files. Confirm expected dotted paths are present, baseline/runtime digests differ, environment mode is honest, restoration is SUCCESS, and controlled files match pre-test content/modes.

- [ ] **Step 8: Commit final documentation**

```bash
git add README.md docs .gitignore output unit_tests/test_documentation.py
git commit -m "docs: add capstone threat model and test guide"
```

- [ ] **Step 9: Final repository audit**

Run:

```bash
git status --short
git log --oneline --decorate -10
python3 -m unittest discover -s unit_tests -v
```

Expected: clean worktree, incremental commits visible, and the complete suite passes from the repository root.
