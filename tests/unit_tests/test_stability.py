import unittest

from cyberscope.integrity.providers import CanonicalIntegrityProvider
from cyberscope.models import CollectedState
from cyberscope.scenarios.stability import run_stability


class SequenceProvider:
    def __init__(self, states: list[CollectedState]) -> None:
        self.states = states

    def collect(self) -> CollectedState:
        return self.states.pop(0)


class StabilityTests(unittest.TestCase):
    def test_stability_reports_false_positive_rate(self) -> None:
        stable = CollectedState({"hostname": "pi"})
        changed = CollectedState({"hostname": "unexpected"})
        summary = run_stability(SequenceProvider([stable, stable, changed]), CanonicalIntegrityProvider(), 3)
        self.assertEqual(summary.matching_iterations, 2)
        self.assertEqual(summary.mismatching_iterations, 1)
        self.assertAlmostEqual(summary.false_positive_rate, 1 / 3)
        self.assertEqual(summary.mismatches[0]["differences"][0]["path"], "hostname")

    def test_iterations_must_be_positive_and_bounded(self) -> None:
        provider = SequenceProvider([])
        for value in (0, -1, 10_001):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_stability(provider, CanonicalIntegrityProvider(), value)


if __name__ == "__main__":
    unittest.main()
