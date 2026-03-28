---
name: prime
description: Prime the session for working on esp-vision-loop — reads project state, checks prereqs, loads context
allowed-tools: [Read, Glob, Grep, Bash, Agent]
---

# Prime: esp-vision-loop

You are priming a session to work on **esp-vision-loop** — an autonomous code-see-judge-improve loop that generates ESP-IDF C code to draw shapes on an ESP32 display, builds it, flashes it, photographs the result, and judges it with a local vision model.

## Step 1: Read project state

Read these files to understand where the project stands:

1. `NEXT_SESSION.md` — handoff notes from last session
2. `chronicles/` — read the most recent chronicle(s) for lessons learned
3. `logs/` — check for build logs, iteration logs, test output
4. `esp_project/main/main.c` — the current LLM-generated code (if it exists)
5. `esp_project/main/display_init.h` — the hand-written display init (don't modify)
6. `config/prompts.yaml` — current prompt templates
7. `config/device.yaml` — hardware config
8. `orchestrator.py` — main loop

## Step 2: Check prerequisites

Run these checks and report status:

```bash
# Python
python3 --version

# Pip packages
python3 -c "import yaml, requests, PIL, esptool" 2>&1

# Ollama
ollama --version 2>&1
curl -s --max-time 2 http://127.0.0.1:11434/api/tags 2>/dev/null | python3 -c "import sys,json; [print(f'  {m[\"name\"]}') for m in json.load(sys.stdin).get('models',[])]" 2>/dev/null || echo "Ollama not running"

# proot-distro
proot-distro list 2>/dev/null | grep installed || echo "proot-distro: not found or no distros"

# ESP-IDF
cat ~/esp/esp-idf/version.txt 2>/dev/null || echo "ESP-IDF: not found"

# Build cache
test -f esp_project/build/build.ninja && echo "Build cache: ready (incremental)" || echo "Build cache: none (first build ~40min)"

# USB
ls /dev/ttyUSB0 2>/dev/null && echo "USB: connected" || echo "USB: not connected"

# RAM
free -m | awk '/Mem:/{printf "RAM: %dMB available / %dMB total\n", $7, $2}'
free -m | awk '/Swap:/{printf "Swap: %dMB used / %dMB total\n", $3, $2}'
```

## Step 3: Report milestones

Based on what you read, report which milestones are done and what's next:

- System design, source files, git repo
- Python + Ollama + models installed
- Dry-run loop (codegen + vision)
- ESP-IDF toolchain via proot
- Build pipeline (997 objects cached, incremental ready)
- Full orchestrator with real build
- Compilable main.c via build-error feedback loop
- USB flash to ESP32
- Camera capture of display
- Complete autonomous loop: code-build-flash-photo-judge

## Step 4: Identify the next action

Based on the current state, propose the single most impactful next step. Consider:

- What failed last time? Check logs.
- What's blocking progress? (missing prereqs, build errors, hardware)
- What's the cheapest win? (prompt tweak vs architecture change)

## Key constraints

- **RAM**: Ollama and builds cannot run simultaneously. Kill one before starting the other.
- **Camera**: `termux-camera-photo` is blocked (Play Store Termux). Use Android intent or manual photo drop.
- **Build**: `ninja -j1` inside proot. Never re-run `idf.py set-target` (it wipes cached objects). Only `main.c` recompiles after initial build.
- **USB**: `termux-usb` for serial access (no root).
- **Platform**: Termux on Android, aarch64, 16GB RAM. ESP-IDF builds via proot-distro Debian.

## Output format

Present a concise status dashboard, then the recommended next action with specific commands or file changes to make.
