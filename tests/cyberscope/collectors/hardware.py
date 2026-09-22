"""Hardware collection with explicit unsupported values."""

from __future__ import annotations

import os
import platform
import time
from pathlib import Path

from cyberscope.collectors.common import read_optional_text
from cyberscope.models import Measurement


def collect_hardware() -> tuple[dict[str, object], dict[str, object]]:
    cpuinfo = read_optional_text(Path("/proc/cpuinfo"), "CPU information unavailable")
    stable_cpu = stable_cpu_information(str(cpuinfo.value or ""))
    serial_values = stable_cpu.get("serial", [])
    serial = serial_values[0] if serial_values else ""
    memory = _memory_total()
    monitored = {
        "cpu_architecture": Measurement.supported_value(platform.machine()).to_dict(),
        "cpu_information": (Measurement.supported_value(stable_cpu) if stable_cpu else Measurement.unsupported("Stable CPU identity unavailable")).to_dict(),
        "hardware_serial": (Measurement.supported_value(serial) if serial else Measurement.unsupported("Hardware serial unavailable in this environment")).to_dict(),
        "memory_total_kib": memory.to_dict(),
        "device_model": read_optional_text(Path("/proc/device-tree/model"), "Device-tree model unavailable in this environment").to_dict(),
    }
    diagnostic = {
        "cpu_frequency": read_optional_text(Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"), "CPU frequency unavailable").to_dict(),
        "cpu_utilisation_percent": _cpu_utilisation().to_dict(),
        "voltage": Measurement.unsupported("Voltage unavailable or unsupported").to_dict(),
        "jtag_status": Measurement.unsupported("JTAG status cannot be safely determined").to_dict(),
    }
    return monitored, diagnostic


def stable_cpu_information(text: str) -> dict[str, list[str]]:
    """Extract stable CPU identity fields and exclude per-sample runtime values."""

    allowed = {"vendor_id", "model name", "cpu implementer", "cpu part", "hardware", "revision", "serial"}
    values: dict[str, set[str]] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        normalised_key = key.lower()
        if normalised_key in allowed and value:
            values.setdefault(normalised_key, set()).add(value)
    return {key: sorted(entries) for key, entries in sorted(values.items())}


def cpu_utilisation_between(before: str, after: str) -> float:
    """Calculate aggregate busy percentage from two Linux /proc/stat samples."""

    before_values = _cpu_stat_values(before)
    after_values = _cpu_stat_values(after)
    total_delta = sum(after_values) - sum(before_values)
    idle_delta = sum(after_values[3:5]) - sum(before_values[3:5])
    if total_delta <= 0:
        raise ValueError("CPU sample has no positive elapsed ticks")
    return round((total_delta - idle_delta) * 100.0 / total_delta, 2)


def _cpu_stat_values(text: str) -> list[int]:
    first = text.splitlines()[0].split()
    if not first or first[0] != "cpu" or len(first) < 5:
        raise ValueError("invalid /proc/stat CPU sample")
    return [int(value) for value in first[1:]]


def _cpu_utilisation() -> Measurement:
    try:
        before = Path("/proc/stat").read_text(encoding="utf-8", errors="replace")
        time.sleep(0.02)
        after = Path("/proc/stat").read_text(encoding="utf-8", errors="replace")
        return Measurement.supported_value(cpu_utilisation_between(before, after))
    except (OSError, ValueError, IndexError):
        return Measurement.unsupported("CPU utilisation unavailable; excluded from integrity hash")


def _memory_total() -> Measurement:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return Measurement.supported_value((pages * page_size) // 1024)
    except (ValueError, OSError):
        return Measurement.unsupported("Memory size unavailable")
