# Session Chronicle: Termux Bootstrap Attempt & NPU Pivot

**Date:** 2026-03-29
**Platform:** Pixel 10 Pro (Tensor G5, 16GB), Pixel 9a (Tensor G4, 8GB)
**Duration:** ~4 hours
**Outcome:** Termux pipeline 90% proven, blocked by Play Store Termux sandbox. Architecture pivot to native Flutter+LiteRT planned.

---

## Original Goal

Bootstrap a fully autonomous AI system on an Android phone using Claude Code running in Termux. The system would:
1. Generate ESP-IDF C firmware via on-device LLM (Ollama deepseek-coder:6.7b)
2. Build it via proot-distro Debian (ESP-IDF + Xtensa GCC)
3. Flash it to an attached ESP32 via USB OTG
4. Photograph the result via the phone's camera
5. Judge the result via on-device vision LLM (Ollama bakllava)
6. Iterate until the display matches the goal

No cloud APIs. No external compute. Everything on-device.

---

## Milestones Achieved

### 1. P9a Cloned from P10
- Pulled Termux, Termux:API, F-Droid APKs from P10 via `adb pull` of `/data/app/` paths
- Installed all three on P9a (Pixel 9a)
- Cloned `esp-vision-loop` repo via authenticated git URL
- Installed Ollama natively via `pkg install ollama` (v0.18.3)
- Pulled identical models: deepseek-coder:6.7b + bakllava

### 2. Ollama Standardized on Both Phones
- P10: Ollama already running natively in Termux
- P9a: Initially tried proot-distro (Ollama binary needs glibc), then discovered `pkg install ollama` works natively
- Both phones now have identical model sets

### 3. Codegen Prompt Engineering
- Diagnosed deepseek-coder:6.7b producing full-width Unicode parentheses `（）` after iteration 3+
- Added `_sanitize_c_code()` post-processor for CJK→ASCII replacement
- Rewrote system prompt with concrete EXAMPLE pattern (strip-based drawing with DMA buffer)
- Reduced temperature 0.3→0.1, num_predict 4096→2048
- Reinforced ASCII-only constraint in both system prompt and instruction

### 4. USB Hardware Fully Identified
- CH343 USB-serial chip: VID=0x1a86, PID=0x55d3
- Bulk IN endpoint 0x82 (64 byte), Bulk OUT endpoint 0x02 (32 byte)
- Control transfers work: baud rate set, DTR/RTS toggle confirmed
- ESP32 reset via DTR pulse verified

### 5. P10 Environment Fully Assessed
- Python 3.13, Git, esptool 5.2.0, Ollama 0.18.3 all present
- proot-distro Debian with ESP-IDF v5.4 + Xtensa toolchain installed
- Pre-built binaries exist (display_demo.bin + bootloader.bin)
- Camera working (termux-camera-info returns sensor data)
- 5.9GB RAM available, 105GB storage free, wireless charging active

---

## Lessons Learned

### 1. Play Store Termux Is a Walled Garden (The Session-Killer)

The **single root cause** of both blocking failures:

| Feature | Play Store Termux | F-Droid Termux |
|---|---|---|
| `termux-camera-photo` | BLOCKED ("not yet available on Google Play") | Works |
| `termux-usb` interface claiming | BLOCKED (interfaces held by UsbManager) | Works |
| `termux-usb` control transfers | Works | Works |

**Lesson:** If you're building anything that touches USB or camera from Termux, you MUST use the F-Droid build. The Play Store version trades these capabilities for distribution convenience. This isn't a permissions issue — the binaries themselves check the build variant and refuse.

### 2. Android USB Access Is Not Linux USB Access

On Linux, USB serial devices appear as `/dev/ttyUSB0`. On Android:
- No kernel USB serial driver creates `/dev/ttyUSB*`
- USB devices only accessible via Android's UsbManager Java API
- `termux-usb` provides a raw fd, but it's an Android UsbDeviceConnection, not a Linux USB device fd
- Control endpoint 0 (vendor commands) works via USBDEVFS_CONTROL ioctl
- Bulk endpoints require USBDEVFS_CLAIMINTERFACE, which fails with EBUSY because Android's UsbManager holds the interfaces
- Even USBDEVFS_RESET + re-claim fails — Android immediately re-claims after reset

