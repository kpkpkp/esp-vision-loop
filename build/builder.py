"""Build module — wraps idf.py build and manages ESP-IDF component dependencies."""

import os
import subprocess

# Map display driver names to ESP Component Registry packages
DRIVER_COMPONENTS = {
    "st7789": None,  # Built into esp_lcd in ESP-IDF v5.x
    "ili9341": "espressif/esp_lcd_ili9341",
    "ssd1306": "espressif/esp_lcd_ssd1306",
    "sh1106": "espressif/esp_lcd_sh1106",
    "gc9a01": "espressif/esp_lcd_gc9a01",
    "st7735": "espressif/esp_lcd_st7735",
}


def _get_idf_env():
    """
    Build an environment dict with ESP-IDF variables.
    Assumes the user has sourced export.sh or IDF_PATH is set.
    """
    env = os.environ.copy()
    idf_path = env.get("IDF_PATH", os.path.expanduser("~/esp/esp-idf"))
    env["IDF_PATH"] = idf_path
    return env


def _write_component_yml(project_dir, config):
    """Write idf_component.yml to pull the correct display driver component."""
    driver = config["display"]["driver"]
    component = DRIVER_COMPONENTS.get(driver)

    main_dir = os.path.join(project_dir, "main")
    os.makedirs(main_dir, exist_ok=True)
    yml_path = os.path.join(main_dir, "idf_component.yml")

    if component:
        content = (
            f"dependencies:\n"
            f"  {component}: \"*\"\n"
        )
    else:
        content = "dependencies: {}\n"

    with open(yml_path, "w") as f:
        f.write(content)


def write_main_c(project_dir, code):
    """Write the generated C code to the ESP-IDF project's main.c."""
    main_c_path = os.path.join(project_dir, "main", "main.c")
    os.makedirs(os.path.dirname(main_c_path), exist_ok=True)
    with open(main_c_path, "w") as f:
        f.write(code)


def build_project(config, project_dir):
    """
    Run idf.py set-target and idf.py build.

    Args:
        config: Parsed device.yaml dict.
        project_dir: Path to the ESP-IDF project directory.

    Returns:
        tuple: (success: bool, output: str)
    """
    env = _get_idf_env()
    chip = config["board"]["chip"]

    # Write component dependencies based on display driver
    _write_component_yml(project_dir, config)

    # Set target (only needed once, but safe to re-run)
    result = subprocess.run(
        ["idf.py", "-C", project_dir, "set-target", chip],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    if result.returncode != 0:
        output = result.stdout + "\n" + result.stderr
        # set-target failure is fatal
        return False, _truncate(output)

    # Build
    result = subprocess.run(
        ["idf.py", "-C", project_dir, "build"],
        capture_output=True,
        text=True,
        env=env,
        timeout=600,
    )
    output = result.stdout + "\n" + result.stderr
    return result.returncode == 0, _truncate(output)


def _truncate(text, max_lines=150):
    """Keep only the last max_lines of build output to fit in LLM context."""
    lines = text.strip().split("\n")
    if len(lines) > max_lines:
        return "... (truncated) ...\n" + "\n".join(lines[-max_lines:])
    return text.strip()
