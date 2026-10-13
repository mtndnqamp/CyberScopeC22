"""Shared reversible behavior for framework-confined file scenarios."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from cyberscope.models import CollectedState
from cyberscope.scenarios.base import BaseSecurityTest, ScenarioContext
from cyberscope.utils.files import atomic_write_text, confined_path, file_state


@dataclass(frozen=True)
class FileSnapshot:
    existed: bool
    content: bytes
    mode: int | None


class ControlledFileScenario(BaseSecurityTest):
    baseline_content = "enabled=true\n"
    modified_content = "enabled=false\n"
    baseline_mode = 0o644
    state_category = "software"

    def __init__(self, target: Path) -> None:
        self.target = target

    def precheck(self, context: ScenarioContext) -> str | None:
        try:
            confined_path(context.config.test_resources_dir, self.target)
        except ValueError as exc:
            return str(exc)
        return None

    def capture_original_state(self, context: ScenarioContext) -> FileSnapshot:
        if not self.target.exists():
            return FileSnapshot(False, b"", None)
        return FileSnapshot(True, self.target.read_bytes(), self.target.stat().st_mode & 0o7777)

    def prepare_baseline(self, context: ScenarioContext) -> None:
        atomic_write_text(self.target, self.baseline_content)
        self.target.chmod(self.baseline_mode)

    def tamper(self, context: ScenarioContext) -> str:
        atomic_write_text(self.target, self.modified_content)
        self.target.chmod(self.baseline_mode)
        return f"Changed controlled file {self.target.name}"

    def simulate_runtime(self, baseline: CollectedState, context: ScenarioContext) -> CollectedState:
        runtime = deepcopy(baseline)
        rows = runtime.monitored[self.state_category]["monitored_files"]  # type: ignore[index]
        if isinstance(rows, list) and rows:
            rows[0] = {**rows[0], "sha256": "simulated-modified-sha256"}
        else:
            runtime.monitored[self.state_category]["monitored_files"] = [{"path": str(self.target), "exists": True, "sha256": "simulated-modified-sha256"}]  # type: ignore[index]
        return runtime

    def restore(self, original: object, context: ScenarioContext) -> None:
        snapshot = _snapshot(original)
        if snapshot.existed:
            self.target.parent.mkdir(parents=True, exist_ok=True)
            self.target.write_bytes(snapshot.content)
            if snapshot.mode is not None:
                self.target.chmod(snapshot.mode)
        elif self.target.exists():
            self.target.unlink()

    def verify_restoration(self, original: object, context: ScenarioContext) -> bool:
        snapshot = _snapshot(original)
        if not snapshot.existed:
            return not self.target.exists()
        current = file_state(self.target)
        return self.target.read_bytes() == snapshot.content and current["mode"] == f"{snapshot.mode:04o}"


def _snapshot(value: object) -> FileSnapshot:
    if not isinstance(value, FileSnapshot):
        raise TypeError("invalid controlled-file snapshot")
    return value
