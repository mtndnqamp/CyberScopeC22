#!/usr/bin/env python3
"""Run labelled simulations through the framework AND production comparison.
No host mutation or Discord delivery. --backend blockchain also checks HashReg.
"""
import argparse
import copy
import json
import tempfile
import uuid
from pathlib import Path

from cyberscope.config import AppConfig
from cyberscope.integrity.team import TeamDeviceStateProvider, TeamIntegrityProvider
from cyberscope.models import CollectedState, TestMode, ResultStatus
from cyberscope.scenarios.base import BaseSecurityTest, ScenarioContext, ScenarioMetadata
import integrity_check

SAMPLE = {"hostname":"demo-pi", "pip_packages":["original==1"],
          "usb_devices":["demo-usb"], "network_interfaces":{"interfaces":{"demo":{"ip_address":"192.0.2.1"}}},
          "cpu_usage":"Standard"}
CASES = [("TEAM-001", "pip_packages", ["original==1", "added==2"]),
         ("TEAM-002", "usb_devices", ["demo-usb", "added-usb"]),
         ("TEAM-003", "hostname", "changed-host"),
         ("TEAM-004", "network_interfaces", {"interfaces":{"demo":{"ip_address":"192.0.2.2"}}})]

class TeamScenario(BaseSecurityTest):
    def __init__(self, test_id, parameter, replacement, backend="local"):
        self.parameter, self.replacement, self.backend = parameter, replacement, backend
        self.metadata = ScenarioMetadata(test_id, "Team integration: " + parameter,
            "integration", "Synthetic parameter change using the production hash/comparison",
            "Unexpected monitored state change", ("Sample data only",), (parameter,),
            "Changed hash and flagged production comparison")
    def simulate_runtime(self, baseline, context):
        state = copy.deepcopy(baseline.monitored)
        state[self.parameter] = copy.deepcopy(self.replacement)
        return CollectedState(state, baseline.diagnostic)
    def after_evaluate(self, result, baseline, runtime, context):
        # Use a unique record so tests cannot replace the actual device baseline.
        device_id = "security-sample-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as directory:
            baseline_path=Path(directory)/"baseline.json"
            sample_path=Path(directory)/"sample.json"
            client=None
            if self.backend == "blockchain":
                from Edge_Node.app_connect import BlockchainClient
                client=BlockchainClient()
            team_map=integrity_check.build_integrity_map(list(baseline.monitored.items()))
            integrity_check.save_baseline(team_map, device_id, baseline_path,
                backend=self.backend, client=client, sample=True)
            sample_path.write_text(json.dumps(baseline.monitored), encoding="utf-8")
            clean, _ = integrity_check.check(alert_on_mismatch=False,device_id=device_id,
                baseline_file=baseline_path,backend=self.backend,client=client,params_file=sample_path)
            sample_path.write_text(json.dumps(runtime.monitored), encoding="utf-8")
            changed, details=integrity_check.check(alert_on_mismatch=False,device_id=device_id,
                baseline_file=baseline_path,backend=self.backend,client=client,params_file=sample_path)
            if clean != "verified" or changed != "flagged" or self.parameter not in details.get("changed",[]):
                result.status=ResultStatus.FAIL
                result.detection_result="PRODUCTION_COMPARISON_FAILED"
            result.notes.extend(["Production backend: " + self.backend,
                "Production clean verdict: " + clean, "Production changed verdict: " + changed,
                "Sample simulation only; no real host tampering and no Discord messages"])

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend",choices=["local","blockchain"],default="local")
    parser.add_argument("--output",type=Path,default=Path(__file__).parent/"output"/"team")
    args=parser.parse_args(argv)
    root=Path(__file__).resolve().parent
    config=AppConfig(root,args.output,root/".cyberscope-test-resources")
    context=ScenarioContext(config,TeamDeviceStateProvider(SAMPLE),TeamIntegrityProvider(),TestMode.SIMULATION)
    results=[TeamScenario(*case,backend=args.backend).run(context) for case in CASES]
    for result in results:
        print(result.test_id + ": " + result.status.value + " (simulation, " + args.backend + ")")
        for error in result.errors:
            print("Error: " + error)
    print("Reports/evidence: " + str(args.output.resolve()))
    return 0 if all(result.status == ResultStatus.PASS for result in results) else 1

if __name__ == "__main__":
    raise SystemExit(main())
