# Session Chronicle: Flutter Scaffold Built (Tutor Side)

**Date:** 2026-03-29
**Platform:** WSL2 on Windows (tutor PC), targeting Pixel 9a (P9a)
**Duration:** ~45 minutes (interrupted by OS restart mid-session)
**Outcome:** Full Flutter app scaffold built, analyzer clean, debug APK compiles (141MB)

---

## Original Goal

Execute the `flutter-vision-loop-demo.md` spec via TAC-Autonomous — scaffold the native Flutter app that replaces the Termux+Ollama pipeline with in-app inference via MediaPipe LLM + TFLite vision + USB serial flash.

---

## Milestones Achieved

### 1. Flutter Project Created and Building
- `flutter create --org com.witnessmark --project-name esp_vision_loop`
- 22 source files: 16 Dart, 4 Kotlin, 2 C++
- `flutter analyze` — 0 issues
- `flutter build apk --debug` — 141MB APK at `build/app/outputs/flutter-apk/app-debug.apk`

### 2. Full Architecture Wired
- **6 Dart services**: CodegenService (MethodChannel + EventChannel), VisionService, BuildService (proot-distro Process.run), FlashService, CameraService, SpelunkerService
- **BLoC state machine**: 10-phase loop (idle → spelunk → generate → build → flash → capture → judge → succeed), up to 10 iterations with feedback accumulation
- **4 Kotlin platform services**: LlmInferenceService (stubbed MediaPipe), UsbFlashService (USB device detection for CH343/CH340/CP2102/FTDI), VisionLoopReceiver (ADB broadcast commands), VisionLoopBridge (singleton callback wiring)
- **C++ FFI**: yuv_to_rgb.cpp with NV21/NV12 conversion + nearest-neighbor resize, CMake build config

### 3. Platform Integration Complete
- Android manifest: CAMERA permission, USB host feature, singleTask launch mode, USB_DEVICE_ATTACHED intent, VisionLoopReceiver with 5 ADB actions
- USB device filter XML: CH343 (6790/21971), CH340 (6790/29987), CP2102 (4292/60000), FTDI (1027/24577) — decimal VID/PID
- CMake 3.22.1 (matched to installed Android SDK version)
- minSdk 24 (required for camera + USB host)

### 4. Tutor Interface Ready
ADB broadcast commands for remote control:
```bash
adb shell am broadcast -n com.witnessmark.esp_vision_loop/.VisionLoopReceiver \
    -a com.witnessmark.esp_vision_loop.NUDGE --es feedback "shift circle right"
```
Actions: NUDGE, SET_GOAL, STATUS, PAUSE, RESUME

---

## Lessons Learned

### 1. /tmp Is Volatile on WSL2 — Use Persistent Storage

First attempt built the entire Flutter project in `/tmp/esp_vision_loop_app/`. OS restart wiped everything. Had to rebuild from scratch.

**Rule:** On WSL2, NEVER put generated projects in `/tmp/`. Use `/mnt/c/Users/.../` or `~/` for anything that must survive a reboot. `/tmp` is only for truly ephemeral scratch files.

**Corollary:** The esp-vision-loop repo clone was also in `/tmp/esp-vision-loop/` and got wiped. Re-cloned to `/mnt/c/Users/kpkpk/.cursor/projects/esp-vision-loop/`.

### 2. CMake Version Must Match Android SDK Installation

Build failed immediately with `CMake '3.18.1' was not found`. The build.gradle.kts specified `version = "3.18.1"` but Android SDK had `3.22.1` installed at `$ANDROID_HOME/cmake/3.22.1/`.

**Rule:** Always check `ls $ANDROID_HOME/cmake/` and match the version string exactly. Don't guess CMake versions.

### 3. TAC-Autonomous Can Recover from Total Loss

The session crashed after the first successful build. On resume, discovered `/tmp` was gone. TAC-Autonomous spec says "retry 2x with different approach" — the approach change was using persistent storage. Second attempt succeeded on first try.

**Wisdom:** Idempotent specs are crash-proof. Because the spec fully described the target state (not a sequence of steps), rebuilding from zero produced an identical result. The spec is the recovery plan.

### 4. Parallel Agent Coordination on Shared Files

Three agents wrote to the same project simultaneously. Two agents both modified `build.gradle.kts`. The second agent's write won, but it correctly incorporated both changes (minSdk=24 AND CMake config) because the prompt explicitly warned about the other agent's modifications.

**Rule:** When spawning parallel agents that touch the same file, tell each agent what the other is doing. Explicit coordination beats hoping for merge luck.

### 5. Android SDK minSdk Version Requirements

Camera plugin requires minSdk 21+. USB host features work on minSdk 21+. But the `usb_serial` plugin and some camera features need 24+. Bumping to 24 covers everything with no device compatibility loss (P9a target is Android 15).

**Rule:** For apps targeting modern Pixels, minSdk 24 is the safe floor.

---

## Pitfalls Encountered

1. **Spec file not in expected repo** — `specs/flutter-vision-loop-demo.md` was in esp-vision-loop repo, not WitnessMark. TAC-Autonomous had to search for it.
2. **OS restart between build and deploy** — Lost all work in /tmp. Cost: 45 minutes of agent time to rebuild.
3. **Default Flutter test references deleted class** — `widget_test.dart` still referenced `MyApp` after replacing `main.dart`. Quick fix: replace test with minimal smoke test.
4. **Three parallel agents creating same directory structure** — No conflicts because Dart, Kotlin, and C++ files are in separate directory trees. Good decomposition.

---

## What's Stubbed (Not Yet Functional)

| Component | Status | What's Missing |
|-----------|--------|----------------|
| LLM codegen | Stubbed | Download INT4 model, add MediaPipe dependency, implement inference |
| Vision judge | Stubbed | Download vision model, implement TFLite inference |
| USB flash | Detection works | esptool SLIP protocol not implemented |
| Camera | Wired | Works on device, not testable on WSL2 |
| Build (proot) | Wired | `Process.run('proot-distro')` — only works if Termux proot is accessible from the Flutter app's UID |
| BLoC loop | Complete | All phases wired, needs real service backends |

---

## Wisdom

1. **The scaffold IS the hard part for a multi-platform app.** Getting 22 files across 3 languages (Dart, Kotlin, C++) to compile together with camera, USB, native C++ FFI, and platform channels — that's the integration puzzle. The AI inference is "just" filling in the stub implementations.

2. **Persistent storage is a form of crash resistance.** The first build was technically perfect — analyzer clean, APK built. But it was worthless because it lived in `/tmp`. The second build was identical in every way except location. Location is a design decision, not a deployment detail.

3. **Specs survive what code doesn't.** The spec file in the GitHub repo survived the OS restart. The code it described didn't. That's the value of declarative specs — they're the seed from which the code can be regenerated. TAC-Autonomous regenerated 22 files from a single spec in 10 minutes.

4. **The tutor can build what the student can't (yet).** This session ran on WSL2 with Android SDK, Flutter, Java 17 — a full desktop build environment. The P9a student device can't run Flutter tooling. The tutor's job is to build and deploy the APK; the student's job is to run inference on-device. Clear division of labor.

---

*"The app exists. It compiles. It has a UI, a state machine, platform channels, and a C++ FFI bridge. It just doesn't think yet. That's next."*
