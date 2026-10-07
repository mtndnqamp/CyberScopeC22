import os
import tempfile
import unittest
from pathlib import Path

from cyberscope.collectors.state import LinuxDeviceStateProvider
from cyberscope.config import AppConfig
from cyberscope.integrity.providers import CanonicalIntegrityProvider
from cyberscope.models import ResultStatus, TestMode
from cyberscope.scenarios.base import ScenarioContext
from cyberscope.scenarios.configuration import ConfigurationPermissionChange, FileOwnershipChange


class ConfigurationScenarioTests(unittest.TestCase):
    def context(self, root: Path, target: Path, mode: TestMode) -> ScenarioContext:
        config = AppConfig(root, root / "output", root / "resources")
        return ScenarioContext(
            config,
            LinuxDeviceStateProvider(include_package_inventory=False, configuration_paths=(target,)),
            CanonicalIntegrityProvider(),
            mode,
        )

    @unittest.skipUnless(os.name == "posix", "Requires POSIX chmod permission semantics")
    def test_cfg002_changes_mode_and_restores_original_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "resources" / "test_config.conf"
            target.parent.mkdir()
            target.write_text("enabled=true\n", encoding="utf-8")
            target.chmod(0o644)
            result = ConfigurationPermissionChange(target).run(self.context(root, target, TestMode.NORMAL))
            self.assertEqual(os.stat(target).st_mode & 0o777, 0o644)
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertTrue(any(item.path == "configuration.monitored_files" for item in result.actual_changes))
        self.assertFalse(any(item.path == "software.monitored_files" for item in result.actual_changes))

    def test_cfg003_simulation_is_honestly_labelled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "resources" / "owned.conf"
            target.parent.mkdir()
            target.write_text("safe=true\n", encoding="utf-8")
            result = FileOwnershipChange(target).run(self.context(root, target, TestMode.SIMULATION))
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(result.environment_mode, "simulation")
        self.assertIn("no physical attack", result.tampering_action.lower())


if __name__ == "__main__":
    unittest.main()
