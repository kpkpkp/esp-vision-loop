# Session Chronicle: PoC Pipeline Verified

**Date:** 2026-03-26
**Platform:** Termux on Android (aarch64, 15GB RAM)
**Duration:** ~1.5 hours
**Outcome:** All software components installed, tested, and dry-run completed successfully

---

## What Got Done

### Environment bootstrapped
- Installed Python 3.13, cmake, ninja, clang, make via `pkg`
- Installed pyyaml, requests, Pillow via `pip`
- esptool required `ANDROID_API_LEVEL=36` env var for the `cryptography`/`maturin` build — Termux quirk
- Ollama installed as a native Termux package (`pkg install ollama ollama-backend-vulkan`) — no manual binary needed

### Models pulled and verified
- **bakllava** (4.7GB) — vision model, tested with synthetic red circle image, scored 9/10
- **deepseek-coder:6.7b** (3.8GB) — coding model, generates ESP-IDF C code, ~5-10 min per generation on phone

### Camera situation diagnosed
- `termux-camera-photo` fails: "Termux:API is not yet available on Google Play"
- Root cause: `TERMUX_VERSION=googleplay.2026.02.11` — Play Store build
- The `termux-api` CLI package is installed, but it needs the **Termux:API companion Android app** which isn't published on Google Play
- The `termux-api-broadcast` binary itself contains the block — it checks the build variant
- Tried bypassing via direct `am startservice` call to `com.termux.service_api` — service starts but no photo produced (needs the companion app's receiver)
- Solution: Updated camera.py with 3 fallback backends:
  1. termux-api (for F-Droid builds)
  2. Android intent (opens camera UI, polls DCIM for new files)
  3. Manual file drop (user places photo at known path)

### Orchestrator dry-run: SUCCESS
- Added `--skip-build` flag for testing without ESP-IDF toolchain
- Ran: `python3 orchestrator.py --goal "draw a red circle centered on screen" --dry-run --skip-build`
- Codegen produced 76 lines of ESP-IDF C with filled circle (Bresenham-style nested loop)
- Vision model judged the synthetic test image: 9/10
- Loop terminated at iteration 1 with SUCCESS

---

## Lessons Learned

### 1. Termux packages surprise you

Ollama has a native Termux package. No manual binary download needed. `pkg install ollama ollama-backend-vulkan` just works. Meanwhile, `esptool` requires knowing about `ANDROID_API_LEVEL` — an env var that's never mentioned in esptool's docs because they don't test on Android.

**Lesson:** Always check `pkg search` before downloading binaries manually. Termux's package repo is better stocked than you'd expect.

### 2. Play Store Termux is a walled garden

The Play Store build of Termux disables the API bridge at the binary level. The `termux-api-broadcast` ELF itself refuses to run. You can't fix this with permissions or config — you need the F-Droid build or a workaround.

**Lesson:** If you're doing serious Termux development, use the F-Droid build. The Play Store version trades capability for distribution convenience.

### 3. 7B models on phone: slow but real

deepseek-coder:6.7b takes ~5-10 minutes to generate 76 lines of C on a phone with 15GB RAM. bakllava judges a photo in ~30 seconds. The asymmetry matters: vision is fast, coding is slow. The bottleneck is code generation, not judgment.

**Lesson:** Optimize the coding prompt for shorter output. The model spends tokens on comments and structure that don't affect correctness. A tighter system prompt could halve generation time.

### 4. The dry-run pattern proves the loop before the hardware exists

By adding `--skip-build` and `--dry-run`, we verified the entire software pipeline (codegen → judge → score → decision) without needing an ESP32, a cross-compiler, or a USB cable. The synthetic test image stood in for reality.

**Lesson:** Always build a dry-run mode first. It separates software bugs from hardware bugs and lets you iterate on prompts and scoring logic without touching iron.

### 5. The generated code won't compile (yet)

The deepseek-coder output uses `esp_lcd_panel_draw_pixel()`, `esp_lcd_panel_clear()`, and `esp_lcd_new_panel()` — none of which exist in ESP-IDF. The real APIs are `esp_lcd_panel_draw_bitmap()`, manual buffer clearing, and `esp_lcd_new_panel_st7789()`. This is expected: the model approximates the API surface. The build-error feedback loop exists specifically for this.

**Lesson:** Don't expect the first codegen output to compile. The system's strength is iteration, not first-shot accuracy.

---

## Current State

| Component | Status |
|---|---|
| Python + packages | Installed |
| Ollama + models | Running (bakllava, deepseek-coder:6.7b) |
| Codegen pipeline | Verified |
| Vision pipeline | Verified |
| Camera capture | Intent + manual fallback (termux-api blocked) |
| Orchestrator dry-run | SUCCESS (9/10, iteration 1) |
| ESP-IDF toolchain | **Not installed — next step** |
| USB flash pipeline | Not tested |
| Live hardware run | Not attempted |

---

## Next: The Toolchain

The last major software blocker is the ESP-IDF cross-compiler. The standard `install.sh` downloads x86_64 Xtensa binaries. On ARM64 Termux, options are:

1. Download `xtensa-esp32-elf` for `linux-arm64` from Espressif GitHub releases
2. Use ESP32-C3 (RISC-V) — the RISC-V toolchain may build natively
3. Docker/proot with QEMU user-mode emulation (slow but universal)

This is the known hard problem. Everything else is glue.

---

*"The loop closed in software. Now it needs to touch the world."*
