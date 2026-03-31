#!/system/bin/sh
# On-device ESP32-S3 build script for P9a
# Usage: sh build.sh draw_frame.c
set -e
KIT=/data/local/tmp/p9a-kit
SRC="${1:-draw_frame.c}"
OUT="$KIT/workspace"
mkdir -p "$OUT"

# Toolchain paths
GLIBC="$KIT/glibc"
TC="$KIT/toolchain"
LD_LINUX="$GLIBC/ld-linux-aarch64.so.1"
GCC="$TC/bin/xtensa-esp32s3-elf-gcc"
OBJCOPY="$TC/bin/xtensa-esp32s3-elf-objcopy"

# Wrapper to run glibc binaries on Android's Bionic
run() {
    "$LD_LINUX" --library-path "$GLIBC:$TC/lib:$TC/libexec/gcc/xtensa-esp-elf/13.2.0" "$@"
}

echo "=== Compile: $SRC ==="
run "$GCC" -c -mlongcalls \
    -ffunction-sections -fdata-sections \
    -I"$KIT/include" \
    -I"$TC/xtensa-esp-elf/include" \
    "$OUT/$SRC" -o "$OUT/draw_frame.o"

echo "=== Link ==="
run "$GCC" @"$KIT/link.rsp" "$OUT/draw_frame.o" -o "$OUT/app.elf"

echo "=== Convert ELF to BIN ==="
run "$OBJCOPY" -O binary "$OUT/app.elf" "$OUT/app.bin"

echo "=== Done: $OUT/app.bin ==="
ls -la "$OUT/app.bin"
