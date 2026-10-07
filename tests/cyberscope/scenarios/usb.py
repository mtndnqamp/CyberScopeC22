"""Interactive and simulated USB tampering scenarios."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from cyberscope.models import CollectedState, ResultStatus, SecurityTestResult, TestMode
from cyberscope.scenarios.base import BaseSecurityTest, ScenarioContext, ScenarioMetadata


SIMULATED_USB = {
    "vendor_id": "0781",
    "product_id": "5591",
    "manufacturer": "SanDisk",
    "product": "Ultra (simulated)",
    "serial": "CYBERSCOPE-SIM-001",
}


def usb_identity(device: dict[str, Any]) -> str:
    vendor = str(device.get("vendor_id") or "unknown")
    product = str(device.get("product_id") or "unknown")
    serial = device.get("serial")
    if serial:
        return f"{vendor}:{product}:{serial}"
    return f"{vendor}:{product}:{device.get('manufacturer') or 'unknown'}:{device.get('product') or 'unknown'}"


def _devices(state: CollectedState) -> list[dict[str, Any]]:
    try:
        value = state.monitored["usb"]["devices"]["value"]  # type: ignore[index]
    except (KeyError, TypeError):
        return []
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    return []


class UsbScenario(BaseSecurityTest):
    instruction = "Change the USB device state, then press ENTER when ready: "

    def __init__(self) -> None:
        self._baseline_identities: tuple[str, ...] = ()

    def precheck(self, context: ScenarioContext) -> str | None:
        if context.mode in {TestMode.SIMULATION, TestMode.DRY_RUN}:
            return None
        if not context.interactive:
            return "Physical USB testing requires --interactive"
        return None

    def capture_original_state(self, context: ScenarioContext) -> object:
        return None

    def validate_baseline(self, baseline: CollectedState, context: ScenarioContext) -> str | None:
        self._baseline_identities = tuple(sorted(usb_identity(item) for item in _devices(baseline)))
        return None

    def tamper(self, context: ScenarioContext) -> str:
        context.input_function(self.instruction)
        return "Operator performed an authorised physical USB state change"

    def restore(self, original: object, context: ScenarioContext) -> None:
        if context.interactive:
            context.input_function("Restore the original USB device arrangement, then press ENTER to verify restoration: ")

    def verify_restoration(self, original: object, context: ScenarioContext) -> bool:
        if not context.interactive:
            return True
        restored = context.device_state_provider.collect()
        identities = tuple(sorted(usb_identity(item) for item in _devices(restored)))
        return identities == self._baseline_identities


class UsbConnection(UsbScenario):
    metadata = ScenarioMetadata(
        "USB-001", "Unauthorised USB device connection", "usb",
        "Detect a newly connected USB device by stable identity fields.",
        "T06 — Unauthorised USB device connection", ("USB inventory is available or simulation mode is used",),
        ("usb.devices.value",), "Runtime I2Map differs and new device is identified",
    )
    instruction = "Insert the authorised test USB device, then press ENTER when ready: "

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        devices = _devices(runtime)
        devices.append(dict(SIMULATED_USB))
        # An unsupported collector returns a detached empty list: attach the synthetic inventory.
        runtime.monitored["usb"]["devices"] = {"supported": True, "value": devices, "reason": None}
        runtime.monitored["usb"]["source"] = "simulation"
        return runtime

    def after_evaluate(self, result: SecurityTestResult, baseline: CollectedState, runtime: CollectedState, context: ScenarioContext) -> None:
        before = {usb_identity(item) for item in _devices(baseline)}
        added = [item for item in _devices(runtime) if usb_identity(item) not in before]
        if result.status is ResultStatus.PASS and added:
            result.detection_result = "UNAUTHORISED_DEVICE_DETECTED"
            result.notes.extend(f"New USB device: {usb_identity(item)}" for item in added)


class UsbRemoval(UsbScenario):
    metadata = ScenarioMetadata(
        "USB-002", "Trusted USB device removal", "usb",
        "Detect when a device present in the trusted baseline disappears.",
        "T03 — Device configuration modification", ("At least one baseline USB device exists or simulation mode is used",),
        ("usb.devices.value",), "Runtime I2Map differs and removed device is identified",
    )
    instruction = "Remove one trusted test USB device, then press ENTER when ready: "

    def validate_baseline(self, baseline: CollectedState, context: ScenarioContext) -> str | None:
        super().validate_baseline(baseline, context)
        if not _devices(baseline):
            return "No device exists in the baseline USB inventory to remove"
        return None

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        devices = _devices(runtime)
        devices.pop()
        return runtime

    def after_evaluate(self, result: SecurityTestResult, baseline: CollectedState, runtime: CollectedState, context: ScenarioContext) -> None:
        after = {usb_identity(item) for item in _devices(runtime)}
        removed = [item for item in _devices(baseline) if usb_identity(item) not in after]
        if result.status is ResultStatus.PASS and removed:
            result.detection_result = "TRUSTED_DEVICE_REMOVED"
            result.notes.extend(f"Removed USB device: {usb_identity(item)}" for item in removed)
