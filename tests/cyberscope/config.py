"""Project paths and bounded defaults."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    output_dir: Path
    test_resources_dir: Path
    command_timeout_seconds: float = 10.0
    max_command_output_bytes: int = 65_536
    max_stability_iterations: int = 10_000

    @classmethod
    def default(cls) -> "AppConfig":
        root = Path(__file__).resolve().parent.parent
        return cls(root, root / "output", root / ".cyberscope-test-resources")

    @property
    def baselines_dir(self) -> Path:
        return self.output_dir / "baselines"

    @property
    def evidence_dir(self) -> Path:
        return self.output_dir / "evidence"

    @property
    def logs_dir(self) -> Path:
        return self.output_dir / "logs"

    @property
    def reports_dir(self) -> Path:
        return self.output_dir / "reports"