**Lesson:** "I have a USB fd" ≠ "I can do serial I/O." On Android, the gap between raw USB access and serial port access requires a userspace CDC ACM driver, which requires claimed interfaces, which requires the app framework (not Termux) to cooperate.

### 3. pyserial Doesn't Know About Android

esptool imports `serial.tools.list_ports_posix` at module level. On Termux:
- `sys.platform = 'android'`
- `os.name = 'posix'`
- pyserial 3.5 has no handler for `platform == 'android'` → crashes with ImportError

**Fix applied:** Replaced `list_ports_posix.py` with a minimal Android-compatible version that provides a dummy `comports()` function. This fixed the import error.

**Lesson:** When using Python tools designed for desktop Linux, always check `sys.platform` handling. Android Python reports 'android', not 'linux'. Many libraries crash on this.

### 4. Termux /tmp Is NOT Writable

Scripts created with `cat > /tmp/script.sh` fail silently. `/tmp` in Termux is read-only. Use `$HOME/tmp_*` or `$PREFIX/tmp` instead.

**Lesson:** Never assume Unix conventions in Termux. `/tmp`, `/dev`, `/proc` are all Android-filtered views.

### 5. `input text` Is Fragile for Automation

Typing commands into Termux via `adb shell input text` works but:
- `%s` encodes spaces, but special characters get mangled
- Git credential prompts swallow typed text into username/password fields
- Long commands with special characters are unreliable

**Better approach:** Push a script to `/sdcard/Download/`, then type `bash /sdcard/Download/s.sh` (short filename). This reliably works.

### 6. pip install --upgrade pip BREAKS Termux

Termux ships its own pip. Upgrading it from PyPI breaks the `python-pip` package. Similarly, packages requiring Rust compilation (cryptography) fail because the Rust target triple `aarch64-unknown-linux-android` isn't supported.

**Fix:** Use `pkg install python-cryptography python-pillow` for native packages. Never upgrade pip itself.

### 7. Ollama Is Now a Termux Package

`pkg install ollama` works as of 2026. No need for manual binary downloads, proot wrappers, or install scripts. The package handles the glibc issue internally.

### 8. Wireless Charging Enables USB OTG + Power

Pixel phones can't simultaneously charge and use USB OTG via a splitter. Wireless charging solves this — charge wirelessly while USB-C is free for the ESP32 OTG connection.

---

## Pitfalls Encountered

1. **Bootstrap script `set -e` + pip errors** — Script died on first pip error. Each fix required push+re-run cycle.
2. **Ollama binary download 404** — Changed from bare binary to `.tar.zst` tarball in recent releases.
3. **Ollama in proot = glibc overhead** — Unnecessary; native `pkg install ollama` works.
4. **Git clone of private repo in Termux** — Needs embedded token in URL; `input text` mangles the URL.
5. **esptool platform detection** — Crashes on import, not on use. Can't even check if flash would work without patching pyserial first.
6. **USBDEVFS ioctl struct sizes** — Different on ARM64 vs x86. USBDEVFS_CONTROL is 0xc0185500 on ARM64 (pointer is 8 bytes).
7. **Multiple Termux processes** — Old sessions persist. `input text` goes to whichever session is active. Use short scripts to avoid confusion.

---

## Wisdom

1. **The last 10% is 90% of the work.** Codegen, build, and vision all worked. USB flash and camera — the physical-world interfaces — are where Android's security model fights you hardest.

2. **Don't fight the platform.** We spent 2 hours trying USBDEVFS ioctls, CDC ACM drivers, URB submissions. The answer was always the same: Play Store Termux doesn't expose this. The fix is architectural (F-Droid Termux or native Flutter app), not technical.

3. **Control transfers are your diagnostic friend.** Even when bulk I/O fails, vendor-specific control transfers let you identify the chip (VID/PID), set baud rate, toggle DTR/RTS. This confirmed the hardware path works — the software sandbox is the blocker.

