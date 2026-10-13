"""Stable discovery and construction of all named security tests."""

from __future__ import annotations

from collections.abc import Iterable

from cyberscope.config import AppConfig
from cyberscope.scenarios.base import BaseSecurityTest
from cyberscope.scenarios.configuration import (
    ConfigurationFileModification,
    ConfigurationPermissionChange,
    DeviceHostnameChange,
    EnabledInterfaceChange,
    FileOwnershipChange,
)
from cyberscope.scenarios.network import (
    DnsConfigurationChange,
    HostnameChange,
    MacAddressChange,
    NetworkInterfaceChange,
    WirelessSsidChange,
)
from cyberscope.scenarios.software import (
    ApplicationConfigModification,
    IsolatedPackageAddition,
    SourceFileModification,
    UnauthorizedExecutable,
)
from cyberscope.scenarios.usb import UsbConnection, UsbRemoval


class ScenarioRegistry:
    def __init__(self, scenarios: Iterable[BaseSecurityTest]) -> None:
        self._scenarios = {item.metadata.test_id: item for item in scenarios}

    def ids(self) -> list[str]:
        return sorted(self._scenarios)

    def list(self) -> list[BaseSecurityTest]:
        return [self._scenarios[item] for item in self.ids()]

    def get(self, test_id: str) -> BaseSecurityTest:
        try:
            return self._scenarios[test_id.upper()]
        except KeyError as exc:
            raise KeyError(f"unknown test ID {test_id}; available: {', '.join(self.ids())}") from exc

    def category(self, category: str) -> list[BaseSecurityTest]:
        return [item for item in self.list() if item.metadata.category == category]


def build_registry(config: AppConfig) -> ScenarioRegistry:
    root = config.test_resources_dir
    return ScenarioRegistry([
        ApplicationConfigModification(root / "application.conf"),
        IsolatedPackageAddition(root / "isolated_package.json"),
        SourceFileModification(root / "sensor_app.py"),
        UnauthorizedExecutable(root / "unauthorized_tool.py"),
        HostnameChange(),
        DnsConfigurationChange(),
        NetworkInterfaceChange(),
        WirelessSsidChange(),
        MacAddressChange(),
        UsbConnection(),
        UsbRemoval(),
        ConfigurationFileModification(root / "test_config.conf"),
        ConfigurationPermissionChange(root / "permission_config.conf"),
        FileOwnershipChange(root / "ownership_config.conf"),
        DeviceHostnameChange(root / "hostname_fixture.conf"),
        EnabledInterfaceChange(root / "interfaces_fixture.conf"),
    ])
