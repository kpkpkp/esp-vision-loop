"""Code generation module — calls Ollama coding model to produce ESP-IDF C code."""

import json
import os
import re

import requests


def _read_template():
    """Load the C template as additional context for the model."""
    tpl_path = os.path.join(os.path.dirname(__file__), "templates", "main_template.c")
    if os.path.exists(tpl_path):
        with open(tpl_path) as f:
            return f.read()
    return ""


def _sanitize_c_code(code):
    """Fix common LLM output issues that break compilation."""
    # Replace full-width Unicode parentheses/brackets with ASCII equivalents.
    # deepseek-coder drifts to CJK characters across iterations.
    replacements = {
        '\uff08': '(',  # （ -> (
        '\uff09': ')',  # ） -> )
        '\uff5b': '{',  # ｛ -> {
        '\uff5d': '}',  # ｝ -> }
        '\uff3b': '[',  # ［ -> [
        '\uff3d': ']',  # ］ -> ]
        '\uff1b': ';',  # ； -> ;
        '\uff0c': ',',  # ， -> ,
        '\u3000': ' ',  # ideographic space
        '\uff1a': ':',  # ： -> :
    }
    for uni, ascii_char in replacements.items():
        code = code.replace(uni, ascii_char)
    return code


def _extract_c_code(text):
    """Extract C code block from LLM response (markdown fences)."""
    match = re.search(r"```c\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return _sanitize_c_code(match.group(1).strip())
    # Fallback: try generic code fences
    match = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return _sanitize_c_code(match.group(1).strip())
    # Last resort: return full text (may contain preamble — caller beware)
    return _sanitize_c_code(text.strip())


def _build_system_prompt(config, prompts):
    """Assemble the system prompt with device config injected."""
    display = config["display"]
    pins = display["pins"]
    return prompts["codegen"]["system"].format(
        chip=config["board"]["chip"],
        driver=display["driver"],
        interface=display["interface"],
        width=display["width"],
        height=display["height"],
        color_depth=display["color_depth"],
        rotation=display["rotation"],
        invert_colors=display.get("invert_colors", False),
        pins=json.dumps(pins),
        pin_mosi=pins.get("mosi", -1),
        pin_sclk=pins.get("sclk", -1),
        pin_cs=pins.get("cs", -1),
        pin_dc=pins.get("dc", -1),
        pin_rst=pins.get("rst", -1),
        pin_bk=pins.get("backlight", -1),
    )


def generate_code(config, goal, previous_code, vision_feedback, prompts):
    """
    Generate ESP-IDF main.c code via Ollama coding model.

    Args:
        config: Parsed device.yaml dict.
        goal: Human-readable drawing goal string.
        previous_code: Previous main.c attempt (str or None).
        vision_feedback: Feedback from vision judge (str or None).
        prompts: Parsed prompts.yaml dict.

    Returns:
        str: The generated C source code for main.c.
    """
    system_prompt = _build_system_prompt(config, prompts)

    # Build user message
    parts = [f"Goal: {goal}"]
    if previous_code:
        parts.append(
            f"Previous code that was attempted:\n```c\n{previous_code}\n```"
        )
    if vision_feedback:
        parts.append(f"Feedback from vision analysis of the previous attempt:\n{vision_feedback}")
    parts.append(prompts["codegen"]["instruction"].format(
        chip=config["board"]["chip"],
    ))

    user_prompt = "\n\n".join(parts)

    ollama_cfg = config["ollama"]
    response = requests.post(
        f"{ollama_cfg['host']}/api/chat",
        json={
            "model": ollama_cfg["coding_model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 2048},
        },
        timeout=1800,
    )
    response.raise_for_status()
    raw = response.json()["message"]["content"]
    return _extract_c_code(raw)


def fix_build_errors(config, code, errors, prompts):
    """
    Ask the coding model to fix compilation errors.

    Args:
        config: Parsed device.yaml dict.
        code: The C source that failed to compile.
        errors: Build error output string.
        prompts: Parsed prompts.yaml dict.

    Returns:
        str: Corrected C source code.
    """
    system_prompt = _build_system_prompt(config, prompts)

    user_prompt = (
        f"Here is the code that failed to compile:\n```c\n{code}\n```\n\n"
        + prompts["codegen"]["fix_build"].format(errors=errors)
    )

    ollama_cfg = config["ollama"]
    response = requests.post(
        f"{ollama_cfg['host']}/api/chat",
        json={
            "model": ollama_cfg["coding_model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 2048},
        },
        timeout=1800,
    )
    response.raise_for_status()
    raw = response.json()["message"]["content"]
    return _extract_c_code(raw)
