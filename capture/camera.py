"""Camera capture module — wraps termux-camera-photo."""

import os
import subprocess
from datetime import datetime


def capture_photo(config, iteration, output_dir="capture/photos"):
    """
    Capture a photo using termux-camera-photo.

    Args:
        config: Parsed device.yaml dict.
        iteration: Current iteration number (for filename).
        output_dir: Directory to save photos.

    Returns:
        str: Absolute path to the captured photo.

    Raises:
        RuntimeError: If camera capture fails.
    """
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"iter_{iteration:03d}_{timestamp}.jpg"
    filepath = os.path.join(output_dir, filename)
    abs_path = os.path.abspath(filepath)

    camera_id = config.get("capture", {}).get("camera_id", 0)

    result = subprocess.run(
        ["termux-camera-photo", "-c", str(camera_id), abs_path],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"termux-camera-photo failed (rc={result.returncode}): "
            f"{result.stderr.strip()}"
        )

    if not os.path.exists(abs_path):
        raise RuntimeError(f"Photo file not created at {abs_path}")

    return abs_path
