# ESP Vision Loop — Flutter Demo Spec

## Overview

A Flutter app that runs on Pixel 10 Pro and autonomously:
1. Generates ESP-IDF C code via on-device LLM
2. Builds it via embedded proot-distro
3. Flashes it to an attached ESP32 via USB OTG
4. Photographs the ESP32's display via the phone's camera
5. Judges the result via on-device vision model
6. Iterates until success

A remote **tutor** (Claude Code on PC) monitors via WiFi ADB, can revise and redeploy the APK, and nudge the student — but CANNOT pass compiled firmware. The student must build on-device.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Flutter App: esp_vision_loop                        │
│                                                      │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐            │
│  │ Codegen  │→│  Build   │→│  Flash   │             │
│  │ (LLM)   │  │ (proot)  │  │ (USB)    │             │
│  └────┬────┘  └─────────┘  └──────────┘             │
│       │                          │                    │
│       │    ┌──────────┐          │                    │
│       └────│  Judge   │←─────────┘                    │
│            │ (Vision) │    ┌──────────┐              │
│            └────┬─────┘    │ Camera   │              │
│                 │          └──────────┘              │
│                 ↓                                     │
│         score >= 7? → SUCCESS                        │
│         score < 7?  → iterate with feedback          │
│                                                      │
│  ┌──────────────────────────────────────┐            │
│  │ Tutor Interface (ADB broadcast rx)   │            │
│  │ - Receive nudges from remote Claude  │            │
│  │ - Report progress via broadcast/log  │            │
│  └──────────────────────────────────────┘            │
└──────────────────────────────────────────────────────┘
         ↕ WiFi ADB                    ↕ USB OTG
    ┌─────────┐                  ┌──────────┐
    │ Tutor   │                  │  ESP32   │
    │ (PC)    │                  │ Display  │
    └─────────┘                  └──────────┘
```

## Components

### 1. Codegen — On-Device LLM

**Package:** MediaPipe LLM Inference API via Kotlin MethodChannel

**Model options (ranked by feasibility on 16GB device):**
| Model | Size (INT4) | Quality | Speed (est.) |
|---|---|---|---|
| Gemma 2B IT | ~1.5GB | Good for structured code | ~30 tok/s |
| DeepSeek Coder 1.3B | ~0.8GB | Purpose-built for code | ~50 tok/s |
| Phi-3 Mini 3.8B | ~2.2GB | Strong reasoning | ~20 tok/s |
| CodeGemma 2B | ~1.5GB | Code-specific Gemma | ~30 tok/s |

**Implementation:**
```kotlin
// Kotlin side: LlmInferenceService.kt
class LlmInferenceService {
    private var llmInference: LlmInference? = null

    fun initialize(modelPath: String) {
        val options = LlmInference.LlmInferenceOptions.builder()
            .setModelPath(modelPath)
            .setMaxTokens(2048)
            .setTemperature(0.1f)
            .setTopK(40)
            .build()
        llmInference = LlmInference.createFromOptions(context, options)
    }

    fun generate(prompt: String, callback: (String) -> Unit) {
        llmInference?.generateResponseAsync(prompt) { partial, done ->
            callback(partial)
        }
    }
}
```

```dart
// Dart side: codegen_service.dart
class CodegenService {
  static const _channel = MethodChannel('esp_vision_loop/llm');
  static const _eventChannel = EventChannel('esp_vision_loop/llm_stream');

  Future<void> initialize(String modelPath) async {
    await _channel.invokeMethod('initialize', {'modelPath': modelPath});
  }

  Stream<String> generate(String prompt) {
    _channel.invokeMethod('generate', {'prompt': prompt});
    return _eventChannel.receiveBroadcastStream().cast<String>();
  }
}
```

### 2. Vision — On-Device Photo Judge

**Package:** `tflite_flutter` with NPU delegate

**Model options:**
| Model | Size | Capability | Notes |
|---|---|---|---|
| moondream2 (INT4) | ~1GB | General VQA | Best for "does this match the goal?" |
| PaLI-3 (INT4) | ~1.5GB | Image+text | Google's, good Tensor support |
| BLIP-2 (INT4) | ~1.2GB | Image captioning | Describe what's on display |
| Custom classifier | ~5MB | Binary yes/no | Fine-tuned on display photos |

**Camera pipeline:**
```
CameraController.startImageStream()
    → YUV420 bytes
    → C++ FFI (yuv_to_rgb.cpp) — zero-copy conversion
    → Uint8List RGB buffer
    → tflite_flutter Interpreter.run()
    → [score, description]
```

**C++ FFI bridge (yuv_to_rgb.cpp):**
```cpp
#include <cstdint>

