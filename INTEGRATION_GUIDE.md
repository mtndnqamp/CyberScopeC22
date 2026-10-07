# CyberScope integration — beginner guide

All changes are on `integration`. Main has not been modified. Teammate hashing and comparison branches were merged by you. Selected blockchain assets and the security framework were then brought in without their old `.env` files or hardcoded startup keys.

## What now works

Collector -> canonical SHA-256 I2Map -> blockchain root hash -> comparison -> mismatch alert hook.
The chain stores only the root hash. Local baseline JSON stores parameter values and the exclusion policy for explaining differences. The local map is validated against its own hash and against the chain before it is used. A mismatch means monitored values changed, not proof of an attack.

The hashing input now includes names and canonical JSON. Old baselines must be recreated. Default exclusions are only CPU usage fields, following the observed CPU false positives. The teammate's broader `--exclude-volatile` option remains explicit. Memory, clock, voltage and other values still need real-device stability testing. The exclusion policy is saved with the baseline and reused automatically.

Pip collection is sorted and uses the exact running Python interpreter. Failure now makes the check incomplete rather than pretending there are no packages. Packages in other virtual environments are not covered. Debian package monitoring is still the teammate's package-count/Python-name approach; it is not a complete package/version inventory.

## Try the local sample demo (PowerShell, from the repo folder)

These samples demonstrate program behavior. They do not attest your laptop or Raspberry Pi. No Discord messages are sent.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe integrity_check.py --backend local --params-file examples/clean.json --baseline-file baseline-demo.json --set-baseline
.\.venv\Scripts\python.exe integrity_check.py --backend local --params-file examples/clean.json --baseline-file baseline-demo.json --no-alert
.\.venv\Scripts\python.exe integrity_check.py --backend local --params-file examples/changed.json --baseline-file baseline-demo.json --no-alert
```

Expected: BASELINE SET, MATCH, then MISMATCH with `pip_packages` changed. Exit 0 = match, 1 = mismatch, 2 = incomplete/configuration error. The QA runner keeps errors separate from detections.

## Start a fresh development blockchain

On this Windows ARM laptop, Ganache failed under ARM Node. An isolated **x64 Node 22** runtime worked via Windows compatibility support. Use x64 Node for this setup. An optional uWS fallback message occurred; the chain still passed the tests.

Codex installed an isolated x64 runtime in ignored `.tools` and installed the Central_Node dependencies on this laptop. From the repo root you can start the development chain with:

```powershell
.\.tools\node.exe Central_Node/dev-chain.cjs
```

Leave that terminal running. On another machine, install x64 Node and then from `Central_Node` use:

```powershell
npm install
npm start
```

`dev-chain.cjs` compiles Aiden's HashReg Solidity contract and deploys it on loopback-only Ganache. It creates fresh temporary development accounts and writes their connection configuration to ignored `.env.demo`, without printing keys. Every restart creates a fresh chain: register a fresh baseline. `.env` and environment variables take priority over `.env.demo`; avoid stale external configuration when using the demo chain. The development chain is not a production service.

Then, from the repo root in another terminal:

```powershell
.\.venv\Scripts\python.exe integrity_check.py --params-file examples/clean.json --baseline-file baseline-chain-demo.json --set-baseline
.\.venv\Scripts\python.exe integrity_check.py --params-file examples/clean.json --baseline-file baseline-chain-demo.json --no-alert
.\.venv\Scripts\python.exe integrity_check.py --params-file examples/changed.json --baseline-file baseline-chain-demo.json --no-alert
```

Blockchain is the default backend. If it is unavailable, the check reports UNKNOWN rather than silently using local trust.

## Discord configuration and verified delivery

The hardcoded webhook fallback has been removed. The group explicitly approved reusing the existing active webhook. It is configured only in ignored local `.env` under `DISCORD_WEBHOOK_URL`; do not post it in chat or commit it. One clearly labelled synthetic mismatch alert was accepted by Discord and its arrival was confirmed in `#alerting-test`.

For a new setup, copy `.env.example` to `.env` and fill in the webhook privately. Nonempty environment variables or `.env` blockchain settings take priority; empty blockchain entries fall back to `.env.demo` for the local demo. Remove `--no-alert` only when an actual Discord message is intended. Alert delivery failure remains separate from the mismatch verdict.

## Actual Raspberry Pi testing still required

Run the collector/check on the Pi using the same Python environment for baseline and checks. Validate repeated unchanged-state checks and controlled package/USB/configuration changes. Windows sample tests do not prove Pi hardware collection or detection rates. Keep the same exclusions; investigate other changing fields before adopting broader exclusions.