4. **The phone CAN do everything.** 16GB RAM, Tensor G5 NPU, USB OTG, camera, WiFi ADB. The silicon is capable. It's the software layers (Play Store policies, Android USB stack, Termux sandboxing) that constrain.

5. **Two paths forward, both valid:**
   - **Quick fix:** Replace Play Store Termux with F-Droid Termux. Rebuild environment (~1 hour). Full pipeline works.
   - **Architectural leap:** Build inference into the Flutter app using LiteRT + Tensor G5 NPU. Native USB via usb-serial-for-android. Camera via Flutter camera package. No Termux needed. Harder to build, but eliminates the entire class of sandbox problems.

---

## Architecture: Next-Gen On-Device Vision Loop

The Termux blockers led to a pivot: move inference into a native Flutter app.

### Why Native Flutter Beats Termux

| Capability | Termux | Native Flutter App |
|---|---|---|
| Camera | BLOCKED (Play Store) | `camera` package, full access |
| USB Serial | BLOCKED (Play Store) | `usb-serial-for-android` (Java) |
| NPU/TPU | Not accessible | LiteRT delegates, NNAPI |
| RAM for AI | Shared with Ollama process | Direct memory management |
| Background execution | Screen-off kills BLE scan | Foreground service |

### Proposed Stack

```
Flutter App (beacon_app or new esp-vision-loop app)
├── Vision Pipeline
│   ├── camera package → ImageStream (YUV420)
│   ├── C++ FFI → YUV→RGB conversion (zero-copy)
│   └── tflite_flutter + GpuDelegateV2 → score
├── Codegen Pipeline
│   ├── MediaPipe LLM Inference API (Kotlin)
│   ├── Model: Gemma 2B INT4 or DeepSeek Coder 1.3B INT4
│   └── MethodChannel/EventChannel → Dart
├── Build Pipeline
│   ├── Bundled proot-distro Debian + ESP-IDF (assets or downloaded)
│   └── Process.run("proot-distro login debian -- ninja -C build -j1")
├── Flash Pipeline
│   ├── usb-serial-for-android (Java, UsbManager API)
│   └── esptool protocol implementation or bundled esptool.py
└── Tutor Interface
    ├── Claude Code API (remote) or on-device LLM
    └── Monitors progress, nudges codegen, evaluates vision scores
```

### P10 Resource Reclamation

Before running on-device AI, free resources held by Google's background AI:
1. **Disable AICore** (Settings > Apps > Show system > AICore > Disable + Clear Storage) — frees 5GB+
2. **Disable Gemini** (revert to Assistant or set digital assistant to None)
3. **Disable Circle to Search, Camera AI features, Call Assist**
4. These actions are reversible and don't void warranty

### Tutor Role (Claude Code / This PC)

The tutor (me, running on this PC) can:
- Revise and reflash the **Flutter APK** onto P10
- Monitor P10's progress via WiFi ADB (screenshots, logs)
- Nudge the on-device system via ADB broadcasts or API calls
- CANNOT pass pre-compiled ESP32 firmware — the student must build it on-device

---

## Files Changed This Session

- `codegen/generator.py` — Unicode sanitizer, lower temperature, reduced token limit
- `config/prompts.yaml` — Concrete example pattern, ASCII-only rules, strip-based drawing
- `build/flasher.py` — esptool wrapper for termux-usb fd passthrough (works for control only)
- `run_loop.sh` — USB permission pre-flight before iteration loop
- pyserial `list_ports_posix.py` on P10 — patched for Android platform

---

## What Needs to Happen Next

1. **Decision:** F-Droid Termux swap (quick, proven) vs Flutter+LiteRT app (architectural, ambitious)
2. If F-Droid: `pkg install` script to rebuild environment in ~1 hour
3. If Flutter: Scaffold the app with tflite_flutter, usb-serial-for-android, MediaPipe LLM
4. Either way: download INT4 quantized models for on-device inference
5. Either way: disable AICore + Gemini to free 5GB+ on P10

---

*"The phone has the silicon. The phone has the camera. The phone has the USB. The only thing stopping it is the software we chose to run on it."*
