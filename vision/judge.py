"""Vision judgment module — sends photos to Ollama vision model for evaluation."""

import base64
import re

import requests


def judge_photo(photo_path, goal, config, prompts):
    """
    Send a photo to the vision model and get a structured judgment.

    Args:
        photo_path: Path to the (preprocessed) photo file.
        goal: The drawing goal string (e.g., "draw a red circle").
        config: Parsed device.yaml dict.
        prompts: Parsed prompts.yaml dict.

    Returns:
        tuple: (score: int, description: str, raw_response: str)
            - score: 1-10 rating of how well the display matches the goal.
            - description: The vision model's full description.
            - raw_response: Unmodified model output.
    """
    with open(photo_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    prompt = prompts["vision"]["judge"].format(goal=goal)
    ollama_cfg = config["ollama"]

    response = requests.post(
        f"{ollama_cfg['host']}/api/chat",
        json={
            "model": ollama_cfg["vision_model"],
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64],
                },
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        },
        timeout=600,
    )
    response.raise_for_status()
    raw_text = response.json()["message"]["content"]

    score = _extract_score(raw_text)
    return score, raw_text, raw_text


def _extract_score(text):
    """
    Parse numeric score from vision model response.

    Looks for patterns like:
        Score: 7/10
        Score: 7
        7/10
    """
    # Try "Score: N/10" or "Score: N" first
    match = re.search(r"[Ss]core[:\s]+(\d+)\s*/\s*10", text)
    if match:
        return min(int(match.group(1)), 10)

    match = re.search(r"[Ss]core[:\s]+(\d+)", text)
    if match:
        val = int(match.group(1))
        if 1 <= val <= 10:
            return val

    # Try bare "N/10" anywhere
    match = re.search(r"(\d+)\s*/\s*10", text)
    if match:
        return min(int(match.group(1)), 10)

    # Conservative default — triggers re-iteration
    return 0
