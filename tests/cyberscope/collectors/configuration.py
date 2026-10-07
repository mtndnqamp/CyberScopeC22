"""Stable device and controlled configuration metadata."""

from __future__ import annotations

import os
import getpass
try:
    import grp
    import pwd
except ImportError:
    grp = pwd = None
import socket
from pathlib import Path

from cyberscope.models import Measurement
from cyberscope.utils.files import file_state


def collect_configuration(paths: tuple[Path, ...] = ()) -> dict[str, object]:
    uid = os.geteuid() if hasattr(os, "geteuid") else None
    gid = os.getegid() if hasattr(os, "getegid") else None
    try:
        user = pwd.getpwuid(uid).pw_name if pwd is not None else getpass.getuser()
    except KeyError:
        user = str(uid)
    try:
        group = grp.getgrgid(gid).gr_name if grp is not None else None
    except KeyError:
        group = str(gid)
    interfaces = sorted(path.name for pattern in ("/dev/spidev*", "/dev/i2c-*") for path in Path("/").glob(pattern.lstrip("/")))
    return {
        "hostname": Measurement.supported_value(socket.gethostname()).to_dict(),
        "effective_user": Measurement.supported_value({"uid": uid, "name": user}).to_dict(),
        "effective_group": (Measurement.supported_value({"gid": gid, "name": group}) if gid is not None else Measurement.unsupported("POSIX group metadata unavailable")).to_dict(),
        "monitored_files": [{"path": str(path), **file_state(path)} for path in sorted(paths, key=str)],
        "enabled_interfaces": Measurement.supported_value(interfaces).to_dict() if interfaces else Measurement.unsupported("SPI/I2C interfaces unavailable").to_dict(),
    }
