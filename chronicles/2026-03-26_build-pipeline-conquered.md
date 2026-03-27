# Session Chronicle: Build Pipeline Conquered

**Date:** 2026-03-26 (session 3)
**Platform:** Termux on Android (aarch64, 15GB RAM)
**Duration:** ~2 hours (mostly waiting for compilation)
**Outcome:** ESP-IDF cross-compilation working end-to-end on phone via proot

---

## What Got Done

### The build works
- 997 ESP-IDF object files compile successfully on a phone
- Xtensa GCC 14.2.0 (ARM64 build) running inside proot-distro Debian
- main.c fails with expected errors — the LLM-generated code uses fake APIs
- After initial build, only main.c recompiles (seconds, not minutes)

### OOM war
- First attempt: OOM-killed at 437/997 (Claude Code + proot + ninja together)
- Second attempt: OOM-killed at ~950/997 (even with Claude Code stopped, default parallelism)
- Third attempt: `set-target` triggered fullclean, wiped cached objects, started over
- Fourth attempt: SUCCESS — ninja -j1 + skip set-target + auto-retry script

### Architecture refined
- `builder.py` now runs `ninja -j1` directly inside proot (not `idf.py build`)
- `set-target` only runs once (when `build.ninja` doesn't exist) — it triggers fullclean
- `build_retry.sh` auto-retries up to 10x, each picking up cached .o files
- Ollama killed before build to free RAM

---

## Milestones (Project-wide)

| # | Milestone | Status | Date |
|---|-----------|--------|------|
| 1 | System design and plan | Done | 2026-03-25 |
| 2 | All source files written | Done | 2026-03-25 |
| 3 | Git repo created and pushed | Done | 2026-03-25 |
| 4 | Python + packages installed | Done | 2026-03-26 |
| 5 | Ollama + models working | Done | 2026-03-26 |
| 6 | Dry-run loop succeeds (codegen + vision) | Done | 2026-03-26 |
| 7 | ESP-IDF toolchain on ARM64 | Done | 2026-03-26 |
| 8 | Build pipeline verified (framework compiles) | Done | 2026-03-26 |
| 9 | Full orchestrator run with real build | **Next** | |
| 10 | First compilable main.c (build-error loop works) | Pending | |
| 11 | USB flash to real ESP32 | Pending | |
| 12 | Camera capture of display | Pending | |
| 13 | Complete loop: code-build-flash-photo-judge | Pending | |
| 14 | First successful shape on hardware | Pending | |

---

## Lessons Learned

### 1. The OOM killer is the real adversary on Android

Not the toolchain. Not proot. Not the cross-compiler. The Android OOM killer is aggressive and silent — it sends SIGKILL with no warning, no core dump, no log. You find out when your terminal says `[Process completed (signal 9)]`.

**Lesson:** On memory-constrained Android, never run two heavy processes simultaneously. Build OR infer, never both. Design for sequential, not parallel.

### 2. `idf.py set-target` is destructive

It calls `fullclean` internally. Every. Time. Running it before each build wipes all cached object files, turning a 5-second incremental rebuild into a 40-minute full rebuild.

**Lesson:** Never put `set-target` in a build loop. Run it once. Check for `build.ninja` to know if it's needed. Use `ninja` directly for subsequent builds.

### 3. Incremental builds change the economics

The initial ESP-IDF build compiles 997 files (~40 min on phone). But after that, changing `main.c` only recompiles 1 file + re-links. This takes seconds. The build-error feedback loop becomes practical only because of this asymmetry.

**Lesson:** Front-load the expensive build. Then iterate cheaply. The system's design should account for a painful first build and fast subsequent ones.

### 4. Auto-retry is the right pattern for unreliable environments

The build_retry.sh script runs ninja, and if it gets killed, waits 5 seconds and runs it again. Ninja sees the cached .o files and picks up where it left off. The user doesn't need to babysit it.

**Lesson:** If your environment is unreliable (OOM, flaky network, intermittent hardware), design for automatic resumption, not manual retry. Idempotent + incremental = resilient.

### 5. Claude Code itself is a RAM hog

Claude Code's Node.js runtime + context + tools consume 2-3GB of RAM. That's 15-20% of this phone's total. When you add Ollama (4-8GB for loaded models) and proot + ninja, you're at 100%.

**Lesson:** The orchestrator needs a "low-memory mode" that stops Ollama during builds and restarts it for codegen/vision. RAM is a scheduling problem, not just a capacity problem.

### 6. The tool was fighting the platform

We spent multiple sessions getting the toolchain to work on Termux. The fix was always the same pattern: find the right abstraction layer (proot for glibc, CLAUDE_CODE_TMPDIR for sandbox, termux-usb for serial). Android isn't hostile to development — it's just opinionated about how things should work.

**Lesson:** Every platform fight has a translation layer. The question isn't "can it work?" but "what's the adapter?"

---

## Wisdom

- **Compilation on a phone is not a toy demo.** 997 object files, Xtensa cross-compilation, 40 minutes of real work. A phone in 2026 has more computing power than the build servers that compiled the first Linux kernels. The limitation is RAM, not CPU.

- **The feedback loop speed is what matters.** A 40-minute first build is tolerable. A 40-minute rebuild for each code fix is not. The difference between "this works" and "this is useless" is incremental compilation.

- **Android's memory management is designed for phones, not dev machines.** The OOM killer protects the foreground app (your messaging, your camera). Background processes (your compiler) are expendable. Designing around this isn't a hack — it's respecting the platform's priorities.

- **The hardest part of this project wasn't AI. It was plumbing.** We have vision models, coding models, prompt engineering, an orchestrator loop. None of that was the bottleneck. The bottleneck was: can we compile C code on this phone without getting killed.

---

## What's Next

The expensive one-time build is done. The framework objects are cached. Now:

1. Run the orchestrator with real builds (only main.c recompiles — fast)
2. Watch the build-error feedback loop fix the fake API calls
3. Get a compilable main.c that actually draws a circle
4. (Then: flash, photo, judge — but that's hardware-dependent)

The software system is feature-complete. What remains is tuning and hardware integration.

---

*"The phone compiled 997 files and didn't flinch. It just needed to do them one at a time."*
