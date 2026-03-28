# esp-vision-loop

Autonomous code-see-judge-improve loop for ESP32 display programming.

## Quick start

Run `/prime` at the beginning of each session to load project context and check prerequisites.

## proot-distro (ESSENTIAL)

All ESP-IDF builds MUST run inside proot-distro Debian. The Xtensa GCC cross-compiler
requires glibc, which Termux does not have. Without proot, nothing compiles.

```bash
# Enter the build environment
proot-distro login debian

# Inside proot, ESP-IDF and Xtensa toolchain are available
# /tmp is READ-ONLY in proot — use /usr/tmp instead (see memory)
```

- Install: `pkg install proot-distro && proot-distro install debian`
- ESP-IDF lives at: `~/esp/esp-idf` (inside proot)
- Build command: `cd /root/esp-vision-loop/esp_project && ninja -C build -j1`
- **Never run `idf.py set-target` again** — it wipes the build cache (~40min rebuild)

## Architecture

- `orchestrator.py` — main loop: codegen -> build -> flash -> capture -> judge -> iterate
- `codegen/` — LLM code generation via Ollama (deepseek-coder:6.7b)
- `build/` — ESP-IDF build pipeline via proot-distro Debian
- `capture/` — camera capture (Android intent or manual)
- `vision/` — photo judgment via Ollama (bakllava)
- `config/` — device.yaml (hardware), prompts.yaml (LLM prompts)
- `esp_project/` — the ESP-IDF project that gets built
- `chronicles/` — session history and lessons learned
- `logs/` — build logs, iteration JSON logs

## Critical rules

- **Never re-run `idf.py set-target`** — it wipes all cached build objects (~40min rebuild)
- **Never run Ollama and builds simultaneously** — OOM killer will strike
- **Don't modify `esp_project/main/display_init.h`** — it's hand-written and tested
- **Build with `ninja -j1`** inside proot to avoid OOM
- **Only `main.c` changes between iterations** — everything else is cached

## Platform

Termux on Android (Play Store build), aarch64, 16GB RAM.
ESP-IDF cross-compilation via proot-distro Debian with Xtensa GCC.
