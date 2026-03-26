"""
Camera capture module — multiple backends for photographing the subject device.

Backends (tried in order):
  1. termux-camera-photo  (needs Termux:API companion app)
  2. Android intent       (opens camera UI, user takes photo manually)
  3. Manual file drop     (waits for user to place a photo at a known path)
"""

import glob
import os
import subprocess
import time
from datetime import datetime


def capture_photo(config, iteration, output_dir="capture/photos"):
    """
    Capture a photo using the best available backend.

    Args:
        config: Parsed device.yaml dict.
        iteration: Current iteration number (for filename).
        output_dir: Directory to save photos.

    Returns:
        str: Absolute path to the captured photo.
    """
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"iter_{iteration:03d}_{timestamp}.jpg"
    filepath = os.path.join(output_dir, filename)
    abs_path = os.path.abspath(filepath)

    method = config.get("capture", {}).get("method", "auto")

    if method == "auto":
        # Try backends in order
        for backend in [_try_termux_api, _try_android_intent, _try_manual]:
            result = backend(config, abs_path)
            if result:
                return result
        raise RuntimeError("No camera backend available.")
    elif method == "termux-api":
        return _try_termux_api(config, abs_path) or _fail("termux-camera-photo")
    elif method == "intent":
        return _try_android_intent(config, abs_path) or _fail("Android intent")
    elif method == "manual":
        return _try_manual(config, abs_path) or _fail("manual capture")
    else:
        raise RuntimeError(f"Unknown capture method: {method}")


def _try_termux_api(config, abs_path):
    """Try termux-camera-photo (requires Termux:API app)."""
    camera_id = config.get("capture", {}).get("camera_id", 0)
    try:
        result = subprocess.run(
            ["termux-camera-photo", "-c", str(camera_id), abs_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and os.path.exists(abs_path):
            return abs_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _try_android_intent(config, abs_path):
    """
    Launch Android camera via intent, wait for user to take photo.
    The photo lands in DCIM; we find the newest file and copy it.
    """
    dcim = "/storage/emulated/0/DCIM/Camera"
    if not os.path.isdir(dcim):
        return None

    # Note existing files
    before = set(glob.glob(os.path.join(dcim, "*.jpg")))

    try:
        subprocess.run(
            ["am", "start", "-a", "android.media.action.IMAGE_CAPTURE"],
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    # Wait for user to take photo (up to 60 seconds)
    print("  [CAMERA] Android camera opened. Take a photo of the display.")
    print("  [CAMERA] Waiting up to 60s for new photo in DCIM...")
    timeout = config.get("capture", {}).get("intent_timeout_sec", 60)
    for _ in range(timeout):
        time.sleep(1)
        after = set(glob.glob(os.path.join(dcim, "*.jpg")))
        new_files = after - before
        if new_files:
            newest = max(new_files, key=os.path.getmtime)
            # Copy to our output path
            import shutil
            shutil.copy2(newest, abs_path)
            print(f"  [CAMERA] Got photo: {newest}")
            return abs_path

    print("  [CAMERA] Timed out waiting for photo.")
    return None


def _try_manual(config, abs_path):
    """
    Manual mode: wait for user to place a photo at the drop path.
    Useful when no automated camera backend works.
    """
    drop_dir = os.path.dirname(abs_path)
    drop_path = os.path.join(drop_dir, "manual_drop.jpg")

    # Check if a pre-placed file exists
    if os.path.exists(drop_path):
        import shutil
        shutil.copy2(drop_path, abs_path)
        os.remove(drop_path)
        print(f"  [CAMERA] Using manually dropped photo.")
        return abs_path

    print(f"  [CAMERA] No automated camera available.")
    print(f"  [CAMERA] Take a photo and place it at:")
    print(f"           {drop_path}")
    print(f"  [CAMERA] Waiting up to 120s...")

    for _ in range(120):
        time.sleep(1)
        if os.path.exists(drop_path):
            import shutil
            shutil.copy2(drop_path, abs_path)
            os.remove(drop_path)
            print(f"  [CAMERA] Got manually dropped photo.")
            return abs_path

    return None


def _fail(method):
    raise RuntimeError(f"Camera capture failed with method: {method}")