extern "C" {

void yuv420_to_rgb(
    const uint8_t* y_plane, int y_stride,
    const uint8_t* u_plane, int u_stride,
    const uint8_t* v_plane, int v_stride,
    uint8_t* rgb_out,
    int width, int height
) {
    for (int j = 0; j < height; j++) {
        for (int i = 0; i < width; i++) {
            int y_val = y_plane[j * y_stride + i];
            int u_val = u_plane[(j/2) * u_stride + (i/2)] - 128;
            int v_val = v_plane[(j/2) * v_stride + (i/2)] - 128;

            int r = y_val + (int)(1.402f * v_val);
            int g = y_val - (int)(0.344f * u_val + 0.714f * v_val);
            int b = y_val + (int)(1.772f * u_val);

            int idx = (j * width + i) * 3;
            rgb_out[idx]     = r < 0 ? 0 : (r > 255 ? 255 : r);
            rgb_out[idx + 1] = g < 0 ? 0 : (g > 255 ? 255 : g);
            rgb_out[idx + 2] = b < 0 ? 0 : (b > 255 ? 255 : b);
        }
    }
}

} // extern "C"
```

### 3. Build — proot-distro ESP-IDF

**Strategy:** Shell out from Flutter via `Process.run()`.

```dart
class BuildService {
  Future<BuildResult> build(String mainCCode, String projectDir) async {
    // Write generated code
    await File('$projectDir/main/main.c').writeAsString(mainCCode);

    // Build via proot (ninja only rebuilds main.c — ~2-5 min)
    final result = await Process.run('proot-distro', [
      'login', 'debian', '--',
      'bash', '-c',
      'source ~/esp/esp-idf/export.sh && cd $projectDir && ninja -C build -j1'
    ]);

    return BuildResult(
      success: result.exitCode == 0,
      output: result.stdout + result.stderr,
    );
  }
}
```

**Prerequisite:** proot-distro Debian with ESP-IDF must be pre-installed in Termux's filesystem (shared with the Flutter app's process).

**Problem:** Flutter apps run as their own UID, not Termux's. They can't access Termux's proot.

**Solution options:**
1. Bundle a minimal proot+toolchain in the app's assets (~500MB compressed)
2. Use Termux as a build service — Flutter app sends code via localhost socket, Termux builds and returns binary path
3. Run build commands via `Runtime.getRuntime().exec()` in Kotlin, accessing a shared filesystem

**Recommended: Option 2 (Termux as build service).** Keep Termux for what it's good at (proot, ESP-IDF) and use the Flutter app for everything else (camera, USB, AI inference).

### 4. Flash — USB Serial via Android API

**Package:** `usb_serial` (Dart) or `usb-serial-for-android` (Java via MethodChannel)

```kotlin
// Kotlin: UsbFlashService.kt
class UsbFlashService(private val context: Context) {
    private var connection: UsbDeviceConnection? = null
    private var serialPort: UsbSerialPort? = null

    fun connect(): Boolean {
        val manager = context.getSystemService(USB_SERVICE) as UsbManager
        val device = manager.deviceList.values.firstOrNull {
            it.vendorId == 0x1a86 && it.productId == 0x55d3 // CH343
        } ?: return false

        connection = manager.openDevice(device)
        val driver = CdcAcmSerialDriver(device)
        serialPort = driver.ports[0]
        serialPort?.open(connection)
        serialPort?.setParameters(460800, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE)
        return true
    }

    fun flash(binaryPath: String): Boolean {
        // Use esptool protocol or bundled esptool.py
        // DTR/RTS toggle to enter download mode
        serialPort?.dtr = false  // Reset
        serialPort?.rts = false  // GPIO0 low
        Thread.sleep(100)
        serialPort?.dtr = true   // Release reset
        Thread.sleep(50)
        serialPort?.rts = true   // Release GPIO0

        // Send SYNC, then flash binary via SLIP protocol
        // ... (esptool protocol implementation)
    }
}
```

### 5. Tutor Interface — ADB Broadcast Receiver

The tutor (Claude Code on PC) communicates via ADB broadcasts:

```kotlin
// Already exists in beacon_app: AdbCommandReceiver pattern
class VisionLoopReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            "NUDGE" -> {
                val feedback = intent.getStringExtra("feedback")
                // Inject feedback into next codegen iteration
            }
            "SET_GOAL" -> {
                val goal = intent.getStringExtra("goal")
                // Change the drawing goal
            }
            "STATUS" -> {
                // Broadcast current state back via logcat
            }
            "PAUSE" -> { /* pause the loop */ }
            "RESUME" -> { /* resume the loop */ }
        }
    }
}
```

Tutor sends commands:
```bash
adb -s P10 shell am broadcast -n com.witnessmark.esp_vision_loop/.VisionLoopReceiver \
    -a NUDGE --es feedback "The circle is off-center, shift x by +20"
