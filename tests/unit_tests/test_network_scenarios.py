import tempfile
import unittest
from pathlib import Path

from cyberscope.config import AppConfig
from cyberscope.integrity.providers import CanonicalIntegrityProvider
from cyberscope.models import CollectedState, ResultStatus, TestMode
from cyberscope.scenarios.base import ScenarioContext
from cyberscope.scenarios.network import HostnameChange, MacAddressChange, NetworkInterfaceChange


class StaticProvider:
    def __init__(self, state: CollectedState) -> None:
        self.state = state

    def collect(self) -> CollectedState:
        return self.state


def network_state() -> CollectedState:
    return CollectedState({
        "network": {
            "hostname": {"supported": True, "value": "raspberrypi", "reason": None},
            "interfaces": {"supported": True, "value": [{"name": "eth0", "address": "00:11:22:33:44:55", "addresses": [{"family": "inet", "local": "10.0.0.2", "prefixlen": 24}]}], "reason": None},
            "default_routes": {"supported": True, "value": [{"gateway": "10.0.0.1"}], "reason": None},
            "dns_servers": {"supported": True, "value": ["1.1.1.1"], "reason": None},
            "wireless_ssid": {"supported": True, "value": "LabWiFi", "reason": None},
        },
        "configuration": {"hostname": {"supported": True, "value": "raspberrypi", "reason": None}},
    })


class NetworkScenarioTests(unittest.TestCase):
    def run_scenario(self, scenario: object, mode: TestMode = TestMode.SIMULATION):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context = ScenarioContext(AppConfig(root, root / "output", root / "resources"), StaticProvider(network_state()), CanonicalIntegrityProvider(), mode)
            return scenario.run(context)  # type: ignore[attr-defined]

    def test_net001_simulation_changes_hostname(self) -> None:
        result = self.run_scenario(HostnameChange())
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(result.environment_mode, "simulation")
        self.assertIn("network.hostname.value", [item.path for item in result.actual_changes])

    def test_net003_simulation_changes_interface_and_route(self) -> None:
        result = self.run_scenario(NetworkInterfaceChange())
        paths = [item.path for item in result.actual_changes]
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertIn("network.interfaces.value", paths)
        self.assertIn("network.default_routes.value", paths)

    def test_net005_normal_mode_skips_instead_of_spoofing_mac(self) -> None:
        result = self.run_scenario(MacAddressChange(), TestMode.NORMAL)
        self.assertEqual(result.status, ResultStatus.SKIPPED)
        self.assertIn("spoof", " ".join(result.notes).lower())


if __name__ == "__main__":
    unittest.main()
