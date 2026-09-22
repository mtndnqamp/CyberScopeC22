import json
import tempfile
import unittest
from pathlib import Path

from cyberscope.integrity.baseline import BaselineRepository, BaselineValidationError
from cyberscope.integrity.providers import CanonicalIntegrityProvider
from cyberscope.models import CollectedState


class BaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repository = BaselineRepository(Path(self.temp.name))
        self.integrity = CanonicalIntegrityProvider()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_saved_baseline_round_trips_and_verifies_digest(self) -> None:
        state = CollectedState({"software": {"os": "Linux"}}, {"sample": 1})
        record = self.repository.create(state, self.integrity, {"kind": "LINUX_VM"})
        loaded = self.repository.load(record.path.name, self.integrity)
        self.assertEqual(loaded.digest, record.digest)
        self.assertEqual(loaded.monitored_state, state.monitored)
        self.assertTrue((Path(self.temp.name) / "latest.json").exists())

    def test_modified_baseline_is_rejected(self) -> None:
        record = self.repository.create(CollectedState({"host": "trusted"}), self.integrity)
        content = json.loads(record.path.read_text())
        content["monitored_state"]["host"] = "tampered"
        record.path.write_text(json.dumps(content))
        with self.assertRaisesRegex(BaselineValidationError, "digest"):
            self.repository.load(record.path.name, self.integrity)

    def test_path_traversal_is_rejected(self) -> None:
        with self.assertRaises(BaselineValidationError):
            self.repository.load("../prompt.md", self.integrity)


if __name__ == "__main__":
    unittest.main()
