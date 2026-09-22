import json
import tempfile
import unittest
from pathlib import Path

from cyberscope.reporting.evidence import EvidenceSession


class EvidenceTests(unittest.TestCase):
    def test_session_creates_named_directory_and_json_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session = EvidenceSession.create(Path(directory), "SW-001")
            artifact = session.write_json("baseline.json", {"hash": "abc"})
            self.assertTrue(session.root.name.startswith("SW-001_"))
            self.assertEqual(json.loads(artifact.read_text()), {"hash": "abc"})
            self.assertTrue((session.root / "commands.log").exists())
            self.assertTrue((session.root / "run.log").exists())

    def test_unlisted_artifact_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session = EvidenceSession.create(Path(directory), "SW-001")
            with self.assertRaises(ValueError):
                session.write_json("../outside.json", {})


if __name__ == "__main__":
    unittest.main()
