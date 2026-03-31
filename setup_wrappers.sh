#!/system/bin/sh
# Create glibc wrapper scripts for Xtensa toolchain on Android
# Run on P9a: sh /data/local/tmp/setup_wrappers.sh

KIT="/data/local/tmp/p9a-kit/p9a-buildkit"
GLIBC="$KIT/glibc"
LD="$GLIBC/ld-linux-aarch64.so.1"
LIB_PATH="$GLIBC"

# Ensure ld-linux is executable
chmod +x "$LD"

# Helper: create a wrapper that invokes a binary through ld-linux
make_wrapper() {
    REAL="$1"
    if [ ! -f "$REAL" ] && [ ! -f "${REAL}.real" ]; then
        echo "SKIP: $REAL (not found)"
        return
    fi
    # Move original to .real if not already done
    if [ -f "$REAL" ] && [ ! -f "${REAL}.real" ]; then
        mv "$REAL" "${REAL}.real"
    fi
    # Write wrapper script
    printf '#!/system/bin/sh\nexec %s --library-path %s %s.real "$@"\n' "$LD" "$LIB_PATH" "$REAL" > "$REAL"
    chmod +x "$REAL"
    echo "OK: $REAL"
}

# Wrap all binaries in toolchain/bin/
for TOOL in xtensa-esp-elf-gcc xtensa-esp-elf-gcc-13.2.0 xtensa-esp-elf-g++ xtensa-esp-elf-c++ xtensa-esp-elf-as xtensa-esp-elf-ld xtensa-esp-elf-objcopy xtensa-esp-elf-ar xtensa-esp-elf-cpp; do
    make_wrapper "$KIT/toolchain/bin/$TOOL"
done

# Wrap binaries in libexec (cc1, collect2, lto1, lto-wrapper)
LIBEXEC="$KIT/toolchain/libexec/gcc/xtensa-esp-elf/13.2.0"
for TOOL in cc1 collect2 lto1 lto-wrapper; do
    make_wrapper "$LIBEXEC/$TOOL"
done

echo "Done. Test: $KIT/toolchain/bin/xtensa-esp-elf-gcc --version"
