#!/bin/bash
# Tutor-side elf2image loop
# Watches for new app.elf from the build server, converts to .bin, pushes back
# Run on PC: bash tutor_elf2image.sh

P9A="192.168.86.250:46749"
EXCHANGE="/storage/emulated/0/Android/data/com.witnessmark.esp_vision_loop/files/exchange"
IDF_EXPORT="source /home/kpkpk/esp/esp-idf/export.sh 2>/dev/null"

eval $IDF_EXPORT

echo "Tutor elf2image loop starting..."
echo "Watching $EXCHANGE/app.elf on P9a"

LAST_SIZE=0
while true; do
    # Check if app.elf changed
    SIZE=$(adb -s $P9A shell "stat -c %s $EXCHANGE/app.elf 2>/dev/null" 2>/dev/null | tr -d '\r')
    if [ -n "$SIZE" ] && [ "$SIZE" != "$LAST_SIZE" ] && [ "$SIZE" -gt 0 ] 2>/dev/null; then
        echo "$(date +%H:%M:%S) New ELF detected: $SIZE bytes"
        LAST_SIZE=$SIZE

        # Pull ELF
        adb -s $P9A pull "$EXCHANGE/app.elf" /tmp/tutor_app.elf 2>/dev/null

        # Convert with esptool
        esptool.py --chip esp32s3 elf2image \
            --flash_mode dio --flash_size 4MB --flash_freq 80m \
            -o /tmp/tutor_app.bin /tmp/tutor_app.elf 2>/dev/null

        if [ $? -eq 0 ]; then
            BIN_SIZE=$(stat -c %s /tmp/tutor_app.bin)
            echo "$(date +%H:%M:%S) Converted: $BIN_SIZE bytes"

            # Push back
            adb -s $P9A push /tmp/tutor_app.bin "$EXCHANGE/app.bin" 2>/dev/null
            echo "$(date +%H:%M:%S) Pushed app.bin"
        else
            echo "$(date +%H:%M:%S) elf2image FAILED"
        fi
    fi
    sleep 1
done
