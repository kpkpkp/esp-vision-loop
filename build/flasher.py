"""Flash module — deploys compiled firmware to ESP32 via USB serial."""

import json
import os
import subprocess


def _get_idf_env():
    """Build an environment dict with ESP-IDF variables."""
    env = os.environ.copy()
    idf_path = env.get("IDF_PATH", os.path.expanduser("~/esp/esp-idf"))
    env["IDF_PATH"] = idf_path
    return env


def _detect_usb_device():
    """
    On Termux without root, use termux-usb to find connected USB devices.

    Returns:
        str or None: The USB device path, or None if not found.
    """
    try:
        result = subprocess.run(
            ["termux-usb", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            devices = json.loads(result.stdout)
            if devices:
                return devices[0]
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return None


def flash_device(config, project_dir):
    """
    Flash the compiled firmware to the ESP32.

    Tries direct serial port first (works on rooted devices or with
    proper permissions). Falls back to termux-usb wrapper on unrooted Android.

    Args:
        config: Parsed device.yaml dict.
        project_dir: Path to the ESP-IDF project directory.

    Returns:
        tuple: (success: bool, output: str)
    """
    port = config["board"]["serial_port"]
    baud = config["board"]["baud_rate"]
    env = _get_idf_env()

    # Try direct idf.py flash first
    if os.path.exists(port):
        return _flash_direct(project_dir, port, baud, env)

    # Fall back to termux-usb
    usb_device = _detect_usb_device()
    if usb_device:
        return _flash_termux_usb(project_dir, usb_device, baud, env)

    return False, f"No serial device found at {port} and termux-usb found no devices."


def _flash_direct(project_dir, port, baud, env):
    """Flash using idf.py flash with direct serial port access."""
    result = subprocess.run(
        [
            "idf.py", "-C", project_dir,
            "-p", port,
            "-b", str(baud),
            "flash",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    output = result.stdout + "\n" + result.stderr
    return result.returncode == 0, output


def _flash_termux_usb(project_dir, usb_device, baud, env):
    """
    Flash using termux-usb to request USB permission and pass fd.

    termux-usb -r -e <script> <device> runs <script> with the USB fd
    as an argument. We create a small wrapper script that uses esptool.py
    with the provided fd.
    """
    # Find the built firmware binary
    build_dir = os.path.join(project_dir, "build")
    bin_path = os.path.join(build_dir, "display_demo.bin")
    bootloader_path = os.path.join(build_dir, "bootloader", "bootloader.bin")
    partition_path = os.path.join(build_dir, "partition_table", "partition-table.bin")

    # Create a wrapper script for termux-usb
    wrapper_path = os.path.join(project_dir, "_flash_wrapper.sh")
    wrapper_content = f"""#!/data/data/com.termux/files/usr/bin/bash
# termux-usb passes the USB file descriptor as $1
FD=$1
esptool.py --chip {env.get('IDF_TARGET', 'esp32')} \\
    --port /proc/self/fd/$FD \\
    --baud {baud} \\
    write_flash \\
    0x0 "{bootloader_path}" \\
    0x8000 "{partition_path}" \\
    0x10000 "{bin_path}"
"""
    with open(wrapper_path, "w") as f:
        f.write(wrapper_content)
    os.chmod(wrapper_path, 0o755)

    result = subprocess.run(
        ["termux-usb", "-r", "-e", wrapper_path, usb_device],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    output = result.stdout + "\n" + result.stderr
    return result.returncode == 0, output
