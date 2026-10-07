# CyberScope Security Test Cases

| ID | Category | Attack | Expected Parameter | Expected Result |
|---|---|---|---|---|
| SW-001 | Software | Modify controlled `application.conf` | `software.monitored_files` | Content hash and I2Map change; file restored |
| SW-002 | Software | Add isolated package fixture | `software.python_packages` | Inventory and I2Map change in simulation; system Python untouched |
| SW-003 | Software | Modify controlled `sensor_app.py` | `software.monitored_files` | Source hash and I2Map change; bytes restored |
| SW-004 | Software | Create harmless controlled executable | `software.monitored_files` | Existence/hash/mode and I2Map change; file removed/restored |
| NET-001 | Network | Change hostname state | `network.hostname.value` | I2Map change detected in simulation |
| NET-002 | Network | Change DNS state | `network.dns_servers.value` | I2Map change without resolver overwrite |
| NET-003 | Network | Change interface/IP/subnet/gateway state | `network.interfaces.value`, `network.default_routes.value` | I2Map change without disconnecting host |
| NET-004 | Network | Change wireless SSID state | `network.wireless_ssid.value` | I2Map change; no automatic connection |
| NET-005 | Network | Change MAC state | `network.interfaces.value` | I2Map change; no automatic spoofing |
| USB-001 | USB | Connect unauthorised device | `usb.devices.value` | `UNAUTHORISED_DEVICE_DETECTED` and I2Map change |
| USB-002 | USB | Remove trusted device | `usb.devices.value` | `TRUSTED_DEVICE_REMOVED` and I2Map change |
| CFG-001 | Configuration | Modify controlled configuration field | `configuration.monitored_files` | Content hash and I2Map change; file restored |
| CFG-002 | Configuration | Change controlled mode 0644→0600 | `configuration.monitored_files` | Mode and I2Map change; mode restored |
| CFG-003 | Configuration | Simulate ownership change | `configuration.monitored_files` | UID/GID and I2Map change; no real chown |
| CFG-004 | Configuration | Change hostname under device configuration | `configuration.hostname.value` | I2Map change in simulation |
| CFG-005 | Configuration | Simulate enabled SPI/I2C state | `configuration.enabled_interfaces` | I2Map change; no debug interface enabled |

## Detailed Preconditions and Restoration

### Software cases

SW-001 and SW-003 require a writable controlled test root. The framework snapshots prior existence, bytes, and mode, establishes known safe baseline content, changes it, collects runtime state, and restores the snapshot. SW-002 is simulation-only in this safe release and explicitly records that no package was installed. SW-004 creates a harmless Python script inside the controlled root and restores the exact prior existence/content/mode state.

### Network cases

NET-001 through NET-005 use deterministic simulation by default because changing an active hostname, resolver, route, address, SSID, or MAC can disrupt the environment. They alter only collected state copies, set `environment_mode=simulation`, and require the expected dotted path and I2Map mismatch. Physical Wi-Fi collection reports unsupported if no interface/tool exists. No case connects to an arbitrary network or spoofs a MAC automatically.

### USB cases

USB-001 needs USB inventory support or simulation. Physical mode additionally requires `--interactive`; the operator inserts a known test device after baseline capture. Stable vendor/product/serial identity is preferred. USB-002 requires at least one device in the baseline and skips instead of fabricating a removal if none exists. The operator restores the physical arrangement when prompted and the framework verifies it by recollection; simulations require no restoration.

### Configuration cases

CFG-001/CFG-002 operate only beneath the controlled root and automatically verify bytes/mode restoration. CFG-003 is simulation-only because changing ownership needs privilege and may affect access. CFG-004 is simulation-first; the corresponding network test maps the same threat without assuming hostname indicates platform. CFG-005 collects SPI/I2C if exposed but never automatically enables SPI, I2C, JTAG, or a debugging interface.

## Stability Case

`test stability --iterations 100` performs no tampering. Expected outcome is 100 matching iterations, zero mismatches, and false-positive rate 0.0. Any mismatch is a failed stability validation and includes its recursive parameter differences for investigation.
