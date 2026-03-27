#!/bin/bash
# Self-retrying ESP-IDF build — survives OOM kills on ninja
# Ninja is incremental, so each run picks up where the last left off.
# Usage: nohup bash build_retry.sh &

PROJECT="/data/data/com.termux/files/home/esp-vision-loop/esp_project"
LOG="/data/data/com.termux/files/home/esp-vision-loop/logs/build_retry.log"
MAX_ATTEMPTS=10

mkdir -p "$(dirname $LOG)"
pkill -f ollama 2>/dev/null
sleep 2

echo "=== ESP-IDF Build (auto-retry, max $MAX_ATTEMPTS attempts) ===" | tee "$LOG"
echo "$(date)" | tee -a "$LOG"
free -h | tee -a "$LOG"

# Do set-target ONCE (it triggers fullclean)
if [ ! -f "$PROJECT/build/build.ninja" ]; then
    echo "=== First run: setting target ===" | tee -a "$LOG"
    proot-distro login debian -- bash -c "
        cd /root/esp/esp-idf && . ./export.sh 2>/dev/null &&
        cd $PROJECT &&
        idf.py set-target esp32 2>&1
    " >> "$LOG" 2>&1
fi

for attempt in $(seq 1 $MAX_ATTEMPTS); do
    echo "" | tee -a "$LOG"
    echo "=== Attempt $attempt/$MAX_ATTEMPTS — $(date) ===" | tee -a "$LOG"
    free -h | tee -a "$LOG"

    # Just run ninja directly — no set-target, no cmake reconfigure
    proot-distro login debian -- bash -c "
        cd /root/esp/esp-idf && . ./export.sh 2>/dev/null &&
        cd $PROJECT/build &&
        ninja -j1 2>&1
    " >> "$LOG" 2>&1

    RC=$?
    echo "ninja exit code: $RC" | tee -a "$LOG"

    if [ $RC -eq 0 ]; then
        echo "=== BUILD SUCCEEDED on attempt $attempt ===" | tee -a "$LOG"
        echo "$(date)" | tee -a "$LOG"
        free -h | tee -a "$LOG"
        ls -lh "$PROJECT/build/display_demo.elf" 2>/dev/null | tee -a "$LOG"
        ls -lh "$PROJECT/build/display_demo.bin" 2>/dev/null | tee -a "$LOG"
        exit 0
    fi

    echo "ninja failed/killed. Cached objects preserved. Retrying in 5s..." | tee -a "$LOG"
    sleep 5
done

echo "=== GAVE UP after $MAX_ATTEMPTS attempts ===" | tee -a "$LOG"
exit 1
