"""Portable Raspberry Pi, VM, and Linux environment detection."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path

from cyberscope.utils.commands import CommandRunner


@dataclass(frozen=True)
class EnvironmentInfo:
    kind: str
    system: str
    architecture: str
    model: str
    virtualisation: str

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "system": self.system,
            "architecture": self.architecture,
            "model": self.model,
            "virtualisation": self.virtualisation,
        }


def detect_environment(
    model_text: str | None = None,
    cpuinfo_text: str | None = None,
    system: str | None = None,
    machine: str | None = None,
    virtualisation: str | None = None,
) -> EnvironmentInfo:
    model = _read_text(Path("/proc/device-tree/model")) if model_text is None else model_text
    cpuinfo = _read_text(Path("/proc/cpuinfo")) if cpuinfo_text is None else cpuinfo_text
    system_value = platform.system() if system is None else system
    machine_value = platform.machine() if machine is None else machine
    if virtualisation is None:
        result = CommandRunner().run(["systemd-detect-virt"])
        virtualisation = result.stdout.strip() if result.returncode == 0 else "none"
    pi_evidence = f"{model}\n{cpuinfo}".lower()
    if "raspberry pi" in pi_evidence or "bcm270" in pi_evidence or "bcm271" in pi_evidence:
        kind = "RASPBERRY_PI"
    elif system_value == "Linux" and virtualisation not in {"", "none"}:
        kind = "LINUX_VM"
    elif system_value == "Linux":
        kind = "GENERIC_LINUX"
    else:
        kind = "UNKNOWN"
    return EnvironmentInfo(kind, system_value, machine_value, model.strip(), virtualisation or "none")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip("\x00\n")
    except OSError:
        return ""
