import tempfile
import unittest
from pathlib import Path

from cyberscope.collectors.state import LinuxDeviceStateProvider
from cyberscope.config import AppConfig
from cyberscope.integrity.providers import CanonicalIntegrityProvider
from cyberscope.models import ResultStatus, TestMode
from cyberscope.scenarios.base import ScenarioContext
from cyberscope.scenarios.software import (
    ApplicationConfigModification,
    UnauthorizedExecutable,
)


class SoftwareScenarioTests(unittest.TestCase):
    def context(self, root: Path, target: Path, mode: TestMode = TestMode.NORMAL) -> ScenarioContext:
        config = AppConfig(root, root / "output", root / "resources")
        return ScenarioContext(config, LinuxDeviceStateProvider((target,), include_package_inventory=False), CanonicalIntegrityProvider(), mode)

    def test_sw001_changes_hash_and_restores_original_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "resources" / "application.conf"
            target.parent.mkdir()
            target.write_text("custom=original\n", encoding="utf-8")
            result = ApplicationConfigModification(target).run(self.context(root, target))
            self.assertEqual(target.read_text(encoding="utf-8"), "custom=original\n")
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertFalse(result.integrity_match)
        self.assertTrue(any(item.path == "software.monitored_files" for item in result.actual_changes))
        self.assertFalse(any(item.path == "configuration.monitored_files" for item in result.actual_changes))
        file_difference = next(item for item in result.actual_changes if item.path == "software.monitored_files")
        self.assertEqual(file_difference.before[0]["mode"], file_difference.after[0]["mode"])  # type: ignore[index]

    def test_sw004_removes_executable_that_did_not_exist_before_test(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "resources" / "unauthorized_tool.py"
            target.parent.mkdir()
            result = UnauthorizedExecutable(target).run(self.context(root, target))
            self.assertFalse(target.exists())
        self.assertEqual(result.status, ResultStatus.PASS)

    def test_dry_run_does_not_create_controlled_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "resources" / "application.conf"
            target.parent.mkdir()
            result = ApplicationConfigModification(target).run(self.context(root, target, TestMode.DRY_RUN))
            self.assertFalse(target.exists())
        self.assertEqual(result.status, ResultStatus.SKIPPED)


if __name__ == "__main__":
    unittest.main()
