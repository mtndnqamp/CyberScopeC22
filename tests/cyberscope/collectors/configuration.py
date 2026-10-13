"""Stable device and controlled configuration metadata."""

from __future__ import annotations

import grp
import os
import pwd
import socket
from pathlib import Path

from cyberscope.models import Measurement
from cyberscope.utils.files import file_state


def collect_configuration(paths: tuple[Path, ...] = ()) -> dict[str, object]:
    uid = os.geteuid()
    gid = os.getegid()
    try:
        user = pwd.getpwuid(uid).pw_name
    except KeyError:
        user = str(uid)
    try:
        group = grp.getgrgid(gid).gr_name
    except KeyError:
        group = str(gid)
    interfaces = sorted(path.name for pattern in ("/dev/spidev*", "/dev/i2c-*") for path in Path("/").glob(pattern.lstrip("/")))
    return {
        "hostname": Measurement.supported_value(socket.gethostname()).to_dict(),
        "effective_user": Measurement.supported_value({"uid": uid, "name": user}).to_dict(),
        "effective_group": Measurement.supported_value({"gid": gid, "name": group}).to_dict(),
        "monitored_files": [{"path": str(path), **file_state(path)} for path in sorted(paths, key=str)],
        "enabled_interfaces": Measurement.supported_value(interfaces).to_dict() if interfaces else Measurement.unsupported("SPI/I2C interfaces unavailable").to_dict(),
    }
