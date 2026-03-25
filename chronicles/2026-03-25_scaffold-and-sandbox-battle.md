# Session Chronicle: Scaffold & Sandbox Battle

**Date:** 2026-03-25
**Platform:** Termux on Android (aarch64)
**Duration:** ~2 hours
**Outcome:** Project scaffolded, committed, pushed to private GitHub repo

---

## The Vision

Build an autonomous closed-loop system running entirely on a phone that:
1. Generates ESP-IDF C code to draw shapes on an ESP32 display
2. Compiles and flashes the code to the microcontroller
3. Photographs the physical screen with the phone's camera
4. Judges the result using a local vision model (LLaVA)
5. If the shape isn't right, feeds the critique back to a coding model
6. Iterates until the display shows what was asked for

No cloud. No human in the loop. A phone teaching a microcontroller to draw.

---

## What Got Done

- Designed full system architecture (orchestrator, codegen, build, flash, capture, vision)
- Built display-agnostic config system (YAML-driven: swap a driver name and pin map, target any screen)
- Wrote all core modules: generator, builder, flasher, camera, preprocessor, judge
- Created the orchestrator loop with build-error sub-retries, photo preprocessing, and scored vision feedback
- Wrote ESP-IDF project scaffold and Termux setup script
- Pushed 22 files / 1,219 lines to `github.com/kpkpkp/esp-vision-loop` (private)

---

## Milestones

| # | Milestone | Status |
|---|-----------|--------|
| 1 | System design and plan | Done |
| 2 | All source files written | Done |
| 3 | Git repo created and pushed | Done |
| 4 | Environment setup (Ollama, ESP-IDF, toolchain) | Not started |
| 5 | First dry run (mock photo, test Ollama calls) | Not started |
| 6 | First live run (real ESP32, real camera) | Not started |
| 7 | First successful shape rendered and verified | Not started |

---

## Lessons Learned

### 1. `/tmp` is a wall on Termux

The entire first hour was spent fighting a single error:
```
EACCES: permission denied, mkdir '/tmp/claude-10470'
```

Claude Code's sandbox hardcodes `/tmp` for its working directory. On Termux, `/tmp` is owned by root. `TMPDIR=~/tmp` doesn't help — the sandbox ignores it.

**Fix:** `export CLAUDE_CODE_TMPDIR=~/tmp` — a dedicated, non-obvious environment variable.

**Lesson:** Platform assumptions kill. The first bug on any unfamiliar platform is always about paths, permissions, or environment. Budget time for it.

### 2. Copy-paste is a real interface constraint

When the AI can't run commands, the human becomes the executor. But:
- Markdown rendering adds leading spaces that break heredocs
- Long one-liners wrap at terminal width, breaking commands mid-token (`git\n  commit` becomes two commands)
- Multi-line blocks need careful escaping

**Lesson:** When the tool chain is broken, write a `.sh` file and have the user run `bash script.sh`. One command, no paste corruption. We discovered this the hard way after 3 failed paste attempts.

### 3. Solve the meta-problem first

We spent time on architecture, code generation, prompt engineering — all while unable to run a single shell command. The right move was to fix the sandbox issue first, then do everything else with working tools.

**Lesson:** If your tools are broken, fix the tools. Everything else is premature.

### 4. The simplest test reveals the most

The bash test was just `echo "hello"`. It failing told us everything we needed to know. No complex debugging required — just the simplest possible probe.

### 5. Design for device diversity from day one

The user insisted the system work across diverse ESP32 displays — not just one board. This led to the config-driven architecture with `device.yaml` holding driver, interface, resolution, and pin mappings. The coding model receives this as structured context.

**Lesson:** "Make it work on my board" is a trap. "Make it work on any board described by a config file" costs ~10% more upfront and saves rewrites later.

---

## Wisdom

- **A phone teaching a microcontroller to draw is a legitimate engineering system.** The components exist: local LLMs run on phone-class hardware, cameras are built in, USB-OTG connects to dev boards. The gap is glue code — which is what we wrote today.

- **The autonomous loop pattern (generate, test, observe, judge, improve) is universal.** Today it's ESP32 displays. Tomorrow it's PCB layout, robot motion, UI design. The shape of the loop doesn't change, only what plugs into each stage.

- **Local models change the game for hardware iteration.** You can't send photos of your bench to the cloud every 30 seconds during a tight debug loop. But a 7B vision model running on the phone in your hand? That's a co-pilot that can literally see what you see.

- **The hardest part isn't the AI. It's the plumbing.** Xtensa cross-compilation on ARM64, USB serial access without root, camera autofocus on a tiny OLED — these mundane integration problems will be where the real battle is fought.

---

## Next Session Agenda

1. Run `setup.sh` — install Ollama, pull models, attempt ESP-IDF toolchain
2. Tackle the Xtensa-on-ARM64 toolchain problem (the known hard part)
3. Test Ollama API calls with a simple coding prompt
4. Test `termux-camera-photo` capture and preprocessing
5. Dry-run the orchestrator end-to-end with a mock photo
6. Connect real hardware and attempt first live loop

---

*"The loop doesn't need to be perfect. It needs to close."*