A Pi cannot reach laptop Ganache through 127.0.0.1. The current demo binds only to loopback. A cross-device demo needs a separately planned reachable RPC configuration.

## Tests completed in Codex

- Seven core integration tests passed, including clean/mismatch, mocked alert, corrupt baseline, mismatched chain reference, sensor rejection, and error classification.
- Real Ganache: contract compilation/deployment, signed baseline write, bytes32 readback, missing-record handling, clean match/no alert, changed pip sample/alert hook, and mismatched local reference all passed.
- The project development startup script was also tested: it deployed a usable contract and generated working configuration.
- A real synthetic-test Discord alert was delivered and visually confirmed by the user. No actual package was installed as tampering.
- Security framework suite: 61 tests completed with 60 passing and one POSIX chmod test skipped on Windows. Fixed unsupported Unix API handling, log cleanup and a USB simulation bug when inventory is unavailable.
- Four team security simulations (pip, USB, hostname, network) passed against the local production comparison and again against the real Ganache baseline. The framework writes evidence/reports for these runs. No alerts are sent by the security runner.

Run the integrated tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s integration_tests -v
```

Use `tests/README.md` for the separate security framework. The original framework scenarios retain their own reference schema. The team runner below is the explicit bridge to production; its blockchain mode uses unique sample record IDs and does not overwrite the device baseline. Actual host mutation is not performed.

## Connected security tests

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe tests/team_security.py --backend local
.\.venv\Scripts\python.exe tests/team_security.py --backend blockchain
```

The blockchain command requires the development chain to be running. Reports/evidence are written to ignored `tests/output/team/`. The adapters in `tests/cyberscope/integrity/team.py` use the team collector/I2Map; the runner deliberately supplies synthetic parameters, separates CPU diagnostics and then exercises production baseline validation and comparison. The original framework scenarios remain available through `tests/main.py` and their own reference providers.

Framework unit tests (from `tests`):

```powershell
..\.venv\Scripts\python.exe -m unittest discover -s unit_tests -v
```

## Remaining integration limits

HashReg retains Aiden's first-writer ownership: whoever first registers a record controls updates. It is not an administrator-controlled device enrollment scheme. A sample integrity demonstration does not prove collector trust under a privileged attacker. The original framework scenarios use their reference providers; four additional team scenarios now exercise production hashing/comparison. Real Pi/Linux validation remains the testing/device team's responsibility.

The current changes are implemented and tested with synthetic state and a real development blockchain. Final real-device acceptance requires Pi/Linux collection. Discord delivery is confirmed with the existing group-approved webhook. Codex could not launch the Microsoft Store Python base executable from its sandbox, so tests used bundled Python 3.12 with separate compatible dependencies. Python 3.11-compatible Web3 wheels were installed into `.venv`, their inherited Windows permissions were repaired, and the user confirmed both MATCH and MISMATCH against Ganache in that environment.

The npm installation reported 38 dependency advisories (including five critical) in the legacy development toolchain. No automatic major upgrades were applied. Keep this Ganache setup confined to the local capstone demo; it is not a production deployment.

Codex has installed Python 3.11-compatible Web3 and dotenv packages into this laptop's existing .venv. The install command above is for recreating the setup elsewhere.

## Before uploading

Review `git diff` and `git status`. Virtual environments, caches, generated baselines and `.env` files are ignored. Commit/push the reviewed source on integration for team review; merging into main is a separate step. Confirm the push outcome in the handover message. No ignored configuration, dependencies, runtime binaries or generated test evidence should be included.

## Current handover status

Core sample integration, real Ganache comparison and confirmed Discord delivery are complete. Connected team simulations pass for pip, USB, hostname and network changes. Core suite: 7 passed. Framework suite: 60 passed, one POSIX-only test skipped on Windows. Real Pi/Linux collection and physical tampering validation remain with the device/testing team.

The review found no credential literals in the changed/new source files. .env, .env.demo, generated baselines, test evidence, dependency folders and runtime binaries are excluded by Git rules.

Codex could not write this checkout's protected .git/index.lock, even after a permission request. No final integration commit or push has been made by Codex. A prepared Publish-CyberScope.ps1 script stages the reviewed source list, checks exclusions/credentials, commits on integration and pushes that branch when run in the user's own VS Code terminal. A successful push is required before claiming the work is on GitHub.

Suggested team update after the push succeeds:

"I've pushed the integration branch. The Windows sample workflow works end to end: hash -> blockchain comparison -> Discord alert. The connected security simulations and unit tests pass, with one Linux-only permission test skipped on Windows. Please validate actual parameter collection and controlled changes on Pi/Linux. INTEGRATION_GUIDE.md has setup, test commands and limitations."
