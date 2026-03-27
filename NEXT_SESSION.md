# Next Session Prompt

Paste this to start the next session:

---

Resume work on ~/esp-vision-loop — an autonomous code-see-judge-improve loop that generates ESP-IDF C code to draw shapes on an ESP32 display, builds it, flashes it, photographs the result, and judges it with a local vision model.

## Where we left off

The architecture was overhauled to split display init (hand-written, display_init.h) from drawing logic (LLM-generated). A test script was prepared but not yet run due to RAM constraints (Ollama + Claude Code can't coexist).

## First thing to do

1. Read `logs/codegen_build_test.log` — this is the output of `test_codegen_and_build.sh` which I ran after the last session. It tests whether the new split-architecture prompt produces compilable code.
2. Read `esp_project/main/main.c` — this is whatever the coding model generated.
3. Check `logs/` for any other new files.
4. Based on the results:
   - If the build succeeded: move to flashing. The ESP32 is connected via USB-OTG.
   - If the build failed with errors: analyze the errors, improve the prompt or display_init.h, and iterate.

## Key context

- Platform: Termux on Android (Play Store build, CLAUDE_CODE_TMPDIR=~/tmp)
- ESP-IDF builds via proot-distro Debian (Xtensa toolchain needs glibc)
- Ollama runs locally: bakllava (vision), deepseek-coder:6.7b (coding)
- Ollama and builds can't run simultaneously (OOM). Orchestrator manages lifecycle.
- Camera: termux-camera-photo blocked (Play Store). Using Android intent or manual file drop.
- USB: use termux-usb for serial access (no root)
- Build: ninja -j1 inside proot. Only main.c recompiles (seconds). Don't re-run set-target.
- Repo: github.com/kpkpkp/esp-vision-loop (private)
- Chronicles in chronicles/ document lessons learned across sessions

## Files to read first

```
logs/codegen_build_test.log    # Output of the test script
esp_project/main/main.c        # LLM-generated code
esp_project/main/display_init.h # Hand-written display init (don't modify)
config/prompts.yaml            # Current prompt templates
config/device.yaml             # Hardware config
build/builder.py               # Build pipeline (proot + ninja)
orchestrator.py                # Main loop
chronicles/                    # Session history
```
