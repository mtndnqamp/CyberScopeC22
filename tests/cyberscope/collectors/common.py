"""Collector measurement helpers."""

from pathlib import Path

from cyberscope.models import Measurement


def read_optional_text(path: Path, unavailable_reason: str) -> Measurement:
    try:
        return Measurement.supported_value(path.read_text(encoding="utf-8", errors="replace").strip("\x00\n"))
    except OSError:
        return Measurement.unsupported(unavailable_reason)
