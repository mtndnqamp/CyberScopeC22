"""Controlled software-state tampering scenarios SW-001 through SW-004."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from cyberscope.models import CollectedState
from cyberscope.scenarios.base import ScenarioContext, ScenarioMetadata
from cyberscope.scenarios.controlled_files import ControlledFileScenario


class ApplicationConfigModification(ControlledFileScenario):
    metadata = ScenarioMetadata(
        "SW-001", "Application configuration modification", "software",
        "Modify a monitored controlled application configuration file.",
        "T01 — Malicious software modification", ("Controlled test directory is writable",),
        ("software.monitored_files",), "Runtime I2Map differs from baseline",
    )
    baseline_content = "mode=normal\n"
    modified_content = "mode=compromised\n"


class IsolatedPackageAddition(ControlledFileScenario):
    metadata = ScenarioMetadata(
        "SW-002", "Isolated package inventory addition", "software",
        "Introduce a harmless package marker in a controlled virtual-environment fixture.",
        "T02 — Unauthorised application/package installation", ("Controlled test directory is writable",),
        ("software.python_packages",), "Runtime I2Map differs from baseline",
    )

    def precheck(self, context: ScenarioContext) -> str | None:
        blocked = super().precheck(context)
        if blocked:
            return blocked
        if context.mode.value not in {"simulation", "dry-run"}:
            return "Package inventory addition is simulation-only; system Python is never modified"
        return None

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        packages = runtime.monitored["software"].setdefault("python_packages", [])  # type: ignore[union-attr]
        if isinstance(packages, list):
            packages.append({"name": "cyberscope-dummy-package", "version": "0.0"})
        return runtime

    def tamper(self, context: ScenarioContext) -> str:
        super().tamper(context)
        return "Created isolated dummy package marker; system Python unchanged"


class SourceFileModification(ControlledFileScenario):
    metadata = ScenarioMetadata(
        "SW-003", "Test application source modification", "software",
        "Add a harmless source comment to a controlled sensor application.",
        "T01 — Malicious software modification", ("Controlled test directory is writable",),
        ("software.monitored_files",), "Runtime I2Map differs from baseline",
    )
    baseline_content = "def read_sensor():\n    return 21.0\n"
    modified_content = "# harmless integrity-test modification\ndef read_sensor():\n    return 21.0\n"


class UnauthorizedExecutable(ControlledFileScenario):
    metadata = ScenarioMetadata(
        "SW-004", "Simulated unauthorised executable", "software",
        "Create a harmless executable script inside the controlled test directory.",
        "T01 — Malicious software modification", ("Controlled test directory is writable",),
        ("software.monitored_files",), "Runtime I2Map differs from baseline",
    )
    baseline_content = ""
    modified_content = "#!/usr/bin/env python3\nprint('CyberScope harmless test executable')\n"
    baseline_mode = 0o644

    def prepare_baseline(self, context: ScenarioContext) -> None:
        if self.target.exists():
            self.target.unlink()

    def tamper(self, context: ScenarioContext) -> str:
        super().tamper(context)
        self.target.chmod(0o755)
        return "Created harmless controlled executable"

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        rows = runtime.monitored["software"]["monitored_files"]  # type: ignore[index]
        replacement = {"path": str(self.target), "exists": True, "sha256": "simulated-executable", "mode": "0755", "uid": 1000, "gid": 1000, "size": 65}
        if isinstance(rows, list) and rows:
            rows[0] = replacement
        return runtime
