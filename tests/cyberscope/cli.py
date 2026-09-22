"""Command-line interface for baselines, security tests, and reports."""

from __future__ import annotations

import argparse
import json
import platform
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

from cyberscope.collectors.state import LinuxDeviceStateProvider
from cyberscope.config import AppConfig
from cyberscope.integrity.baseline import BaselineRepository, BaselineValidationError
from cyberscope.integrity.comparison import diff_values
from cyberscope.integrity.providers import CanonicalIntegrityProvider
from cyberscope.models import ResultStatus, TestMode
from cyberscope.reporting.evidence import EvidenceSession
from cyberscope.reporting.log import configure_logger
from cyberscope.reporting.report import ReportWriter
from cyberscope.scenarios.base import BaseSecurityTest, ScenarioContext
from cyberscope.scenarios.registry import ScenarioRegistry, build_registry
from cyberscope.scenarios.stability import run_stability
from cyberscope.utils.environment import detect_environment


CATEGORIES = ("software", "network", "usb", "configuration")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CyberScope IoT integrity security testing")
    parser.add_argument("--debug", action="store_true", help="show detailed diagnostics")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("system-info", help="collect platform and environment information")

    baseline = commands.add_parser("baseline", help="manage trusted device baselines")
    baseline_commands = baseline.add_subparsers(dest="baseline_command", required=True)
    baseline_commands.add_parser("create", help="collect and store a trusted baseline")
    baseline_show = baseline_commands.add_parser("show", help="display a baseline")
    baseline_show.add_argument("name", nargs="?", default="latest.json")
    baseline_compare = baseline_commands.add_parser("compare", help="compare current state with a baseline")
    baseline_compare.add_argument("name", nargs="?", default="latest.json")

    test = commands.add_parser("test", help="discover and execute security tests")
    test_commands = test.add_subparsers(dest="test_command", required=True)
    test_commands.add_parser("list", help="list available security tests")
    for category in CATEGORIES:
        category_parser = test_commands.add_parser(category, help=f"run {category} tests")
        _add_mode_arguments(category_parser, interactive=category == "usb")
    run = test_commands.add_parser("run", help="run one security test")
    run.add_argument("test_id")
    _add_mode_arguments(run, interactive=True)
    all_tests = test_commands.add_parser("all", help="run all registered tests")
    _add_mode_arguments(all_tests)
    stability = test_commands.add_parser("stability", help="measure unchanged-state false positives")
    stability.add_argument("--iterations", type=_positive_iterations, default=100)

    report = commands.add_parser("report", help="browse generated reports")
    report_commands = report.add_subparsers(dest="report_command", required=True)
    report_commands.add_parser("list", help="list JSON reports")
    report_show = report_commands.add_parser("show", help="show latest matching report")
    report_show.add_argument("query")
    return parser


def _add_mode_arguments(parser: argparse.ArgumentParser, interactive: bool = False) -> None:
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--simulation", "--simulate", dest="simulation", action="store_true", help="simulate labelled before/after state")
    modes.add_argument("--dry-run", action="store_true", help="record intent without mutation")
    modes.add_argument("--real-test", action="store_true", help="explicitly enable a supported real host test")
    if interactive:
        parser.add_argument("--interactive", action="store_true", help="pause for an operator-controlled physical step")


