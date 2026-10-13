"""Shared typed models used throughout CyberScope."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True)
class Measurement:
    """A collected value together with availability information."""

    supported: bool
    value: JsonValue
    reason: str | None = None

    @classmethod
    def supported_value(cls, value: JsonValue) -> "Measurement":
        return cls(supported=True, value=value)

    @classmethod
    def unsupported(cls, reason: str) -> "Measurement":
        if not reason.strip():
            raise ValueError("unsupported measurement requires a reason")
        return cls(supported=False, value=None, reason=reason)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"supported": self.supported, "value": self.value, "reason": self.reason}


@dataclass(frozen=True)
class Difference:
    """One path-aware difference between baseline and runtime state."""

    path: str
    kind: str
    before: JsonValue
    after: JsonValue

    def to_dict(self) -> dict[str, JsonValue]:
        return asdict(self)


@dataclass
class CollectedState:
    """Stable monitored values and non-hashed diagnostic observations."""

    monitored: dict[str, JsonValue]
    diagnostic: dict[str, JsonValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"monitored": self.monitored, "diagnostic": self.diagnostic}


class TestMode(StrEnum):
    NORMAL = "normal"
    SIMULATION = "simulation"
    DRY_RUN = "dry-run"
    REAL_TEST = "real-test"


class ResultStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class RestorationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NOT_REQUIRED = "NOT REQUIRED"


@dataclass
class SecurityTestResult:
    """Complete result and evidence index for one scenario execution."""

    test_id: str
    test_name: str
    category: str
    description: str
    threat: str
    preconditions: list[str]
    expected_changed_parameters: list[str]
    expected_i2map_behavior: str
    environment_mode: str
    started_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat(timespec="seconds"))
    finished_at: str = ""
    original_values: dict[str, JsonValue] = field(default_factory=dict)
    tampering_action: str = ""
    actual_changes: list[Difference] = field(default_factory=list)
    baseline_hash: str = ""
    runtime_hash: str = ""
    integrity_match: bool | None = None
    detection_result: str = "NOT_EVALUATED"
    status: ResultStatus = ResultStatus.ERROR
    errors: list[str] = field(default_factory=list)
    restoration_status: RestorationStatus = RestorationStatus.NOT_REQUIRED
    evidence: list[str] = field(default_factory=list)
    environment: str = "UNKNOWN"
    device: str = ""
    operating_system: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def timestamp(self) -> str:
        return self.started_at

    @property
    def changed_parameters(self) -> list[Difference]:
        return self.actual_changes

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "category": self.category,
            "description": self.description,
            "threat": self.threat,
            "preconditions": self.preconditions,
            "original_values": self.original_values,
            "tampering_action": self.tampering_action,
            "expected_changed_parameters": self.expected_changed_parameters,
            "expected_result": self.expected_i2map_behavior,
            "actual_changed_parameters": [item.path for item in self.actual_changes],
            "changed_parameters": [item.to_dict() for item in self.actual_changes],
            "baseline_hash": self.baseline_hash,
            "runtime_hash": self.runtime_hash,
            "integrity_match": self.integrity_match,
            "detection_result": self.detection_result,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "errors": self.errors,
            "restoration_status": self.restoration_status.value,
            "evidence": self.evidence,
            "environment_mode": self.environment_mode,
            "environment": self.environment,
            "device": self.device,
            "operating_system": self.operating_system,
            "notes": self.notes,
        }
