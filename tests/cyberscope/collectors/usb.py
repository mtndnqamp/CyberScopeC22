"""USB inventory from Linux sysfs with optional lsusb parsing."""

from __future__ import annotations

import re
from pathlib import Path

from cyberscope.models import Measurement
from cyberscope.utils.commands import CommandRunner


LSUSB_PATTERN = re.compile(r"^Bus \d+ Device \d+: ID ([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\s*(.*)$")


def parse_lsusb(text: str) -> list[dict[str, object]]:
    devices = []
    for line in text.splitlines():
        match = LSUSB_PATTERN.match(line.strip())
        if match:
            devices.append({"vendor_id": match.group(1).lower(), "product_id": match.group(2).lower(), "description": match.group(3).strip()})
    return sorted(devices, key=lambda item: (str(item["vendor_id"]), str(item["product_id"]), str(item["description"])))


def collect_usb_sysfs(root: Path = Path("/sys/bus/usb/devices")) -> list[dict[str, object]]:
    if not root.is_dir():
        return []
    devices = []
    for candidate in root.iterdir():
        vendor = _field(candidate / "idVendor")
        product_id = _field(candidate / "idProduct")
        if not vendor or not product_id:
            continue
        devices.append({
            "vendor_id": vendor.lower(),
            "product_id": product_id.lower(),
            "manufacturer": _field(candidate / "manufacturer"),
            "product": _field(candidate / "product"),
            "serial": _field(candidate / "serial"),
        })
    return sorted(devices, key=lambda item: tuple(str(item[key] or "") for key in ("vendor_id", "product_id", "serial", "manufacturer", "product")))


def collect_usb() -> dict[str, object]:
    sysfs = collect_usb_sysfs()
    if sysfs:
        return {"devices": Measurement.supported_value(sysfs).to_dict(), "source": "sysfs"}
    result = CommandRunner().run(["lsusb"])
    if result.returncode == 0:
        return {"devices": Measurement.supported_value(parse_lsusb(result.stdout)).to_dict(), "source": "lsusb"}
    return {"devices": Measurement.unsupported("USB inventory unavailable in this environment").to_dict(), "source": "unavailable"}


def _field(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip() or None
    except OSError:
        return None
