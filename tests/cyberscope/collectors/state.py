"""Composition of collectors into the versioned device-state schema."""

from __future__ import annotations

from pathlib import Path

from cyberscope.collectors.configuration import collect_configuration
from cyberscope.collectors.hardware import collect_hardware
from cyberscope.collectors.network import collect_network
from cyberscope.collectors.software import collect_software
from cyberscope.collectors.usb import collect_usb
from cyberscope.models import CollectedState
from cyberscope.utils.environment import detect_environment


class LinuxDeviceStateProvider:
    def __init__(
        self,
        monitored_paths: tuple[Path, ...] = (),
        include_package_inventory: bool = True,
        configuration_paths: tuple[Path, ...] = (),
    ) -> None:
        self.software_paths = monitored_paths
        self.configuration_paths = configuration_paths
        self.include_package_inventory = include_package_inventory

    def collect(self) -> CollectedState:
        environment = detect_environment().to_dict()
        hardware, diagnostic_hardware = collect_hardware()
        monitored = {
            "schema_version": 1,
            "environment": environment,
            "software": collect_software(self.software_paths, self.include_package_inventory),
            "hardware": hardware,
            "network": collect_network(),
            "configuration": collect_configuration(self.configuration_paths),
            "usb": collect_usb(),
        }
        return CollectedState(monitored=monitored, diagnostic={"hardware": diagnostic_hardware})
