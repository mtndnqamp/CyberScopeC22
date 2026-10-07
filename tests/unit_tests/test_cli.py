import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from cyberscope.cli import build_parser, main
from cyberscope.config import AppConfig


class CliTests(unittest.TestCase):
    def config(self, root: Path) -> AppConfig:
        return AppConfig(root, root / "output", root / "resources")

    def test_parser_accepts_requested_command_shapes(self) -> None:
        parser = build_parser()
        self.assertEqual(parser.parse_args(["baseline", "create"]).baseline_command, "create")
        self.assertEqual(parser.parse_args(["test", "run", "USB-001", "--simulation"]).test_id, "USB-001")
        self.assertTrue(parser.parse_args(["test", "run", "NET-005", "--simulate"]).simulation)
        self.assertEqual(parser.parse_args(["test", "stability", "--iterations", "100"]).iterations, 100)
        self.assertTrue(parser.parse_args(["test", "usb", "--interactive"]).interactive)

    def test_test_list_prints_all_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()) as output:
            exit_code = main(["test", "list"], config=self.config(Path(directory)))
        self.assertEqual(exit_code, 0)
        self.assertIn("USB-001", output.getvalue())
        self.assertIn("CFG-005", output.getvalue())

    def test_system_info_creates_python_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            exit_code = main(["system-info"], config=self.config(root))
            logs = list((root / "output" / "logs").glob("cyberscope_*.log"))
            log_text = logs[0].read_text(encoding="utf-8") if logs else ""
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(logs), 1)
        self.assertIn("system-info", log_text)

    def test_shorthand_simulation_runs_usb_test(self) -> None:
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()) as output:
            exit_code = main(["test", "USB-001", "--simulation"], config=self.config(Path(directory)))
        self.assertEqual(exit_code, 0)
        self.assertIn("UNAUTHORISED_DEVICE_DETECTED", output.getvalue())

    def test_controlled_sw001_restores_absent_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            exit_code = main(["test", "run", "SW-001"], config=self.config(root))
            self.assertFalse((root / "resources" / "application.conf").exists())
        self.assertEqual(exit_code, 0)

    def test_stability_writes_json_and_text_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            exit_code = main(["test", "stability", "--iterations", "1"], config=self.config(root))
            report_names = {path.name for path in (root / "output" / "reports").iterdir()}
        self.assertEqual(exit_code, 0)
        self.assertTrue(any(name.startswith("STABILITY_") and name.endswith(".json") for name in report_names))
        self.assertTrue(any(name.startswith("STABILITY_") and name.endswith(".txt") for name in report_names))


if __name__ == "__main__":
    unittest.main()
