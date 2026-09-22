import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from cyberscope.config import AppConfig
from cyberscope.integrity.providers import CanonicalIntegrityProvider
from cyberscope.models import CollectedState, RestorationStatus, ResultStatus, TestMode
from cyberscope.scenarios.base import BaseSecurityTest, ScenarioContext, ScenarioMetadata


class SequenceProvider:
    def __init__(self, states: list[CollectedState | Exception]) -> None:
        self.states = states

    def collect(self) -> CollectedState:
        item = self.states.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FixtureScenario(BaseSecurityTest):
    metadata = ScenarioMetadata(
        test_id="SW-999",
        name="Fixture change",
        category="software",
        description="Changes a fixture",
        threat="Test threat",
        preconditions=("Temporary directory is writable",),
        expected_changed_paths=("software.mode",),
        expected_i2map_behavior="Runtime hash differs",
    )

    def __init__(self, explode_restore: bool = False) -> None:
        self.restore_called = False
        self.explode_restore = explode_restore

    def capture_original_state(self, context: ScenarioContext) -> object:
        return {"saved": True}

    def tamper(self, context: ScenarioContext) -> str:
        return "changed fixture"

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        changed = deepcopy(baseline)
        changed.monitored["software"]["mode"] = "compromised"  # type: ignore[index]
        return changed

    def restore(self, original: object, context: ScenarioContext) -> None:
        self.restore_called = True
        if self.explode_restore:
            raise RuntimeError("restore exploded")

    def verify_restoration(self, original: object, context: ScenarioContext) -> bool:
        return self.restore_called


class ScenarioLifecycleTests(unittest.TestCase):
    def context(self, root: Path, states: list[CollectedState | Exception], mode: TestMode) -> ScenarioContext:
        config = AppConfig(root, root / "output", root / "resources")
        return ScenarioContext(config, SequenceProvider(states), CanonicalIntegrityProvider(), mode)

    def test_expected_simulated_change_and_digest_mismatch_is_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = CollectedState({"software": {"mode": "normal"}})
            result = FixtureScenario().run(self.context(Path(directory), [state], TestMode.SIMULATION))
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(result.detection_result, "TRUE_POSITIVE")
        self.assertEqual(result.environment_mode, "simulation")
        self.assertFalse(result.integrity_match)

    def test_restoration_runs_when_runtime_collection_raises(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scenario = FixtureScenario()
            state = CollectedState({"software": {"mode": "normal"}})
            result = scenario.run(self.context(Path(directory), [state, RuntimeError("collector exploded")], TestMode.NORMAL))
        self.assertTrue(scenario.restore_called)
        self.assertEqual(result.status, ResultStatus.ERROR)
        self.assertEqual(result.restoration_status, RestorationStatus.SUCCESS)

    def test_restoration_failure_turns_detection_into_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scenario = FixtureScenario(explode_restore=True)
            states = [
                CollectedState({"software": {"mode": "normal"}}),
                CollectedState({"software": {"mode": "compromised"}}),
            ]
            result = scenario.run(self.context(Path(directory), states, TestMode.NORMAL))
        self.assertEqual(result.status, ResultStatus.ERROR)
        self.assertEqual(result.restoration_status, RestorationStatus.FAILED)
        self.assertIn("restore exploded", " ".join(result.errors))

    def test_dry_run_skips_without_tampering_or_restoration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scenario = FixtureScenario()
            state = CollectedState({"software": {"mode": "normal"}})
            result = scenario.run(self.context(Path(directory), [state], TestMode.DRY_RUN))
        self.assertEqual(result.status, ResultStatus.SKIPPED)
        self.assertFalse(scenario.restore_called)
        self.assertEqual(result.restoration_status, RestorationStatus.NOT_REQUIRED)

    def test_equal_hash_after_tamper_is_false_negative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = CollectedState({"software": {"mode": "normal"}})
            result = FixtureScenario().run(self.context(Path(directory), [state, deepcopy(state)], TestMode.NORMAL))
        self.assertEqual(result.status, ResultStatus.FAIL)
        self.assertEqual(result.detection_result, "FALSE_NEGATIVE")


if __name__ == "__main__":
    unittest.main()
