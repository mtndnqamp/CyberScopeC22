import tempfile
import unittest
from pathlib import Path

from cyberscope.collectors.common import read_optional_text
from cyberscope.collectors.hardware import cpu_utilisation_between, stable_cpu_information
from cyberscope.collectors.software import collect_monitored_files, parse_os_release
from cyberscope.collectors.state import LinuxDeviceStateProvider


class CollectorTests(unittest.TestCase):
    def test_missing_optional_file_is_unsupported(self) -> None:
        value = read_optional_text(Path("/definitely/missing"), "not available")
        self.assertFalse(value.supported)
        self.assertEqual(value.reason, "not available")

    def test_os_release_parser_handles_quotes_and_ignores_comments(self) -> None:
        parsed = parse_os_release('NAME="Debian GNU/Linux"\n# comment\nVERSION_ID="13"\n')
        self.assertEqual(parsed, {"NAME": "Debian GNU/Linux", "VERSION_ID": "13"})

    def test_monitored_file_hash_changes_with_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "sensor.py"
            target.write_text("print('normal')\n", encoding="utf-8")
            before = collect_monitored_files([target])
            target.write_text("print('changed')\n", encoding="utf-8")
            after = collect_monitored_files([target])
        self.assertNotEqual(before[0]["sha256"], after[0]["sha256"])

    def test_aggregate_provider_exposes_all_parameter_categories(self) -> None:
        state = LinuxDeviceStateProvider(include_package_inventory=False).collect()
        self.assertEqual(
            set(state.monitored),
            {"schema_version", "environment", "software", "hardware", "network", "configuration", "usb"},
        )
        self.assertIn("cpu_utilisation_percent", state.diagnostic["hardware"])

    def test_stable_cpu_information_excludes_runtime_frequency(self) -> None:
        parsed = stable_cpu_information(
            "processor: 0\nmodel name: Test CPU\ncpu MHz: 1100.000\nSerial: abc\n"
            "processor: 1\nmodel name: Test CPU\ncpu MHz: 2200.000\n"
        )
        self.assertEqual(parsed, {"model name": ["Test CPU"], "serial": ["abc"]})

    def test_cpu_utilisation_is_calculated_from_proc_stat_deltas(self) -> None:
        before = "cpu  100 0 50 850 0 0 0 0\n"
        after = "cpu  150 0 70 880 0 0 0 0\n"
        self.assertEqual(cpu_utilisation_between(before, after), 70.0)


if __name__ == "__main__":
    unittest.main()
