"""Repeated unchanged-state false-positive analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cyberscope.integrity.comparison import diff_values
from cyberscope.integrity.providers import DeviceStateProvider, IntegrityProvider


@dataclass(frozen=True)
class StabilitySummary:
    iterations: int
    matching_iterations: int
    mismatching_iterations: int
    false_positive_rate: float
    baseline_hash: str
    hashes: list[str]
    mismatches: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "iterations": self.iterations,
            "matching_iterations": self.matching_iterations,
            "mismatching_iterations": self.mismatching_iterations,
            "false_positive_rate": self.false_positive_rate,
            "baseline_hash": self.baseline_hash,
            "hashes": self.hashes,
            "mismatches": self.mismatches,
        }


def run_stability(
    provider: DeviceStateProvider,
    integrity: IntegrityProvider,
    iterations: int = 100,
    max_iterations: int = 10_000,
) -> StabilitySummary:
    if isinstance(iterations, bool) or not isinstance(iterations, int) or not 1 <= iterations <= max_iterations:
        raise ValueError(f"iterations must be between 1 and {max_iterations}")
    baseline = provider.collect()
    baseline_hash = integrity.digest(baseline.monitored)
    hashes = [baseline_hash]
    mismatches: list[dict[str, Any]] = []
    for index in range(1, iterations):
        runtime = provider.collect()
        digest = integrity.digest(runtime.monitored)
        hashes.append(digest)
        if digest != baseline_hash:
            mismatches.append({
                "iteration": index + 1,
                "hash": digest,
                "differences": [item.to_dict() for item in diff_values(baseline.monitored, runtime.monitored)],
            })
    mismatch_count = len(mismatches)
    return StabilitySummary(
        iterations,
        iterations - mismatch_count,
        mismatch_count,
        mismatch_count / iterations,
        baseline_hash,
        hashes,
        mismatches,
    )