def _positive_iterations(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= 10_000:
        raise argparse.ArgumentTypeError("iterations must be between 1 and 10000")
    return parsed


def _normalise_shorthand(argv: list[str]) -> list[str]:
    known = {"list", "run", "all", "stability", *CATEGORIES}
    if len(argv) >= 2 and argv[0] == "test" and argv[1] not in known:
        return ["test", "run", *argv[1:]]
    return argv


def main(argv: Sequence[str] | None = None, *, config: AppConfig | None = None) -> int:
    arguments = _normalise_shorthand(list(sys.argv[1:] if argv is None else argv))
    args = build_parser().parse_args(arguments)
    app_config = config or AppConfig.default()
    log_path = app_config.logs_dir / f"cyberscope_{datetime.now().astimezone():%Y%m%d_%H%M%S}.log"
    logger = configure_logger(log_path, debug=args.debug)
    logger.info("Starting command: %s", " ".join(arguments))
    integrity = CanonicalIntegrityProvider()
    registry = build_registry(app_config)
    try:
        if args.command == "system-info":
            print(json.dumps(detect_environment().to_dict(), indent=2, sort_keys=True))
            return 0
        if args.command == "baseline":
            return _baseline_command(args, app_config, integrity)
        if args.command == "test":
            return _test_command(args, app_config, integrity, registry)
        if args.command == "report":
            return _report_command(args, app_config)
    except (BaselineValidationError, KeyError, ValueError, OSError) as exc:
        logger.error("Command failed: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 1


def _baseline_command(args: argparse.Namespace, config: AppConfig, integrity: CanonicalIntegrityProvider) -> int:
    repository = BaselineRepository(config.baselines_dir)
    if args.baseline_command == "create":
        state = LinuxDeviceStateProvider().collect()
        environment = state.monitored.get("environment", {})
        record = repository.create(state, integrity, environment if isinstance(environment, dict) else {})
        print(f"Baseline: {record.path}")
        print(f"I2Map: {record.digest}")
        return 0
    record = repository.load(args.name, integrity)
    if args.baseline_command == "show":
        print(json.dumps(record.to_dict(), indent=2, sort_keys=True))
        return 0
    runtime = LinuxDeviceStateProvider().collect()
    runtime_hash, differences = repository.compare(record, runtime, integrity)
    print(f"Baseline I2Map: {record.digest}")
    print(f"Runtime I2Map:  {runtime_hash}")
    print("Integrity match:", "YES" if runtime_hash == record.digest else "NO")
    _print_differences(differences)
    return 0 if runtime_hash == record.digest else 1


def _test_command(
    args: argparse.Namespace,
    config: AppConfig,
    integrity: CanonicalIntegrityProvider,
    registry: ScenarioRegistry,
) -> int:
    if args.test_command == "list":
        for scenario in registry.list():
            print(f"{scenario.metadata.test_id:<8} {scenario.metadata.category:<14} {scenario.metadata.name}")
        return 0
    if args.test_command == "stability":
        summary = run_stability(LinuxDeviceStateProvider(include_package_inventory=False), integrity, args.iterations, config.max_stability_iterations)
        evidence = EvidenceSession.create(config.evidence_dir, "STABILITY")
        evidence.write_json("result.json", summary.to_dict())
        environment = detect_environment()
        changes = [difference for mismatch in summary.mismatches for difference in mismatch["differences"]]
        report = {
            "test_id": "STABILITY",
            "test_name": "Repeated unchanged-state stability test",
            "category": "stability",
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "device": socket.gethostname(),
            "operating_system": platform.system(),
            "environment": environment.kind,
            "environment_mode": "normal",
            "threat": "False-positive integrity mismatch on an unchanged device",
            "expected_result": "All repeated I2Maps match iteration one",
            "baseline_hash": summary.baseline_hash,
            "runtime_hash": summary.hashes[-1],
            "integrity_match": summary.mismatching_iterations == 0,
            "changed_parameters": changes,
            "detection_result": "TRUE_NEGATIVE" if summary.mismatching_iterations == 0 else "FALSE_POSITIVE",
            "status": "PASS" if summary.mismatching_iterations == 0 else "FAIL",
            "restoration_status": "NOT REQUIRED",
            "evidence": [str(evidence.root / "result.json"), str(evidence.root / "commands.log"), str(evidence.root / "run.log")],
            "errors": [],
            "notes": [f"{summary.matching_iterations}/{summary.iterations} matching; false-positive rate {summary.false_positive_rate:.6f}"],
        }
        ReportWriter(config.reports_dir).write(report)
        print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
        print(f"Evidence: {evidence.root}")
        return 0 if summary.mismatching_iterations == 0 else 1
    if args.test_command == "run":
        scenarios = [registry.get(args.test_id)]
    elif args.test_command == "all":
        scenarios = registry.list()
    else:
        scenarios = registry.category(args.test_command)
    mode = _mode_from_args(args)
    results = []
    for scenario in scenarios:
        provider = _provider_for_scenario(scenario)
        context = ScenarioContext(
            config,
            provider,
            integrity,
            mode,
            interactive=getattr(args, "interactive", False),
        )
        result = scenario.run(context)
        results.append(result)
        print(f"{result.test_id}: {result.status.value} — {result.detection_result}")
        if result.actual_changes:
            print("  changed:", ", ".join(item.path for item in result.actual_changes))
        print("  restoration:", result.restoration_status.value)
        if result.evidence:
            print("  evidence:", result.evidence[0])
        for note in result.notes:
            print("  note:", note)
        for error in result.errors:
            print("  error:", error)
    return 1 if any(item.status in {ResultStatus.FAIL, ResultStatus.ERROR} for item in results) else 0


def _provider_for_scenario(scenario: BaseSecurityTest) -> LinuxDeviceStateProvider:
    target = getattr(scenario, "target", None)
    paths = (target,) if isinstance(target, Path) else ()
    if getattr(scenario, "state_category", "software") == "configuration":
        return LinuxDeviceStateProvider(include_package_inventory=False, configuration_paths=paths)
    return LinuxDeviceStateProvider(paths, include_package_inventory=False)


def _mode_from_args(args: argparse.Namespace) -> TestMode:
    if getattr(args, "simulation", False):
        return TestMode.SIMULATION
    if getattr(args, "dry_run", False):
        return TestMode.DRY_RUN
    if getattr(args, "real_test", False):
        return TestMode.REAL_TEST
    return TestMode.NORMAL


def _report_command(args: argparse.Namespace, config: AppConfig) -> int:
    writer = ReportWriter(config.reports_dir)
    if args.report_command == "list":
        for path in writer.list():
            print(path.name)
        return 0
    matches = writer.find(args.query)
    if not matches:
        raise ValueError(f"no report matches {args.query}")
    print(matches[0].read_text(encoding="utf-8"))
    return 0


def _print_differences(differences: list[object]) -> None:
    if not differences:
        print("Changed parameters: none")
        return
    print("Changed parameters:")
    for difference in differences:
        print(f"  {difference.path}")  # type: ignore[attr-defined]
        print(f"    before: {difference.before!r}")  # type: ignore[attr-defined]
        print(f"    after:  {difference.after!r}")  # type: ignore[attr-defined]
