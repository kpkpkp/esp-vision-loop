# Session Chronicle: Fresh Device Bootstrap

**Date:** 2026-03-28
**Platform:** Termux on Android (aarch64, 16GB RAM)
**Duration:** ~15 minutes
**Outcome:** Project primed on fresh device, proot docs elevated, shell launcher created

---

## What Got Done

### Full prime on a bare device
- Ran `/prime` on a fresh Termux install where nothing was installed (no python3, no ollama, no proot-distro)
- Confirmed the repo was cloned and intact but the entire toolchain is missing
- Identified that current `main.c` is stale — uses raw ESP-IDF APIs instead of `display_init.h`
- `codegen_build_test.log` was never created (test from previous session never ran or wasn't committed)

### proot-distro elevated to top of CLAUDE.md
- Added a dedicated "proot-distro (ESSENTIAL)" section right after Quick Start
- Documents: why it's needed (glibc for Xtensa GCC), how to install, how to enter, build commands
- Cross-references the /tmp read-only workaround from memory
- Every future Claude session will see this before anything else

### Shell launcher: `cl_go`
- Added `cl_go` function to `~/.bashrc`
- One command: `cd ~/esp-vision-loop && export CLAUDE_CODE_TMPDIR=~/tmp && claude`
- Replaces the old `cl` function which used wrong env var (`TMPDIR` instead of `CLAUDE_CODE_TMPDIR`)

---

## Lessons Learned

### 1. Essential infrastructure docs go at the top
proot-distro was buried in a one-line mention under "Platform." But it's the single most critical dependency — without it, literally nothing compiles. Moving it to a prominent section with install/usage commands means no session will waste time rediscovering this.

### 2. Shell aliases are underrated DX
The two-command dance (`cd` + `export` + `claude`) is easy to forget or mistype. A single `cl_go` removes friction from every session start. Small ergonomic wins compound.

---

## What's Next

1. Install the full toolchain: proot-distro, python3, ollama, ESP-IDF
2. Regenerate `main.c` using the codegen prompt (current one doesn't use `display_init.h`)
3. Build and iterate toward a compilable result
4. Flash to ESP32 when USB is connected

---

*"A fresh device is a fresh start — but only if the project knows how to explain itself."*
