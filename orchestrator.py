#!/usr/bin/env python3
"""
ESP Vision Loop — Autonomous Code-See-Judge-Improve Orchestrator

Generates ESP-IDF display code via a local coding model, builds and flashes it
to an ESP32, photographs the result, judges it with a local vision model,
and iterates until the display output matches the goal.

Usage:
    python3 orchestrator.py --goal "draw a red circle centered on screen"
    python3 orchestrator.py --goal "draw a blue hexagon" --config config/device.yaml
    python3 orchestrator.py --goal "fill screen with green" --dry-run
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time

import yaml

from codegen.generator import generate_code, fix_build_errors
from build.builder import build_project, write_main_c
from build.flasher import flash_device
from capture.camera import capture_photo
from capture.preprocess import preprocess_photo
from vision.judge import judge_photo


def _ensure_ollama():
    """Start Ollama if not running."""
    try:
        import requests
        requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
    except Exception:
        print("  Starting Ollama...")
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(5)


def _stop_ollama():
    """Stop Ollama to free RAM for builds."""
    subprocess.run(["pkill", "-f", "ollama"], capture_output=True)
    time.sleep(2)


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def save_log(log_entry, iteration, log_dir="logs"):
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, f"iteration_{iteration:03d}.json")
    with open(path, "w") as f:
        json.dump(log_entry, f, indent=2, default=str)
    return path


def print_status(msg):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")


def run_loop(goal, config, prompts, project_dir, dry_run=False, skip_build=False):
    """
    Main autonomous loop.

    Args:
        goal: Human-readable drawing goal.
        config: Parsed device.yaml.
        prompts: Parsed prompts.yaml.
        project_dir: Path to ESP-IDF project.
        dry_run: If True, skip flash/capture and use a test photo.

    Returns:
        bool: True if goal was achieved within max_iterations.
    """
    loop_cfg = config["loop"]
    max_iter = loop_cfg["max_iterations"]
    threshold = loop_cfg["success_threshold"]
    build_retries = loop_cfg["build_retry_limit"]
    photo_delay = loop_cfg["photo_delay_sec"]

    previous_code = None
    vision_feedback = None

    for iteration in range(1, max_iter + 1):
        log = {"iteration": iteration, "goal": goal}

        # --- STEP 1: CODE GENERATION ---
        _ensure_ollama()
        print_status(f"Iteration {iteration}/{max_iter} — Generating code")
        try:
            code = generate_code(
                config=config,
                goal=goal,
                previous_code=previous_code,
                vision_feedback=vision_feedback,
                prompts=prompts,
            )
        except Exception as e:
            print(f"  [ERROR] Code generation failed: {e}")
            log["status"] = "codegen_failed"
            log["error"] = str(e)
            save_log(log, iteration)
            vision_feedback = f"Code generation failed with error: {e}. Try a simpler approach."
            continue

        log["generated_code"] = code
        write_main_c(project_dir, code)
        print(f"  Generated {len(code.splitlines())} lines of C code.")

        # --- STEP 2: BUILD (with sub-retry loop) ---
        if skip_build:
            print("  [SKIP BUILD] Skipping build step.")
            log["build"] = "skipped"
            build_ok = True

        if not skip_build:
            _stop_ollama()  # Free RAM for build
            print_status(f"Iteration {iteration}/{max_iter} — Building")
            build_ok = False
            for build_attempt in range(1, build_retries + 1):
                print(f"  Build attempt {build_attempt}/{build_retries}...")
                try:
                    success, build_output = build_project(config, project_dir)
                except Exception as e:
                    build_output = str(e)
                    success = False

                log[f"build_attempt_{build_attempt}"] = {
                    "success": success,
                    "output_tail": build_output[-500:] if build_output else "",
                }

                if success:
                    build_ok = True
                    print("  Build SUCCESS.")
                    break

                print(f"  Build FAILED. Asking model to fix errors...")
                _ensure_ollama()
                try:
                    code = fix_build_errors(
                        config=config,
                        code=code,
                        errors=build_output,
                        prompts=prompts,
                    )
                    write_main_c(project_dir, code)
                    log["generated_code"] = code
                except Exception as e:
                    print(f"  [ERROR] Fix generation failed: {e}")
                    break

        if not build_ok:
            print(f"  Build failed after {build_retries} attempts.")
            log["status"] = "build_failed"
            save_log(log, iteration)
            vision_feedback = (
                "The previous code failed to compile even after multiple fix "
                f"attempts. Last build errors:\n{build_output[-300:]}\n"
                "Try a completely different and simpler approach."
            )
            previous_code = code
            continue

        # --- STEP 3: FLASH ---
        if dry_run:
            print("  [DRY RUN] Skipping flash.")
            log["flash"] = "dry_run"
        else:
            print_status(f"Iteration {iteration}/{max_iter} — Flashing")
            try:
                flash_ok, flash_output = flash_device(config, project_dir)
            except Exception as e:
                flash_ok = False
                flash_output = str(e)

            log["flash_output"] = flash_output[-500:] if flash_output else ""

            if not flash_ok:
                print(f"  Flash FAILED: {flash_output[-200:]}")
                log["status"] = "flash_failed"
                save_log(log, iteration)
                vision_feedback = f"Flash failed: {flash_output[-200:]}"
                previous_code = code
                continue

            print("  Flash SUCCESS.")

        # --- STEP 4: WAIT AND CAPTURE ---
        if dry_run:
            print("  [DRY RUN] Skipping capture. Using placeholder.")
            photo_path = _get_dry_run_photo()
            if not photo_path:
                print("  [DRY RUN] No test photo available. Ending.")
                log["status"] = "dry_run_no_photo"
                save_log(log, iteration)
                break
        else:
            print(f"  Waiting {photo_delay}s for display to initialize...")
            time.sleep(photo_delay)

            # Optional camera settle time
            settle = config.get("capture", {}).get("settle_time_sec", 0)
            if settle:
                time.sleep(settle)

            print_status(f"Iteration {iteration}/{max_iter} — Capturing photo")
            try:
                photo_path = capture_photo(config, iteration)
            except Exception as e:
                print(f"  [ERROR] Capture failed: {e}")
                log["status"] = "capture_failed"
                log["error"] = str(e)
                save_log(log, iteration)
                vision_feedback = f"Could not capture photo: {e}"
                previous_code = code
                continue

        # Preprocess (crop + resize)
        try:
            processed_path = preprocess_photo(photo_path, config)
            print(f"  Photo preprocessed: {processed_path}")
        except Exception as e:
            print(f"  [WARN] Preprocessing failed ({e}), using raw photo.")
            processed_path = photo_path

        log["photo_path"] = processed_path

        # --- STEP 5: VISION JUDGMENT ---
        _ensure_ollama()
        print_status(f"Iteration {iteration}/{max_iter} — Judging result")
        try:
            score, description, raw_response = judge_photo(
                photo_path=processed_path,
                goal=goal,
                config=config,
                prompts=prompts,
            )
        except Exception as e:
            print(f"  [ERROR] Vision judgment failed: {e}")
            log["status"] = "judge_failed"
            log["error"] = str(e)
            save_log(log, iteration)
            vision_feedback = f"Vision model failed: {e}. Try generating clearer shapes."
            previous_code = code
            continue

        log["vision_score"] = score
        log["vision_description"] = description
        log["status"] = "judged"
        save_log(log, iteration)

        print(f"  Score: {score}/10")
        print(f"  Vision: {description[:200]}...")

        # --- STEP 6: CHECK TERMINATION ---
        if score >= threshold:
            print_status(
                f"SUCCESS at iteration {iteration}! "
                f"Score: {score}/10 (threshold: {threshold})"
            )
            print(f"  Final code saved at: {project_dir}/main/main.c")
            return True

        # --- STEP 7: PREPARE FEEDBACK ---
        print(f"  Score {score} < threshold {threshold}. Iterating...")
        previous_code = code
        vision_feedback = (
            f"Score: {score}/10. The vision model saw: {description}\n"
            f"The goal was: {goal}\n"
            "Improve the code to better match the goal. Focus on the issues "
            "described above."
        )

    print_status(f"FAILED after {max_iter} iterations. Best effort in logs/.")
    return False


def _get_dry_run_photo():
    """Find a test photo for dry-run mode."""
    test_paths = [
        "capture/photos/test.jpg",
        "test_photo.jpg",
    ]
    for p in test_paths:
        if os.path.exists(p):
            return os.path.abspath(p)
    return None


def main():
    parser = argparse.ArgumentParser(
        description="ESP Vision Loop — Autonomous display code generation"
    )
    parser.add_argument(
        "--goal", required=True,
        help="Drawing goal, e.g. 'draw a red circle centered on screen'"
    )
    parser.add_argument(
        "--config", default="config/device.yaml",
        help="Path to device configuration YAML"
    )
    parser.add_argument(
        "--prompts", default="config/prompts.yaml",
        help="Path to prompt templates YAML"
    )
    parser.add_argument(
        "--project-dir", default="esp_project",
        help="Path to ESP-IDF project directory"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Skip flash and capture; use test photo for vision"
    )
    parser.add_argument(
        "--skip-build", action="store_true",
        help="Skip ESP-IDF build step (for testing without toolchain)"
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)"
    )
    args = parser.parse_args()

    # Set up logging to both console and file
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler("logs/orchestrator.log", mode="a"),
        ],
    )
    log = logging.getLogger("esp-vision-loop")
    log.info("Starting ESP Vision Loop — goal: %s", args.goal)

    # Change to script directory so relative paths work
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    config = load_config(args.config)
    prompts = load_config(args.prompts)

    print_status(f"ESP Vision Loop")
    print(f"  Goal: {args.goal}")
    print(f"  Config: {args.config}")
    print(f"  Display: {config['display']['driver']} "
          f"{config['display']['width']}x{config['display']['height']}")
    print(f"  Coding model: {config['ollama']['coding_model']}")
    print(f"  Vision model: {config['ollama']['vision_model']}")
    print(f"  Max iterations: {config['loop']['max_iterations']}")
    print(f"  Success threshold: {config['loop']['success_threshold']}/10")
    if args.dry_run:
        print("  MODE: DRY RUN (no flash/capture)")
    if args.skip_build:
        print("  MODE: SKIP BUILD (no ESP-IDF compilation)")

    success = run_loop(
        goal=args.goal,
        config=config,
        prompts=prompts,
        project_dir=os.path.abspath(args.project_dir),
        dry_run=args.dry_run,
        skip_build=args.skip_build,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
