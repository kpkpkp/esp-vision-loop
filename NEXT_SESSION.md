# Next Session Prompt

```
/tac-autonomous specs/flutter-vision-loop-demo.md
```

---

Resume esp-vision-loop. **Red circle on display — flash pipeline proven.** Now close the remaining gaps for full on-device autonomy.

## Session Summary (2026-03-29)

**Achieved:** Phone (P9a) compiled ESP-IDF C, flashed it to ESP32-S3 via USB OTG, and a red circle appeared on the round GC9A01 display. Vision scorer saw it and reported "color MATCH: red" (4.5/10).

## What Works

| Component | Status | Details |
|-----------|--------|---------|
| Compile on P9a | **PROVEN** | Xtensa GCC 13.2.0 aarch64 via glibc loader. 0.22s per compile |
| USB flash | **PROVEN** | SLIP protocol, 312 blocks in 30s, reboot + boot capture |
| Display init | **PROVEN** | GC9A01 240×240, pins SCK=10 MOSI=11 CS=9 DC=8 RST=12 BL=40 |
| Vision scoring | **WORKS** | Finds display, identifies colors. Shape detection needs tuning |
| Camera | **WORKS** | Shared CameraService, 30fps rear |
| Skip-build mode | **WORKS** | Codegen → capture → judge (no build/flash) |

## What's Needed (priority order)

1. **Rebuild S3 build kit** — P9a has ESP32 libs, needs ESP32-S3 + GC9A01 component
2. **On-device link** — main.o + ~100 .a libs + 9 linker scripts → app.elf
3. **ELF to ESP image** — app.elf → app.bin (implement in Kotlin, ~150 lines)
4. **Wire BuildService** — replace dead proot code with Kotlin NativeBuildService
5. **LLM model** — download DeepSeek Coder 1.3B INT4 (~0.8GB) for real codegen
6. **Unfilled shapes + complex colors** — outline-only, compound shapes, cyan/magenta/yellow
7. **Scorer tuning** — shape detection at current camera distance
8. **Escalation path** — app reports failure to tutor after N iterations; tutor can fix + redeploy APK

## Hard-Won Lessons

- **ESP32-S3 FLASH_BEGIN is 20 bytes, not 16** — 5th field `begin_rom_encrypted=0`. Without it, writes silently fail (returns success, writes nothing). All non-ESP32 chips need this.
- **Must flash bootloader + partition table + app** — merged at 0x0. App-only at 0x10000 doesn't work with unknown existing bootloader.
- **GCC cc1/as/ld each need glibc wrappers** — gcc exec's subprograms directly, bionic can't load glibc ELFs. Plus unprefixed `as`/`ld` symlinks.
- **The vision scorer tells you the hardware** — it reported "circular shape" for 2 hours while we asked "what display is this?"
- **debugPrint not developer.log** — latter goes to Dart DevTools only, not adb logcat.
- **Red-on-black average brightness is ~17** — below any reasonable "display detected" threshold. Use 25, not 60.

## Key Files

**On P9a (`/data/local/tmp/`):**
- `p9a-kit/toolchain/` — Xtensa GCC + glibc + wrapper scripts
- `p9a-kit/buildkit/` — ESP-IDF framework (ESP32 version — **needs S3 rebuild**)
- `gcc-wrap.sh` — gcc launcher via ld-linux-aarch64.so.1
- `compile.sh` — full compile command (155 -I flags, 10 -D flags)

**On WSL2:**
- `esp_vision_loop_app/` — Flutter app source
- `esp-vision-loop/esp_project/` — ESP-IDF project (now targets ESP32-S3 + GC9A01)
- `specs/flutter-vision-loop-demo.md` — spec with all checkpoints

**Pitfall:** `/tmp/esp-build-kit/` on WSL2 is volatile. Toolchain tarballs + packaging scripts gone after reboot. P9a copy persists.

## Device Info

- **P9a**: Pixel 9a, Tensor G4, 8GB, WiFi ADB `192.168.86.250:46749`
- **ESP32**: ESP32-S3 (chip magic 0x09), Waveshare ESP32-S3-LCD-1.28
- **Display**: GC9A01, 240×240 round, SPI at 20MHz
- **USB**: CH343 (VID=0x1a86 PID=0x55d3)

## Architecture

```
P9a Flutter App (tutor deploys APK)
  │
  ├─ LLM Codegen (stub now, DeepSeek Coder next)
  │   → generates main.c body
  │
  ├─ On-Device Build
  │   ├─ compile.sh → gcc-wrap.sh → ld-linux → xtensa-esp-elf-gcc → main.o
  │   ├─ link.sh → gcc-wrap.sh (g++) → app.elf  [NOT YET]
  │   └─ ElfToEspImage.kt → app.bin  [NOT YET]
  │
  ├─ USB Flash (UsbFlashService.kt)
  │   → SLIP: SYNC → SPI_ATTACH → FLASH_BEGIN(20 bytes for S3)
  │   → FLASH_DATA × N → FLASH_END → hard reset
  │
  ├─ Camera → capture photo of ESP32 display
  │
  └─ Vision Scorer (VisionInferenceService.kt)
      → find display by brightness contrast
      → baseline comparison
      → color matching + shape analysis → score 0-10
      → if score < 7 after 10 iterations → ESCALATE to tutor
```
