#!/bin/bash
# ELF2Image watcher — replaces tutor tool for the vision loop
# Watches the P9a exchange dir for BUILD_RESULT, pulls ELF, converts to bin, pushes back
#
# Requires: esptool.py (pip install esptool)
# Usage: bash elf2image_watcher.sh

DEVICE="192.168.86.250:46749"
EXCHANGE="/storage/emulated/0/Android/data/com.witnessmark.esp_vision_loop/files/exchange"
TMPDIR="/tmp/elf2image_watcher"
mkdir -p "$TMPDIR"

echo "[elf2image] Watcher started for $DEVICE"
echo "[elf2image] Exchange: $EXCHANGE"

while true; do
    # Check for BUILD_RESULT
    RESULT=$(adb -s "$DEVICE" shell "cat $EXCHANGE/BUILD_RESULT 2>/dev/null" 2>/dev/null)

    if echo "$RESULT" | grep -q '"success":true'; then
        # Check if app.bin already exists (don't redo)
        BINSIZE=$(adb -s "$DEVICE" shell "wc -c < $EXCHANGE/app.bin 2>/dev/null" 2>/dev/null | tr -d ' \r')
        if [ "$BINSIZE" -gt 1000 ] 2>/dev/null; then
            sleep 0.5
            continue
        fi

        echo "[elf2image] BUILD_RESULT found — pulling ELF..."
        adb -s "$DEVICE" pull "$EXCHANGE/app.elf" "$TMPDIR/app.elf" 2>/dev/null

        if [ -f "$TMPDIR/app.elf" ]; then
            echo "[elf2image] Converting ELF → bin..."
            esptool.py --chip esp32s3 elf2image --flash_size 4MB --flash_mode dio "$TMPDIR/app.elf" -o "$TMPDIR/app.bin" 2>&1

            if [ -f "$TMPDIR/app.bin" ] && [ $(wc -c < "$TMPDIR/app.bin") -gt 1000 ]; then
                BINSIZE=$(wc -c < "$TMPDIR/app.bin")
                echo "[elf2image] Pushing app.bin ($BINSIZE bytes)..."
                adb -s "$DEVICE" push "$TMPDIR/app.bin" "$EXCHANGE/app.bin" 2>/dev/null
                echo "[elf2image] Done!"
            else
                echo "[elf2image] Conversion failed"
            fi
            rm -f "$TMPDIR/app.elf" "$TMPDIR/app.bin"
        fi
    fi

    sleep 0.5
done
