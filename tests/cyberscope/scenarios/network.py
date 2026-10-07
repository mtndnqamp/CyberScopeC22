"""Conservative network tampering scenarios NET-001 through NET-005."""

from __future__ import annotations

from copy import deepcopy

from cyberscope.models import CollectedState, TestMode
from cyberscope.scenarios.base import BaseSecurityTest, ScenarioContext, ScenarioMetadata


class NetworkSimulationScenario(BaseSecurityTest):
    def precheck(self, context: ScenarioContext) -> str | None:
        if context.mode not in {TestMode.SIMULATION, TestMode.DRY_RUN}:
            return "This network mutation is simulation-only to prevent host disconnection"
        return None

    def tamper(self, context: ScenarioContext) -> str:
        raise RuntimeError("network mutation must not execute outside simulation")


class HostnameChange(NetworkSimulationScenario):
    metadata = ScenarioMetadata(
        "NET-001", "Hostname modification", "network",
        "Detect a hostname transition without assuming a hostname proves device type.",
        "T04 — Network configuration modification", ("Simulation mode is available",),
        ("network.hostname.value",), "Runtime I2Map differs from baseline",
    )

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        runtime.monitored["network"]["hostname"]["value"] = "compromised-pi"  # type: ignore[index]
        if "configuration" in runtime.monitored:
            runtime.monitored["configuration"]["hostname"]["value"] = "compromised-pi"  # type: ignore[index]
        return runtime


class DnsConfigurationChange(NetworkSimulationScenario):
    metadata = ScenarioMetadata(
        "NET-002", "DNS configuration change", "network",
        "Model a resolver change without overwriting the host resolver file.",
        "T05 — Rogue/changed network settings", ("Simulation mode is available",),
        ("network.dns_servers.value",), "Runtime I2Map differs from baseline",
    )

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        runtime.monitored["network"]["dns_servers"] = {"supported": True, "value": ["203.0.113.53"], "reason": None}  # type: ignore[index]
        return runtime


class NetworkInterfaceChange(NetworkSimulationScenario):
    metadata = ScenarioMetadata(
        "NET-003", "Network interface configuration change", "network",
        "Model assigned address, subnet, and gateway changes without disconnecting the host.",
        "T04 — Network configuration modification", ("Simulation mode is available",),
        ("network.interfaces.value", "network.default_routes.value"), "Runtime I2Map differs from baseline",
    )

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        network = runtime.monitored["network"]  # type: ignore[assignment]
        network["interfaces"] = {"supported": True, "value": [{"name": "eth0", "address": "00:11:22:33:44:55", "addresses": [{"family": "inet", "local": "192.0.2.20", "prefixlen": 24}]}], "reason": None}
        network["default_routes"] = {"supported": True, "value": [{"gateway": "192.0.2.1"}], "reason": None}
        return runtime


class WirelessSsidChange(NetworkSimulationScenario):
    metadata = ScenarioMetadata(
        "NET-004", "Wireless SSID change", "network",
        "Detect a changed monitored wireless identity without connecting to another network.",
        "T05 — Rogue/changed network settings", ("Wireless state is available or simulation mode is used",),
        ("network.wireless_ssid.value",), "Runtime I2Map differs from baseline",
    )

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        runtime.monitored["network"]["wireless_ssid"] = {"supported": True, "value": "RogueLabSSID", "reason": None}  # type: ignore[index]
        return runtime


class MacAddressChange(NetworkSimulationScenario):
    metadata = ScenarioMetadata(
        "NET-005", "MAC address change detection", "network",
        "Detect a MAC transition while refusing to spoof the active host interface.",
        "T05 — Rogue/changed network settings", ("Simulation mode is available",),
        ("network.interfaces.value",), "Runtime I2Map differs from baseline",
    )

    def precheck(self, context: ScenarioContext) -> str | None:
        if context.mode not in {TestMode.SIMULATION, TestMode.DRY_RUN}:
            return "Automatic MAC spoofing is disabled; use --simulation for safe detection testing"
        return None

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        interfaces = runtime.monitored["network"]["interfaces"].get("value", [])  # type: ignore[index,union-attr]
        if isinstance(interfaces, list) and interfaces:
            interfaces[0] = {**interfaces[0], "address": "02:00:00:00:00:99"}
        return runtime
