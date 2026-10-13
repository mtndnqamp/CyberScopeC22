"""Network and device-configuration collection."""

from __future__ import annotations

import json
import socket
from pathlib import Path

from cyberscope.models import Measurement
from cyberscope.utils.commands import CommandRunner


def collect_network() -> dict[str, object]:
    runner = CommandRunner()
    address_result = runner.run(["ip", "-j", "address", "show"])
    route_result = runner.run(["ip", "-j", "route", "show", "default"])
    interfaces = _json_or_empty(address_result.stdout) if address_result.returncode == 0 else []
    routes = _json_or_empty(route_result.stdout) if route_result.returncode == 0 else []
    return {
        "hostname": Measurement.supported_value(socket.gethostname()).to_dict(),
        "interfaces": Measurement.supported_value(_normalise_interfaces(interfaces)).to_dict(),
        "default_routes": Measurement.supported_value(routes).to_dict() if routes else Measurement.unsupported("Default route unavailable").to_dict(),
        "dns_servers": Measurement.supported_value(_dns_servers()).to_dict(),
        "wireless_ssid": _wireless_ssid(runner).to_dict(),
    }


def _json_or_empty(text: str) -> list[dict[str, object]]:
    try:
        value = json.loads(text)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def _normalise_interfaces(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    normalised = []
    for row in rows:
        addresses = []
        for info in row.get("addr_info", []) if isinstance(row.get("addr_info"), list) else []:
            if isinstance(info, dict):
                addresses.append({key: info.get(key) for key in ("family", "local", "prefixlen")})
        normalised.append({"name": row.get("ifname"), "address": row.get("address"), "addresses": sorted(addresses, key=lambda value: str(value))})
    return sorted(normalised, key=lambda value: str(value["name"]))


def _dns_servers() -> list[str]:
    try:
        lines = Path("/etc/resolv.conf").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return sorted({line.split()[1] for line in lines if line.strip().startswith("nameserver ") and len(line.split()) >= 2})


def _wireless_ssid(runner: CommandRunner) -> Measurement:
    result = runner.run(["iwgetid", "--raw"])
    if result.returncode == 0 and result.stdout.strip():
        return Measurement.supported_value(result.stdout.strip())
    return Measurement.unsupported("Wireless SSID unavailable")