```

### 6. Spelunking — USB Device Discovery

Borrow from beacon_app's BLE scanning pattern. When an unknown ESP32 is connected:

1. Read USB VID/PID to identify the USB-serial chip (CH340, CP2102, FTDI, CH343)
2. Enter ESP32 download mode (DTR/RTS toggle)
3. Use esptool SYNC to identify the chip variant (ESP32, ESP32-S2, ESP32-S3, ESP32-C3)
4. Read flash size, MAC address, chip features
5. Query any existing firmware's version string

```dart
class DeviceSpelunker {
  Future<EspDeviceInfo> identify(UsbSerialPort port) async {
    await enterDownloadMode(port);
    final chipId = await readChipId(port);
    final flashSize = await readFlashSize(port);
    final mac = await readMac(port);
    return EspDeviceInfo(chip: chipId, flash: flashSize, mac: mac);
  }
}
```

## P10 Resource Reclamation

Before running on-device AI, free resources:

```bash
# Disable AICore (frees 5GB+ storage + background RAM)
adb shell pm disable-user com.google.android.aicore
adb shell pm clear com.google.android.aicore

# Disable Gemini
adb shell pm disable-user com.google.android.apps.bard

# Disable Circle to Search
adb shell settings put secure assist_gesture_enabled 0

# Disable Camera AI features
# (Must be done in Camera app settings manually)

# Verify
adb shell pm list packages -d | grep -i "ai\|gemini\|bard"
```

## App Structure

```
esp_vision_loop/
├── android/
│   └── app/src/main/kotlin/
│       ├── LlmInferenceService.kt     # MediaPipe LLM
│       ├── UsbFlashService.kt         # USB serial flash
│       ├── VisionLoopReceiver.kt      # ADB command receiver
│       └── MainActivity.kt
├── lib/
│   ├── main.dart
│   ├── services/
│   │   ├── codegen_service.dart        # LLM code generation
│   │   ├── vision_service.dart         # TFLite photo judgment
│   │   ├── build_service.dart          # proot ESP-IDF build
│   │   ├── flash_service.dart          # USB serial flash
│   │   ├── camera_service.dart         # Camera capture
│   │   └── spelunker_service.dart      # USB device discovery
│   ├── models/
│   │   ├── iteration.dart              # Iteration state/log
│   │   ├── esp_device_info.dart        # Discovered device info
│   │   └── build_result.dart
│   ├── ui/
│   │   ├── loop_screen.dart            # Main loop progress UI
│   │   ├── camera_preview.dart         # Live camera feed
│   │   └── code_viewer.dart            # Generated code display
│   └── bloc/
│       ├── vision_loop_bloc.dart       # Main state machine
│       └── vision_loop_event.dart
├── assets/
│   ├── models/
│   │   ├── codegen.tflite              # Quantized coding model
│   │   └── vision.tflite               # Quantized vision model
│   └── prompts/
│       └── prompts.yaml
├── cpp/
│   └── yuv_to_rgb.cpp                  # FFI bridge
└── pubspec.yaml
```

## Dependencies

```yaml
dependencies:
  camera: ^0.11.0
  tflite_flutter: ^0.10.0
  ffi: ^2.1.0
  usb_serial: ^0.5.0        # or platform channel to usb-serial-for-android
  yaml: ^3.1.0
  path_provider: ^2.1.0
  flutter_bloc: ^8.1.0

dev_dependencies:
  ffigen: ^11.0.0            # Generate FFI bindings from yuv_to_rgb.cpp
```

## Tutor Rules

1. Tutor MAY revise and reflash the **Flutter APK** onto P10
2. Tutor MAY send nudges via ADB broadcast (feedback, goal changes, pause/resume)
3. Tutor MAY monitor via WiFi ADB (screenshots, logcat, file pulls)
4. Tutor MAY NOT pass compiled ESP32 firmware to the student
5. Tutor MAY NOT directly write to the ESP32's flash
6. Student MUST build firmware on-device (proot + ESP-IDF)
7. Student MUST flash firmware on-device (USB OTG)
8. Only ONE instance of the app may run — use `singleTask` launch mode

## Anti-Patterns to Avoid

- Multiple APK instances: Use `android:launchMode="singleTask"` in manifest
- Ollama alongside Flutter: Don't run both — they'll OOM fight. All inference in-app.
- Cloud API fallback: Defeats the purpose. All inference on-device.
- Desktop esptool: The whole point is on-device autonomy.

## MVP Milestone

Get a single iteration working:
1. Hardcoded goal ("draw a red circle")
2. Codegen via smallest model (DeepSeek Coder 1.3B INT4)
3. Skip build (use pre-built binary initially)
4. Flash via USB serial
5. Camera capture
6. Vision judgment (even a simple "is the display on?" classifier)
7. Log result

Then iterate on each component.
