#!/usr/bin/env python3
"""
pi_device_params.py

Pulls hardware, software, and network/device-config parameters from a
Raspberry Pi and stores them in a list variable (list of (parameter_name,
value) tuples).

Requires:
    pip install psutil
Many parameters rely on Linux/Raspberry Pi OS specific commands and files
(vcgencmd, /proc, /sys, /etc/os-release, iwgetid, lsusb, ip route, dpkg).
Fields will come back as None on systems where the relevant command/file
isn't available.
"""

import os
import sys
import socket
import getpass
import platform
import subprocess

try:
    import psutil
except ImportError:
    raise SystemExit("This script requires psutil. Install it with: pip install psutil")


def run_command(cmd):
    """Run a shell command and return its stripped output, or None on failure."""
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def read_file(path):
    """Read a file and return its stripped contents, or None on failure."""
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return None


# --------------------------------------------------------------------------
# Hardware Parameters
# --------------------------------------------------------------------------

def get_mac_address():
    """MAC address of the primary (default-route) network interface."""
    return run_command("cat /sys/class/net/$(ip route show default | awk '{print $5}')/address")


def get_serial_number():
    """Hardware serial number, from /proc/cpuinfo."""
    output = run_command("grep Serial /proc/cpuinfo")
    if output and ":" in output:
        return output.split(":")[1].strip()
    return None


def get_cpu_clock_frequency():
    """Current CPU clock frequency in MHz."""
    freq = psutil.cpu_freq()
    if freq:
        return round(freq.current, 1)
    # Fallback: vcgencmd (Hz -> MHz)
    output = run_command("vcgencmd measure_clock arm")
    if output and "=" in output:
        try:
            return round(int(output.split("=")[1]) / 1_000_000, 1)
        except ValueError:
            return None
    return None




def get_voltage_supply():
    """Core voltage supply in volts (Raspberry Pi specific, via vcgencmd)."""
    output = run_command("vcgencmd measure_volts core")
    if output and "volt=" in output:
        return output.replace("volt=", "")
    return None


def get_jtag_status():
    """Whether JTAG is enabled, based on /boot(/firmware)/config.txt."""
    for path in ("/boot/firmware/config.txt", "/boot/config.txt"):
        content = read_file(path)
        if content is None:
            continue
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("#"):
                continue
            if "enable_jtag_gpio" in line:
                return "enabled" if line.split("=")[-1].strip() == "1" else "disabled"
    return "disabled (not found in config.txt)"


def get_spi_status():
    """Whether the SPI interface is enabled (checks for /dev/spidev* devices)."""
    output = run_command("ls /dev/spidev* 2>/dev/null")
    if output:
        return f"enabled ({output.replace(chr(10), ', ')})"
    for path in ("/boot/firmware/config.txt", "/boot/config.txt"):
        content = read_file(path)
        if content and "dtparam=spi=on" in content:
            return "enabled (config.txt)"
    return "disabled"


def get_node_cpu_arch():
    """CPU architecture in Node.js `process.arch` naming convention."""
    machine = platform.machine().lower()
    mapping = {
        "x86_64": "x64",
        "amd64": "x64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv7l": "arm",
        "armv6l": "arm",
        "i686": "ia32",
        "i386": "ia32",
    }
    return mapping.get(machine, machine)


def get_total_memory():
    """Total physical memory in MB."""
    return round(psutil.virtual_memory().total / (1024 ** 2), 1)


RESOURCE_THRESHOLD_PERCENT = 85


def get_cpu_usage_status():
    """CPU usage: 'Standard' if usage is within threshold, otherwise the actual percentage."""
    usage = psutil.cpu_percent(interval=1)
    if usage > RESOURCE_THRESHOLD_PERCENT:
        return f"{usage}% (exceeds {RESOURCE_THRESHOLD_PERCENT}% threshold)"
    return "Standard"


def get_memory_usage_status():
    """Memory usage: 'Standard' if usage is within threshold, otherwise the actual percentage."""
    usage = psutil.virtual_memory().percent
    if usage > RESOURCE_THRESHOLD_PERCENT:
        return f"{usage}% (exceeds {RESOURCE_THRESHOLD_PERCENT}% threshold)"
    return "Standard"


# --------------------------------------------------------------------------
# Software Parameters
# --------------------------------------------------------------------------

def get_os_release():
    """OS release / distro name, from /etc/os-release (PRETTY_NAME)."""
    content = read_file("/etc/os-release")
    if not content:
        return None
    for line in content.splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def get_kernel_version():
    """Kernel version (uname -r)."""
    return platform.release()


def get_node_os_platform():
    """OS platform in Node.js `os.platform()` naming convention (e.g. 'linux')."""
    return sys.platform  # 'linux' on Linux, matches Node.js convention


