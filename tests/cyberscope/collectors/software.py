"""Software and controlled monitored-file collection."""

from __future__ import annotations

import importlib.metadata
import os
import platform
from pathlib import Path

from cyberscope.utils.commands import CommandRunner
from cyberscope.utils.files import file_state


def parse_os_release(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"').strip("'")
    return values


def collect_monitored_files(paths: list[Path] | tuple[Path, ...]) -> list[dict[str, object]]:
    return [{"path": str(path), **file_state(path)} for path in sorted(paths, key=lambda item: str(item))]


def collect_software(paths: tuple[Path, ...] = (), include_packages: bool = True) -> dict[str, object]:
    try:
        os_release = parse_os_release(Path("/etc/os-release").read_text(encoding="utf-8"))
    except OSError:
        os_release = {}
    result: dict[str, object] = {
        "os_release": os_release,
        "kernel": platform.release(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "os_type": platform.system(),
        "python_packages": sorted(
            ({"name": item.metadata.get("Name", ""), "version": item.version} for item in importlib.metadata.distributions()),
            key=lambda item: (str(item["name"]).lower(), str(item["version"])),
        ) if include_packages else [],
        "installed_packages": _installed_packages() if include_packages else [],
        "monitored_files": collect_monitored_files(paths),
    }
    return result


def _installed_packages() -> list[str]:
    runner = CommandRunner(default_timeout=20)
    for argv in (["dpkg-query", "-W", "-f=${Package}=${Version}\\n"], ["rpm", "-qa"]):
        result = runner.run(argv)
        if result.returncode == 0:
            return sorted(line.strip() for line in result.stdout.splitlines() if line.strip())
    return []
