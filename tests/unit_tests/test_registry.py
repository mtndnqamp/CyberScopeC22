import tempfile
import unittest
from pathlib import Path

from cyberscope.config import AppConfig
from cyberscope.scenarios.registry import build_registry


EXPECTED_IDS = {
    "SW-001", "SW-002", "SW-003", "SW-004",
    "NET-001", "NET-002", "NET-003", "NET-004", "NET-005",
    "USB-001", "USB-002",
    "CFG-001", "CFG-002", "CFG-003", "CFG-004", "CFG-005",
}


class RegistryTests(unittest.TestCase):
    def test_registry_contains_every_named_test(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = build_registry(AppConfig(root, root / "output", root / "resources"))
        self.assertEqual(set(registry.ids()), EXPECTED_IDS)

    def test_unknown_test_lists_available_choice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = build_registry(AppConfig(root, root / "output", root / "resources"))
            with self.assertRaisesRegex(KeyError, "SW-001"):
                registry.get("BAD-001")


if __name__ == "__main__":
    unittest.main()
