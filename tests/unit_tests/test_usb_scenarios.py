import tempfile
import unittest
from pathlib import Path

from cyberscope.config import AppConfig
from cyberscope.integrity.providers import CanonicalIntegrityProvider
from cyberscope.models import CollectedState, ResultStatus, TestMode
from cyberscope.scenarios.base import ScenarioContext
from cyberscope.scenarios.usb import UsbConnection, UsbRemoval, usb_identity


TRUSTED = {"vendor_id": "1d6b", "product_id": "0002", "manufacturer": "Linux Foundation", "product": "Hub", "serial": None}
NEW = {"vendor_id": "0781", "product_id": "5591", "manufacturer": "SanDisk", "product": "Ultra", "serial": "ABC123"}


class SequenceProvider:
    def __init__(self, states: list[CollectedState]) -> None:
        self.states = states

    def collect(self) -> CollectedState:
        return self.states.pop(0)


def usb_state(devices: list[dict[str, object]]) -> CollectedState:
    return CollectedState({"usb": {"devices": {"supported": True, "value": devices, "reason": None}, "source": "fixture"}})


class UsbScenarioTests(unittest.TestCase):
    def context(self, root: Path, states: list[CollectedState], mode: TestMode, interactive: bool = False) -> ScenarioContext:
        return ScenarioContext(
            AppConfig(root, root / "output", root / "resources"),
            SequenceProvider(states),
            CanonicalIntegrityProvider(),
            mode,
            interactive=interactive,
            input_function=lambda _prompt: "",
        )

    def test_usb_identity_prefers_serial(self) -> None:
        self.assertEqual(usb_identity(NEW), "0781:5591:ABC123")

    def test_usb001_marks_added_device_unauthorised(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = UsbConnection().run(self.context(Path(directory), [usb_state([TRUSTED])], TestMode.SIMULATION))
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(result.detection_result, "UNAUTHORISED_DEVICE_DETECTED")

    def test_usb002_detects_trusted_device_removal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = UsbRemoval().run(self.context(Path(directory), [usb_state([TRUSTED, NEW])], TestMode.SIMULATION))
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(result.detection_result, "TRUSTED_DEVICE_REMOVED")

    def test_usb002_empty_inventory_is_skipped_not_fabricated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = UsbRemoval().run(self.context(Path(directory), [usb_state([])], TestMode.SIMULATION))
        self.assertEqual(result.status, ResultStatus.SKIPPED)
        self.assertIn("baseline USB", " ".join(result.notes))

    def test_physical_usb_requires_interactive_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = UsbConnection().run(self.context(Path(directory), [usb_state([TRUSTED])], TestMode.NORMAL))
        self.assertEqual(result.status, ResultStatus.SKIPPED)

    def test_interactive_usb_prompts_for_and_verifies_physical_restoration(self) -> None:
        prompts: list[str] = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context = ScenarioContext(
                AppConfig(root, root / "output", root / "resources"),
                SequenceProvider([usb_state([TRUSTED]), usb_state([TRUSTED, NEW]), usb_state([TRUSTED])]),
                CanonicalIntegrityProvider(),
                TestMode.NORMAL,
                interactive=True,
                input_function=lambda prompt: prompts.append(prompt) or "",
            )
            result = UsbConnection().run(context)
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(result.restoration_status.value, "SUCCESS")
        self.assertEqual(len(prompts), 2)
        self.assertIn("restore", prompts[1].lower())


if __name__ == "__main__":
    unittest.main()
