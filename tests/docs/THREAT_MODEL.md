# CyberScope Security Threat Model

## Scope

Assets are trusted IoT configuration, executable/application state, software inventory, network identity, peripheral inventory, sensor-data acceptance decisions, I2Map evidence, and the availability of the laboratory device. Threat actors include a local unauthorised user, a malicious maintainer, an attacker who gained application-level access, and a person with physical peripheral access. This model covers detection validation, not exploitation.

| ID | Asset | Threat actor | Attack vector | Affected parameter | Expected security control | Expected I2Map behaviour | Tests |
|---|---|---|---|---|---|---|---|
| T01 | Application code and configuration | Local or application attacker | Modify source/configuration or add an executable | Monitored file existence, SHA-256, mode | Recollect monitored software state and reject changed device state | Base and runtime I2Maps differ | SW-001, SW-003, SW-004 |
| T02 | Approved software inventory | Malicious maintainer or compromised updater | Introduce an unapproved package/dependency | Python/package inventory | Compare deterministic package inventory with trusted baseline | Base and runtime I2Maps differ | SW-002 |
| T03 | Trusted device configuration | Local privileged or maintenance actor | Change ownership, hostname, or enabled interface | Owner/group, hostname, SPI/I2C state | Attest configuration and prevent sensor-data acceptance on mismatch | Base and runtime I2Maps differ | CFG-003, CFG-004, CFG-005, USB-002 |
| T04 | Network identity and reachability configuration | Local/network administrator account attacker | Change hostname, assigned address, subnet, interface, or gateway | Hostname, interfaces, IP/prefix, default route | Attest network state before accepting device data | Base and runtime I2Maps differ | NET-001, NET-003 |
| T05 | Expected network environment | Rogue access-point operator or local attacker | Change DNS, SSID, or MAC identity | Resolver addresses, SSID, interface MAC | Detect rogue/changed network settings; never auto-connect during testing | Base and runtime I2Maps differ | NET-002, NET-004, NET-005 |
| T06 | Authorised peripheral set | Person with physical device access | Attach an unauthorised USB device | Vendor ID, product ID, manufacturer, product, serial | Compare stable USB identities and identify additions | Base and runtime I2Maps differ; added identity is flagged | USB-001 |
| T07 | Security/application configuration | Local or application attacker | Modify a configuration field | File SHA-256 and metadata | Attest the controlled configuration file | Base and runtime I2Maps differ | CFG-001, SW-001 |
| T08 | Configuration access policy | Local user or compromised process | Change file permissions | POSIX mode, owner/group, file SHA-256 | Attest metadata as well as content | Base and runtime I2Maps differ | CFG-002 |

## Trust Boundaries and Assumptions

- The baseline is created only after the operator verifies the device is trusted.
- The collector and Python runtime are assumed not to be controlled by the attacker during this prototype test.
- Output evidence is local laboratory evidence, not an immutable audit ledger.
- Physical tests occur only on owned/authorised devices.
- A mismatch blocks or rejects sensor data in the wider CyberScope system; this repository records the decision but does not implement that external data path.

## Security-Control Limitations

I2Map comparison is a detective control. It cannot prove the reason for a change, repair a compromised host, prevent privileged measurement forgery, or replace secure boot and hardware-backed attestation. Unsupported measurements reduce coverage and are retained explicitly in evidence. Dynamic measurements are excluded because instability would undermine the control with false positives.
