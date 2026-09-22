"""Reusable safety lifecycle for all CyberScope attack tests."""

from __future__ import annotations

import platform
import socket
import logging
from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cyberscope.config import AppConfig
from cyberscope.integrity.comparison import diff_values
from cyberscope.integrity.providers import DeviceStateProvider, IntegrityProvider
from cyberscope.models import (
    CollectedState,
    Difference,
    RestorationStatus,
    ResultStatus,
    SecurityTestResult,
    TestMode,
)
from cyberscope.reporting.evidence import EvidenceSession
from cyberscope.reporting.report import ReportWriter


@dataclass(frozen=True)
class ScenarioMetadata:
    test_id: str
    name: str
    category: str
    description: str
    threat: str
    preconditions: tuple[str, ...]
    expected_changed_paths: tuple[str, ...]
    expected_i2map_behavior: str


@dataclass
class ScenarioContext:
    config: AppConfig
    device_state_provider: DeviceStateProvider
    integrity_provider: IntegrityProvider
    mode: TestMode = TestMode.NORMAL
    interactive: bool = False
    input_function: Any = input


class BaseSecurityTest(ABC):
    """Own precheck, evidence, mutation, comparison, and restoration ordering."""

    metadata: ScenarioMetadata

    def precheck(self, context: ScenarioContext) -> str | None:
        return None

    def capture_original_state(self, context: ScenarioContext) -> object:
        return None

    def validate_baseline(self, baseline: CollectedState, context: ScenarioContext) -> str | None:
        """Return a skip reason when collected prerequisites are unavailable."""

        return None

    def prepare_baseline(self, context: ScenarioContext) -> None:
        """Create only controlled resources required to establish a known baseline."""

        return None

    def tamper(self, context: ScenarioContext) -> str:
        raise NotImplementedError

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        raise NotImplementedError

    def restore(self, original: object, context: ScenarioContext) -> None:
        return None

    def verify_restoration(self, original: object, context: ScenarioContext) -> bool:
        return True

    def after_evaluate(
        self,
        result: SecurityTestResult,
        baseline: CollectedState,
        runtime: CollectedState,
        context: ScenarioContext,
    ) -> None:
        """Allow a scenario to add domain-specific detection labels or notes."""

        return None

    def run(self, context: ScenarioContext) -> SecurityTestResult:
        logger = logging.getLogger("cyberscope")
        logger.info("Starting %s", self.metadata.test_id)
        result = self._initial_result(context)
        evidence: EvidenceSession | None = None
        baseline: CollectedState | None = None
        runtime: CollectedState | None = None
        original: object = None
        mutation_started = False
        restoration_required = False
        try:
            evidence = EvidenceSession.create(context.config.evidence_dir, self.metadata.test_id)
            result.evidence.extend([str(evidence.root / "commands.log"), str(evidence.root / "run.log")])
            evidence.append_run("Capturing baseline state")
            blocked_reason = self.precheck(context)
            if not blocked_reason and context.mode not in {TestMode.DRY_RUN, TestMode.SIMULATION}:
                original = self.capture_original_state(context)
                restoration_required = True
                mutation_started = True
                self.prepare_baseline(context)
            baseline = context.device_state_provider.collect()
            blocked_reason = blocked_reason or self.validate_baseline(baseline, context)
            result.baseline_hash = context.integrity_provider.digest(baseline.monitored)
            result.original_values = baseline.monitored
            environment = baseline.monitored.get("environment", {})
            if isinstance(environment, dict):
                result.environment = str(environment.get("kind", "UNKNOWN"))
                result.operating_system = str(environment.get("system", platform.system()))
            evidence.write_json("baseline.json", {"state": baseline.to_dict(), "hash": result.baseline_hash})
            result.evidence.append(str(evidence.root / "baseline.json"))

            if blocked_reason:
                result.status = ResultStatus.SKIPPED
                result.detection_result = "NOT_TESTED"
                result.notes.append(blocked_reason)
            elif context.mode is TestMode.DRY_RUN:
                result.status = ResultStatus.SKIPPED
                result.detection_result = "DRY_RUN"
                result.tampering_action = "No mutation performed"
                result.notes.append("Dry-run mode: intended action recorded without changing state")
                evidence.append_run("Dry-run completed without mutation")
            elif context.mode is TestMode.SIMULATION:
                result.tampering_action = "Simulated state transition; no physical attack occurred"
                runtime = self.simulate_runtime(baseline, context)
                evidence.append_run("Simulated runtime state collected; no physical attack occurred")
                self._evaluate(result, baseline, runtime, context, tampering_occurred=True)
            else:
                result.tampering_action = self.tamper(context)
                evidence.append_run(result.tampering_action)
                runtime = context.device_state_provider.collect()
                self._evaluate(result, baseline, runtime, context, tampering_occurred=True)
        except Exception as exc:  # lifecycle must convert failures into reportable evidence
            logger.error("%s failed: %s", self.metadata.test_id, exc)
            result.errors.append(f"{type(exc).__name__}: {exc}")
            result.status = ResultStatus.ERROR
            result.detection_result = "ERROR"
        finally:
            if mutation_started:
                try:
                    self.restore(original, context)
                    if self.verify_restoration(original, context):
                        result.restoration_status = RestorationStatus.SUCCESS
                        if evidence is not None:
                            evidence.append_run("Restoration verified")
                    else:
                        raise RuntimeError("restoration verification failed")
                except Exception as exc:
                    logger.error("%s restoration failed: %s", self.metadata.test_id, exc)
                    result.restoration_status = RestorationStatus.FAILED
                    result.errors.append(f"Restoration error: {exc}")
                    result.status = ResultStatus.ERROR
            elif not restoration_required:
                result.restoration_status = RestorationStatus.NOT_REQUIRED

            result.finished_at = datetime.now().astimezone().isoformat(timespec="seconds")
            if evidence is not None:
                evidence.append_run(f"Finished with status {result.status.value}")
            if evidence is not None:
                self._finish_evidence(evidence, baseline, runtime, result, context)
            logger.info("%s result: %s", self.metadata.test_id, result.status.value)
        return result

    def _evaluate(
        self,
        result: SecurityTestResult,
        baseline: CollectedState,
        runtime: CollectedState,
        context: ScenarioContext,
        tampering_occurred: bool,
    ) -> None:
        result.runtime_hash = context.integrity_provider.digest(runtime.monitored)
        result.integrity_match = result.baseline_hash == result.runtime_hash
        result.actual_changes = diff_values(baseline.monitored, runtime.monitored)
        changed = {item.path for item in result.actual_changes}
        expected = set(self.metadata.expected_changed_paths)
        expected_seen = all(any(path == wanted or path.startswith(f"{wanted}.") for path in changed) for wanted in expected)
        if tampering_occurred and result.integrity_match:
            result.status = ResultStatus.FAIL
            result.detection_result = "FALSE_NEGATIVE"
        elif tampering_occurred and expected_seen and not result.integrity_match:
            result.status = ResultStatus.PASS
            result.detection_result = "TRUE_POSITIVE"
        elif tampering_occurred:
            result.status = ResultStatus.FAIL
            result.detection_result = "UNEXPECTED_CHANGE"
        elif result.integrity_match:
            result.status = ResultStatus.PASS
            result.detection_result = "TRUE_NEGATIVE"
        else:
            result.status = ResultStatus.FAIL
            result.detection_result = "FALSE_POSITIVE"
        self.after_evaluate(result, baseline, runtime, context)

    def _finish_evidence(
        self,
        evidence: EvidenceSession,
        baseline: CollectedState | None,
        runtime: CollectedState | None,
        result: SecurityTestResult,
        context: ScenarioContext,
    ) -> None:
        try:
            if runtime is not None:
                evidence.write_json("runtime.json", {"state": runtime.to_dict(), "hash": result.runtime_hash})
                result.evidence.append(str(evidence.root / "runtime.json"))
            evidence.write_json("diff.json", [item.to_dict() for item in result.actual_changes])
            result.evidence.append(str(evidence.root / "diff.json"))
            evidence.write_json("result.json", result.to_dict())
            result.evidence.append(str(evidence.root / "result.json"))
            report_paths = ReportWriter(context.config.reports_dir).write(result.to_dict())
            result.evidence.extend(str(path) for path in report_paths)
            evidence.write_json("result.json", result.to_dict())
        except Exception as exc:
            result.errors.append(f"Evidence error: {exc}")
            result.status = ResultStatus.ERROR

    def _initial_result(self, context: ScenarioContext) -> SecurityTestResult:
        return SecurityTestResult(
            test_id=self.metadata.test_id,
            test_name=self.metadata.name,
            category=self.metadata.category,
            description=self.metadata.description,
            threat=self.metadata.threat,
            preconditions=list(self.metadata.preconditions),
            expected_changed_parameters=list(self.metadata.expected_changed_paths),
            expected_i2map_behavior=self.metadata.expected_i2map_behavior,
            environment_mode=context.mode.value,
            device=socket.gethostname(),
            operating_system=platform.system(),
        )
