#!/system/bin/sh
# ESP32-S3 Build Server — file-based IPC
# Polls for build requests, compiles, writes result.
#
# Protocol:
#   App writes: /data/local/tmp/p9a-kit/exchange/draw_frame.c
#   App writes: /data/local/tmp/p9a-kit/exchange/BUILD_REQUEST (trigger)
#   Server reads draw_frame.c, compiles+links
#   Server writes: /data/local/tmp/p9a-kit/exchange/BUILD_RESULT (JSON)
#   Server writes: /data/local/tmp/p9a-kit/exchange/app.elf (if success)
#   App reads BUILD_RESULT, reads app.elf
#
# Start: adb shell "nohup sh /data/local/tmp/build_server.sh > /data/local/tmp/build_server.log 2>&1 &"

KIT="/data/local/tmp/p9a-kit/p9a-buildkit"
# The exchange dir is the app's external files directory (accessible to shell)
EXCHANGE="/storage/emulated/0/Android/data/com.witnessmark.esp_vision_loop/files/exchange"
GCC="$KIT/toolchain/bin/xtensa-esp-elf-gcc"
GPP="$KIT/toolchain/bin/xtensa-esp-elf-g++"
DYNCONFIG="-mdynconfig=xtensa_esp32s3.so"

export LD_LIBRARY_PATH="$KIT/glibc:$KIT/toolchain/lib"
export PATH="$KIT/toolchain/bin:$PATH"

mkdir -p "$EXCHANGE"
chmod 777 "$EXCHANGE"

log() { echo "$(date '+%H:%M:%S') $1"; }

log "Build server starting (file-based IPC)"
log "Exchange dir: $EXCHANGE"

# Verify toolchain
$GCC --version > /dev/null 2>&1
if [ $? -ne 0 ]; then
    log "ERROR: gcc not working"
    exit 1
fi
log "GCC OK — polling for BUILD_REQUEST..."

while true; do
    if [ -f "$EXCHANGE/BUILD_REQUEST" ]; then
        rm -f "$EXCHANGE/BUILD_REQUEST"
        rm -f "$EXCHANGE/BUILD_RESULT"

        if [ ! -f "$EXCHANGE/draw_frame.c" ]; then
            log "ERROR: draw_frame.c not found"
            echo '{"success":false,"stage":"setup","output":"draw_frame.c not found"}' > "$EXCHANGE/BUILD_RESULT"
            continue
        fi

        SRC_SIZE=$(wc -c < "$EXCHANGE/draw_frame.c")
        log "Build request: $SRC_SIZE bytes"

        # Compile
        log "Compiling..."
        COMPILE_OUT=$($GCC $DYNCONFIG -c -mlongcalls \
            -ffunction-sections -fdata-sections \
            -B"$KIT/toolchain/bin/xtensa-esp-elf-" \
            -I"$KIT/include" \
            -I"$KIT/toolchain/xtensa-esp-elf/include" \
            "$EXCHANGE/draw_frame.c" -o "$EXCHANGE/draw_frame.o" 2>&1)
        COMPILE_EXIT=$?

        if [ $COMPILE_EXIT -ne 0 ]; then
            log "Compile FAILED ($COMPILE_EXIT): $COMPILE_OUT"
            SAFE_OUT=$(echo "$COMPILE_OUT" | head -5 | tr '"' "'" | tr '\n' '|')
            echo "{\"success\":false,\"stage\":\"compile\",\"exit\":$COMPILE_EXIT,\"output\":\"$SAFE_OUT\"}" > "$EXCHANGE/BUILD_RESULT"
            continue
        fi
        log "Compile OK"

        # Link
        log "Linking..."
        LINK_OUT=$($GPP $DYNCONFIG \
            -B"$KIT/toolchain/bin/xtensa-esp-elf-" \
            @"$KIT/link.rsp" \
            "$EXCHANGE/draw_frame.o" \
            -o "$EXCHANGE/app.elf" 2>&1)
        LINK_EXIT=$?

        if [ $LINK_EXIT -ne 0 ]; then
            log "Link FAILED ($LINK_EXIT)"
            SAFE_OUT=$(echo "$LINK_OUT" | tail -3 | tr '"' "'" | tr '\n' '|')
            echo "{\"success\":false,\"stage\":\"link\",\"exit\":$LINK_EXIT,\"output\":\"$SAFE_OUT\"}" > "$EXCHANGE/BUILD_RESULT"
            continue
        fi

        ELF_SIZE=$(wc -c < "$EXCHANGE/app.elf")
        log "Build OK: app.elf = $ELF_SIZE bytes"

        # Create merged binary: prepend bootloader + partition table
        # The tutor's elf2image loop produces app.bin from app.elf
        # We also prepare a merge script that the tutor can use
        echo "{\"success\":true,\"elfPath\":\"$EXCHANGE/app.elf\",\"elfSize\":$ELF_SIZE}" > "$EXCHANGE/BUILD_RESULT"
    fi
    sleep 0.3
done
