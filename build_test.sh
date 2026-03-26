#!/bin/bash
# Standalone ESP-IDF build test — run OUTSIDE Claude Code to avoid OOM
# Usage: bash build_test.sh
#
# Ninja is incremental — re-run after OOM to continue from where it stopped.
# Kill Ollama and other heavy processes before running.

PROJECT="/data/data/com.termux/files/home/esp-vision-loop/esp_project"
LOG="/data/data/com.termux/files/home/esp-vision-loop/logs/build_test.log"
mkdir -p "$(dirname $LOG)"

echo "=== ESP-IDF Build Test ===" | tee "$LOG"
echo "$(date)" | tee -a "$LOG"

# Kill Ollama to free RAM
pkill -f ollama 2>/dev/null
sleep 2

echo "Memory before build:" | tee -a "$LOG"
free -h | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "Starting proot build (j1, incremental)..." | tee -a "$LOG"

proot-distro login debian -- bash -c "
cd /root/esp/esp-idf && . ./export.sh 2>/dev/null &&
cd $PROJECT &&
idf.py set-target esp32 2>&1 &&
echo '=== BUILDING (j1) ===' &&
ninja -C build -j1 2>&1
" 2>&1 | tee -a "$LOG"

RC=${PIPESTATUS[0]}
echo "" | tee -a "$LOG"
echo "=== Build exit code: $RC ===" | tee -a "$LOG"
echo "$(date)" | tee -a "$LOG"
free -h | tee -a "$LOG"

if [ $RC -eq 0 ]; then
    echo "=== BUILD SUCCEEDED ===" | tee -a "$LOG"
    ls -lh "$PROJECT/build/display_demo.bin" 2>/dev/null | tee -a "$LOG"
    ls -lh "$PROJECT/build/display_demo.elf" 2>/dev/null | tee -a "$LOG"
else
    echo "=== BUILD FAILED (rc=$RC) — re-run to continue ===" | tee -a "$LOG"
fi
