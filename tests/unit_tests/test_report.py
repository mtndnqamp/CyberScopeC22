import json
import tempfile
import unittest
from pathlib import Path

from cyberscope.reporting.report import ReportWriter


def sample_result() -> dict[str, object]:
    return {
        "test_id": "SW-001",
        "test_name": "Application configuration modification",
        "category": "software",
        "timestamp": "2026-09-15T15:30:00+10:00",
        "device": "test-host",
        "operating_system": "Linux",
        "environment": "LINUX_VM",
        "environment_mode": "simulation",
        "threat": "Malicious software modification",
        "expected_result": "Hash changes",
        "baseline_hash": "aaa",
        "runtime_hash": "bbb",
        "integrity_match": False,
        "changed_parameters": [{"path": "software.file.sha256", "kind": "changed", "before": "aaa", "after": "bbb"}],
        "detection_result": "TRUE_POSITIVE",
        "status": "PASS",
        "restoration_status": "SUCCESS",
        "evidence": ["baseline.json"],
        "errors": [],
        "notes": [],
    }


class ReportTests(unittest.TestCase):
    def test_report_contains_required_headings_and_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            json_path, text_path = ReportWriter(Path(directory)).write(sample_result())
            text = text_path.read_text()
            self.assertIn("CyberScope Security Test Report", text)
            self.assertIn("Changed Parameters:", text)
            self.assertIn("Restoration:", text)
            self.assertEqual(json.loads(json_path.read_text())["status"], "PASS")

    def test_report_lookup_rejects_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            writer = ReportWriter(Path(directory))
            with self.assertRaises(ValueError):
                writer.find("../secret")


if __name__ == "__main__":
    unittest.main()
