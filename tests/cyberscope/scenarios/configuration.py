"""Configuration tampering scenarios CFG-001 through CFG-005."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from cyberscope.models import CollectedState
from cyberscope.scenarios.base import ScenarioContext, ScenarioMetadata
from cyberscope.scenarios.controlled_files import ControlledFileScenario


class ConfigurationFileModification(ControlledFileScenario):
    state_category = "configuration"
    metadata = ScenarioMetadata(
        "CFG-001", "Configuration file modification", "configuration",
        "Modify one field in a controlled monitored configuration file.",
        "T07 — Configuration-file modification", ("Controlled test directory is writable",),
        ("configuration.monitored_files",), "Runtime I2Map differs from baseline",
    )
    baseline_content = "telemetry=enabled\n"
    modified_content = "telemetry=disabled\n"


class ConfigurationPermissionChange(ConfigurationFileModification):
    metadata = ScenarioMetadata(
        "CFG-002", "Configuration file permission change", "configuration",
        "Change a controlled file from mode 0644 to 0600.",
        "T08 — Configuration permission modification", ("Controlled test directory is writable",),
        ("configuration.monitored_files",), "Runtime I2Map differs from baseline",
    )

    def tamper(self, context: ScenarioContext) -> str:
        self.target.chmod(0o600)
        return "Changed controlled configuration permissions from 0644 to 0600"

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        rows = runtime.monitored["configuration"]["monitored_files"]  # type: ignore[index]
        if isinstance(rows, list) and rows:
            rows[0] = {**rows[0], "mode": "0600"}
        return runtime


class FileOwnershipChange(ConfigurationFileModification):
    metadata = ScenarioMetadata(
        "CFG-003", "Configuration file ownership change", "configuration",
        "Simulate a controlled configuration ownership transition.",
        "T03 — Device configuration modification", ("Simulation mode is available",),
        ("configuration.monitored_files",), "Runtime I2Map differs from baseline",
    )

    def precheck(self, context: ScenarioContext) -> str | None:
        blocked = super().precheck(context)
        if blocked:
            return blocked
        if context.mode.value not in {"simulation", "dry-run"}:
            return "Ownership mutation is simulation-only in this safe release"
        return None

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        rows = runtime.monitored["configuration"]["monitored_files"]  # type: ignore[index]
        if isinstance(rows, list) and rows:
            rows[0] = {**rows[0], "uid": 65534, "gid": 65534}
        return runtime


class DeviceHostnameChange(ConfigurationFileModification):
    metadata = ScenarioMetadata(
        "CFG-004", "Device hostname change", "configuration",
        "Detect a hostname state transition under configuration threat mapping.",
        "T03 — Device configuration modification", ("Simulation mode is available",),
        ("configuration.hostname.value",), "Runtime I2Map differs from baseline",
    )

    def precheck(self, context: ScenarioContext) -> str | None:
        if context.mode.value not in {"simulation", "dry-run"}:
            return "Hostname mutation requires simulation or the guarded network scenario"
        return None

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        runtime.monitored["configuration"]["hostname"]["value"] = "compromised-pi"  # type: ignore[index]
        return runtime


class EnabledInterfaceChange(ConfigurationFileModification):
    metadata = ScenarioMetadata(
        "CFG-005", "Enabled interface configuration change", "configuration",
        "Detect a simulated SPI/I2C enabled-state transition without enabling debug interfaces.",
        "T03 — Device configuration modification", ("Simulation mode is available",),
        ("configuration.enabled_interfaces",), "Runtime I2Map differs from baseline",
    )

    def precheck(self, context: ScenarioContext) -> str | None:
        if context.mode.value not in {"simulation", "dry-run"}:
            return "Interface mutation is simulation-only; no debug interface is automatically enabled"
        return None

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        runtime.monitored["configuration"]["enabled_interfaces"] = {"supported": True, "value": ["spidev0.0"], "reason": None}  # type: ignore[index]
        return runtime
