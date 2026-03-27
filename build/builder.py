"""
Build module — wraps idf.py build via proot-distro Debian.

On Termux/Android, the Xtensa cross-compiler (glibc) cannot run natively
under bionic. All builds are dispatched into a proot-distro Debian
environment where ESP-IDF's ARM64 toolchain works.
"""

import logging
import os
import subprocess

log = logging.getLogger("esp-vision-loop.builder")

# Map display driver names to ESP Component Registry packages
DRIVER_COMPONENTS = {
    "st7789": None,  # Built into esp_lcd in ESP-IDF v5.x
    "ili9341": "espressif/esp_lcd_ili9341",
    "ssd1306": "espressif/esp_lcd_ssd1306",
    "sh1106": "espressif/esp_lcd_sh1106",
    "gc9a01": "espressif/esp_lcd_gc9a01",
    "st7735": "espressif/esp_lcd_st7735",
}

# The ESP-IDF path inside the proot Debian environment
PROOT_IDF_PATH = "/root/esp/esp-idf"


def _write_component_yml(project_dir, config):
    """Write idf_component.yml to pull the correct display driver component."""
    driver = config["display"]["driver"]
    component = DRIVER_COMPONENTS.get(driver)

    main_dir = os.path.join(project_dir, "main")
    os.makedirs(main_dir, exist_ok=True)
    yml_path = os.path.join(main_dir, "idf_component.yml")

    if component:
        content = f"dependencies:\n  {component}: \"*\"\n"
    else:
        content = "dependencies: {}\n"

    with open(yml_path, "w") as f:
        f.write(content)
    log.debug("Wrote idf_component.yml: %s", content.strip())


def write_main_c(project_dir, code):
    """Write the generated C code to the ESP-IDF project's main.c."""
    main_c_path = os.path.join(project_dir, "main", "main.c")
    os.makedirs(os.path.dirname(main_c_path), exist_ok=True)
    with open(main_c_path, "w") as f:
        f.write(code)
    log.info("Wrote main.c (%d lines) to %s", len(code.splitlines()), main_c_path)


def _run_in_proot(command_str, timeout=600):
    """
    Execute a bash command inside proot-distro Debian.

    Args:
        command_str: Shell command to run inside the proot environment.
        timeout: Seconds before killing the process.

    Returns:
        tuple: (returncode: int, stdout: str, stderr: str)
    """
    full_cmd = [
        "proot-distro", "login", "debian", "--",
        "bash", "-c", command_str,
    ]
    log.debug("proot command: %s", command_str[:200])

    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as e:
        log.error("proot command timed out after %ds", timeout)
        stdout = e.stdout.decode() if e.stdout else ""
        stderr = e.stderr.decode() if e.stderr else ""
        return -1, stdout, stderr + f"\n[TIMEOUT after {timeout}s]"


def build_project(config, project_dir):
    """
    Build the ESP-IDF project inside proot-distro Debian.

    The project directory is accessible inside proot at its full
    Termux path (/data/data/com.termux/files/home/...).

    Args:
        config: Parsed device.yaml dict.
        project_dir: Absolute path to the ESP-IDF project directory.

    Returns:
        tuple: (success: bool, output: str)
    """
    chip = config["board"]["chip"]

    # Write component dependencies based on display driver
    _write_component_yml(project_dir, config)

    log.info("Starting build for chip=%s project=%s", chip, project_dir)

    # Check if build.ninja exists — if not, we need set-target first.
    # set-target triggers fullclean, so only do it once.
    build_ninja = os.path.join(project_dir, "build", "build.ninja")
    if not os.path.exists(build_ninja):
        log.info("No build.ninja found — running set-target (one-time)")
        set_target_script = (
            f"cd {PROOT_IDF_PATH} && . ./export.sh 2>/dev/null && "
            f"cd {project_dir} && "
            f"idf.py set-target {chip} 2>&1"
        )
        rc, stdout, stderr = _run_in_proot(set_target_script, timeout=300)
        if rc != 0:
            output = stdout + "\n" + stderr
            return False, _truncate(_strip_ansi(output))

    # Run ninja directly with -j1 to avoid OOM on Android.
    # ninja is incremental — only recompiles changed files (main.c).
    build_script = (
        f"cd {PROOT_IDF_PATH} && . ./export.sh 2>/dev/null && "
        f"cd {project_dir}/build && "
        f"ninja -j1 2>&1"
    )

    rc, stdout, stderr = _run_in_proot(build_script, timeout=600)

    output = stdout + "\n" + stderr
    output = _strip_ansi(output)
    truncated = _truncate(output)

    if rc == 0:
        log.info("Build succeeded")
    else:
        log.warning("Build failed (rc=%d). Last 20 lines:\n%s",
                     rc, "\n".join(truncated.splitlines()[-20:]))

    return rc == 0, truncated


def _strip_ansi(text):
    """Remove ANSI escape sequences from build output."""
    import re
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)


def _truncate(text, max_lines=150):
    """Keep only the last max_lines of build output to fit in LLM context."""
    lines = text.strip().split("\n")
    if len(lines) > max_lines:
        return "... (truncated) ...\n" + "\n".join(lines[-max_lines:])
    return text.strip()