def get_os_machine_type():
    """Machine hardware type (e.g. arm64, x86_64, arm, i386)."""
    return platform.machine()


def get_os_type():
    """OS type (e.g. Linux)."""
    return platform.system()


def get_process_gid():
    """Numerical group ID of the current process."""
    try:
        return os.getgid()
    except AttributeError:
        return None  # not available on non-POSIX systems


def get_process_title():
    """Title/name of the current process."""
    try:
        return psutil.Process(os.getpid()).name()
    except Exception:
        return os.path.basename(sys.argv[0])


def get_installed_package_count():
    """Number of default/installed packages (via dpkg)."""
    return run_command("dpkg --get-selections | wc -l")


def get_python_packages():
    """Installed packages whose name contains the string 'python' (via dpkg)."""
    output = run_command("dpkg -l | grep -i python | awk '{print $2}'")
    if output:
        return output.splitlines()
    return []


def get_pip_packages():
    """Installed Python packages, as 'name==version' strings (via pip)."""
    output = run_command(f"{sys.executable} -m pip list --format=freeze")
    if output:
        return output.splitlines()
    return []


# --------------------------------------------------------------------------
# Network & Device Config
# --------------------------------------------------------------------------

def get_network_interfaces():
    """IP address, subnet mask, and default gateway per active interface."""
    interfaces = {}
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                interfaces[iface] = {
                    "ip_address": addr.address,
                    "subnet_mask": addr.netmask,
                }
    gateway = run_command("ip route show default | awk '{print $3}'")
    return {"interfaces": interfaces, "default_gateway": gateway}


def get_effective_user():
    """Currently effective user running the script."""
    try:
        return getpass.getuser()
    except Exception:
        return None


def get_hostname():
    return socket.gethostname()


def get_dns_servers():
    """Nameserver IP addresses configured for DNS resolution."""
    content = read_file("/etc/resolv.conf")
    if not content:
        return []
    return [line.split()[1] for line in content.splitlines()
            if line.strip().startswith("nameserver")]


def get_wifi_info():
    """Wireless SSID and encryption type of the current connection."""
    ssid = run_command("iwgetid -r")
    encryption = None
    iface = run_command("iwgetid -r --interface 2>/dev/null") or run_command(
        "iw dev | awk '$1==\"Interface\"{print $2; exit}'"
    )
    if iface:
        iw_output = run_command(f"iw dev {iface} link")
        if iw_output:
            enc_output = run_command(f"iwconfig {iface} 2>/dev/null | grep -i 'encryption key'")
            if enc_output:
                encryption = "on" if "on" in enc_output.lower() else "off"
    return {"ssid": ssid, "encryption": encryption}


def get_usb_devices():
    """Details of connected USB devices (via lsusb)."""
    output = run_command("lsusb")
    if output:
        return output.splitlines()
    return []


# --------------------------------------------------------------------------
# Aggregate collection
# --------------------------------------------------------------------------

def get_device_parameters():
    """Collect all device parameters and return them as a list of (name, value) tuples."""

    params = [
        # Hardware Parameters
        ("mac_address", get_mac_address()),
        ("hardware_serial_number", get_serial_number()),
        ("cpu_clock_frequency_mhz", get_cpu_clock_frequency()),
        ("voltage_supply", get_voltage_supply()),
        ("jtag_interface_status", get_jtag_status()),
        ("spi_interface_status", get_spi_status()),
        ("cpu_architecture_node", get_node_cpu_arch()),
        ("total_memory_mb", get_total_memory()),
        ("cpu_usage", get_cpu_usage_status()),
        ("memory_usage", get_memory_usage_status()),

        # Software Parameters
        ("os_release", get_os_release()),
        ("os_kernel_version", get_kernel_version()),
        ("os_platform_node", get_node_os_platform()),
        ("os_machine_type", get_os_machine_type()),
        ("os_type", get_os_type()),
        ("process_group_id", get_process_gid()),
        ("process_title", get_process_title()),
        ("installed_package_count", get_installed_package_count()),
        ("python_packages", get_python_packages()),
        ("pip_packages", get_pip_packages()),

        # Network & Device Config
        ("network_interfaces", get_network_interfaces()),
        ("effective_user", get_effective_user()),
        ("hostname", get_hostname()),
        ("dns_servers", get_dns_servers()),
        ("wifi_info", get_wifi_info()),
        ("usb_devices", get_usb_devices()),
    ]

    return params


if __name__ == "__main__":
    device_params = get_device_parameters()

    print("Device Parameters:")
    print("-" * 60)
    for name, value in device_params:
        print(f"{name:28}: {value}")