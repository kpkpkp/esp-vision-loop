# Session Chronicle: Toolchain & Proot

**Date:** 2026-03-26 (session 2)
**Platform:** Termux on Android (aarch64, 15GB RAM)
**Duration:** ~1 hour
**Outcome:** ESP-IDF toolchain working inside proot-distro Debian, builder.py updated, logging added

---

## What Got Done

### Toolchain problem solved
- Espressif publishes `aarch64-linux-gnu` Xtensa toolchain binaries
- They require glibc — won't run natively on Termux (bionic libc)
- Solution: `proot-distro` with Debian — ESP-IDF's `install.sh` auto-downloads the correct ARM64 toolchain
- Verified: `xtensa-esp-elf-gcc 14.2.0` runs inside proot on this phone

### Environment inside proot Debian
- Debian trixie (arm64) with gcc, cmake, ninja, python3, etc.
- ESP-IDF v5.4.1 cloned and installed
- Termux home directory accessible inside proot at full path (`/data/data/com.termux/files/home/...`)

### Builder rewritten for proot
- `builder.py` now dispatches all `idf.py` commands into `proot-distro login debian -- bash -c "..."`
- ANSI escape stripping on build output (proot adds terminal control codes)
- Build and flash are decoupled: build in proot, flash from native Termux with esptool

### Logging added
- Python `logging` module throughout orchestrator and builder
- Dual output: stderr (console) + `logs/orchestrator.log` (persistent)
- `--log-level DEBUG` flag for crash investigation
- Needed because Termux was crashing during toolchain tests with no trace

### Repo cleanup
- Removed 76,537 lines of accidentally committed build artifacts
- Fixed .gitignore (leading spaces from heredoc paste issue)

---

## Lessons Learned

### 1. proot-distro is the bridge between Android and Linux

Termux runs on bionic. The embedded toolchain world runs on glibc. `proot-distro` gives you a full Debian userland without root. The performance overhead of proot (syscall translation) is acceptable for compilation — it's not a VM, just a namespace remapper.

**Lesson:** When a binary says "linux-arm64" it means "glibc linux-arm64". On Termux, that means proot.

### 2. Build artifacts multiply fast

One `idf.py build` generates hundreds of `.obj` files, cmake artifacts, and intermediate outputs. The build directory was 76K+ lines when accidentally committed. It bloated the repo from 1K to 77K lines.

**Lesson:** Always verify `.gitignore` works before the first build. The leading-space bug in our .gitignore meant the patterns weren't matching. `git status` after a build would have caught it.

### 3. Logging prevents debugging in the dark

Termux crashed during toolchain testing with zero diagnostic output. Without logging, we had no idea where it failed — OOM? proot segfault? toolchain error? Adding structured logging to a file means the next crash leaves a trace.

**Lesson:** Add file-based logging before you need it, not after the crash.

### 4. Decoupled build and flash is the right architecture

Building inside proot, flashing from native Termux. The build produces firmware binaries at a known path. The flasher reads them from the same filesystem. No need to copy files between environments — proot shares the filesystem.

---

## Architecture After This Session

```
Native Termux                    proot-distro Debian
─────────────                    ───────────────────
orchestrator.py ────────────────
  │
  ├─► codegen (Ollama API) ◄────
  │
  ├─► builder.py ──────────────► idf.py build (Xtensa GCC)
  │     (proot-distro login)     esp-idf/export.sh
  │
  ├─► flasher.py ◄──────────────
  │     (native esptool)
  │
  ├─► camera.py ◄───────────────
  │     (intent / manual)
  │
  └─► judge.py (Ollama API) ◄──
```

---

## Next

Test the actual `idf.py build` of our project through the proot pipeline. The generated main.c uses nonexistent ESP-IDF APIs — this will be the first real test of the build-error feedback loop.

---

*"The toolchain doesn't care about your operating system's libc. It cares about its own."*
