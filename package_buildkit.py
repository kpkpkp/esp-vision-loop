#!/usr/bin/env python3
"""
Package the ESP32-S3 build kit for on-device compilation on P9a.

Creates: p9a-buildkit/ with:
  toolchain/  — aarch64 xtensa-esp-elf-gcc + libexec + internal libs
  glibc/      — ld-linux-aarch64.so.1 + minimal glibc from toolchain sysroot
  libs/       — all .a files from ESP-IDF build
  ld/         — linker scripts
  include/    — draw_api.h (minimal header for LLM code)
  boot/       — bootloader.bin, partition-table.bin
  obj/        — project_elf_src_esp32s3.c.obj (ESP-IDF boilerplate)
  link.rsp    — response file for linker (@link.rsp)
  build.sh    — on-device build script
"""
import os
import shutil
import subprocess
import tarfile
import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(SCRIPT_DIR, "esp_project", "build")
KIT_DIR = os.path.join(SCRIPT_DIR, "p9a-buildkit")
TOOLCHAIN_TAR = os.path.join(SCRIPT_DIR, "xtensa-esp-elf-aarch64.tar.xz")
IDF_PATH = os.path.expanduser("~/esp/esp-idf")

def clean():
    if os.path.exists(KIT_DIR):
        shutil.rmtree(KIT_DIR)
    os.makedirs(KIT_DIR)

def extract_toolchain():
    """Extract the full aarch64 toolchain, then copy needed parts."""
    print("Extracting aarch64 toolchain (full extract)...")
    tc_dir = os.path.join(KIT_DIR, "toolchain")
    tmp_dir = os.path.join(SCRIPT_DIR, "_tc_tmp")

    # Full extraction to temp dir
    if not os.path.exists(tmp_dir):
        with tarfile.open(TOOLCHAIN_TAR, "r:xz") as tar:
            tar.extractall(tmp_dir)

    # Find the root dir inside the tarball
    entries = os.listdir(tmp_dir)
    tc_root = os.path.join(tmp_dir, entries[0]) if len(entries) == 1 else tmp_dir

    # Copy the needed parts
    needed_dirs = [
        "bin",
        "libexec/gcc/xtensa-esp-elf/13.2.0",
        "lib/gcc/xtensa-esp-elf/13.2.0",
        "xtensa-esp-elf/lib/esp32s3",
        "xtensa-esp-elf/include",
    ]

    os.makedirs(tc_dir, exist_ok=True)
    for d in needed_dirs:
        src = os.path.join(tc_root, d)
        dst = os.path.join(tc_dir, d)
        if os.path.exists(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst, symlinks=False)  # resolve symlinks

    # Also copy xtensa-esp-elf/lib root .a files (libnosys, libc, libm, etc.)
    elf_lib_src = os.path.join(tc_root, "xtensa-esp-elf", "lib")
    elf_lib_dst = os.path.join(tc_dir, "xtensa-esp-elf", "lib")
    os.makedirs(elf_lib_dst, exist_ok=True)
    for f in os.listdir(elf_lib_src):
        fp = os.path.join(elf_lib_src, f)
        if os.path.isfile(fp):
            shutil.copy2(fp, elf_lib_dst)

    file_count = sum(len(files) for _, _, files in os.walk(tc_dir))
    print(f"  Copied {file_count} files to {tc_dir}")

def collect_libs():
    """Collect all .a library files from the ESP-IDF build."""
    print("Collecting library archives...")
    libs_dir = os.path.join(KIT_DIR, "libs")
    os.makedirs(libs_dir, exist_ok=True)

    count = 0
    # Libraries from build/esp-idf/*/
    for lib_path in glob.glob(os.path.join(BUILD_DIR, "esp-idf", "*", "*.a")):
        shutil.copy2(lib_path, libs_dir)
        count += 1

    # Nested libs (mbedtls/mbedtls/library/, 3rdparty/)
    for lib_path in glob.glob(os.path.join(BUILD_DIR, "esp-idf", "*", "*", "*", "*.a")):
        shutil.copy2(lib_path, libs_dir)
        count += 1
    for lib_path in glob.glob(os.path.join(BUILD_DIR, "esp-idf", "*", "*", "*", "*", "*.a")):
        shutil.copy2(lib_path, libs_dir)
        count += 1

    # WiFi/BT/PHY/Coex binary blobs from ESP-IDF
    for pattern in ["esp_wifi/lib/esp32s3/*.a", "esp_phy/lib/esp32s3/*.a",
                     "esp_coex/lib/esp32s3/*.a", "bt/controller/lib_esp32c3_family/esp32s3/*.a"]:
        for lib_path in glob.glob(os.path.join(IDF_PATH, "components", pattern)):
            shutil.copy2(lib_path, libs_dir)
            count += 1

    # libxt_hal.a
    xt_hal = os.path.join(IDF_PATH, "components/xtensa/esp32s3/libxt_hal.a")
    if os.path.exists(xt_hal):
        shutil.copy2(xt_hal, libs_dir)
        count += 1

    print(f"  Collected {count} libraries")

def collect_linker_scripts():
    """Collect all linker scripts needed for the final link."""
    print("Collecting linker scripts...")
    ld_dir = os.path.join(KIT_DIR, "ld")
    os.makedirs(ld_dir, exist_ok=True)

    # Generated scripts from build
    for ld in ["memory.ld", "sections.ld"]:
        src = os.path.join(BUILD_DIR, "esp-idf", "esp_system", "ld", ld)
        if os.path.exists(src):
            shutil.copy2(src, ld_dir)

    # __ldgen_output_sections.ld
    ldgen = os.path.join(BUILD_DIR, "esp-idf", "esp_system", "__ldgen_output_sections.ld")
    if os.path.exists(ldgen):
        shutil.copy2(ldgen, ld_dir)

    # ROM linker scripts from ESP-IDF
    rom_ld_dir = os.path.join(IDF_PATH, "components/esp_rom/esp32s3/ld")
    for ld in os.listdir(rom_ld_dir):
        if ld.endswith(".ld"):
            shutil.copy2(os.path.join(rom_ld_dir, ld), ld_dir)

    # SoC peripherals
    soc_ld = os.path.join(IDF_PATH, "components/soc/esp32s3/ld/esp32s3.peripherals.ld")
    if os.path.exists(soc_ld):
        shutil.copy2(soc_ld, ld_dir)

    print(f"  Collected {len(os.listdir(ld_dir))} linker scripts")

def collect_boot():
    """Copy bootloader and partition table."""
    print("Collecting boot binaries...")
    boot_dir = os.path.join(KIT_DIR, "boot")
    os.makedirs(boot_dir, exist_ok=True)

    shutil.copy2(os.path.join(BUILD_DIR, "bootloader", "bootloader.bin"), boot_dir)
    shutil.copy2(os.path.join(BUILD_DIR, "partition_table", "partition-table.bin"), boot_dir)

def collect_obj():
    """Copy the project ELF source object (ESP-IDF boilerplate)."""
    print("Collecting object files...")
    obj_dir = os.path.join(KIT_DIR, "obj")
    os.makedirs(obj_dir, exist_ok=True)

    proj_obj = os.path.join(BUILD_DIR, "CMakeFiles", "display_demo.elf.dir", "project_elf_src_esp32s3.c.obj")
    if os.path.exists(proj_obj):
        shutil.copy2(proj_obj, obj_dir)

def collect_headers():
    """Copy the minimal draw_api.h."""
    print("Collecting headers...")
    inc_dir = os.path.join(KIT_DIR, "include")
    os.makedirs(inc_dir, exist_ok=True)
    shutil.copy2(os.path.join(SCRIPT_DIR, "esp_project", "main", "draw_api.h"), inc_dir)

def create_link_response_file():
    """Create the linker response file with all flags."""
    print("Creating link response file...")
    # Absolute device paths so build_server.sh works from any cwd
    R = "/data/local/tmp/p9a-kit/p9a-buildkit"
    lines = [
        "-mlongcalls",
        "-fno-builtin-memcpy -fno-builtin-memset -fno-builtin-bzero -fno-builtin-stpcpy -fno-builtin-strncpy",
        "-Wl,--cref",
        "-Wl,--defsym=IDF_TARGET_ESP32S3=0",
        "-Wl,--no-warn-rwx-segments",
        "-fno-rtti -fno-lto",
        "-Wl,--gc-sections",
        "-Wl,--warn-common",
        # Linker scripts
        f"-T {R}/ld/esp32s3.peripherals.ld",
        f"-T {R}/ld/esp32s3.rom.ld",
        f"-T {R}/ld/esp32s3.rom.api.ld",
        f"-T {R}/ld/esp32s3.rom.bt_funcs.ld",
        f"-T {R}/ld/esp32s3.rom.libgcc.ld",
        f"-T {R}/ld/esp32s3.rom.wdt.ld",
        f"-T {R}/ld/esp32s3.rom.version.ld",
        f"-T {R}/ld/esp32s3.rom.newlib.ld",
        f"-T {R}/ld/memory.ld",
        f"-T {R}/ld/sections.ld",
        # Object files
        f"{R}/obj/project_elf_src_esp32s3.c.obj",
        # Library search path
        f"-L{R}/libs",
    ]

    # Extract exact link order from build.ninja (ESP-IDF's multi-pass resolution)
    import re
    ninja_path = os.path.join(BUILD_DIR, "build.ninja")
    with open(ninja_path) as f:
        ninja_text = f.read()
    m = re.search(r'LINK_LIBRARIES = (.+)', ninja_text)
    if not m:
        raise RuntimeError("Could not find LINK_LIBRARIES in build.ninja")

    for token in m.group(1).split():
        token = token.strip()
        if not token:
            continue
        if token.startswith('-'):
            # Flags: -u, -Wl, -l, etc. — pass through
            lines.append(token)
        elif token.endswith('.a'):
            # Library path — convert to -l with our libs dir
            name = os.path.basename(token)
            if name.startswith('lib') and name.endswith('.a'):
                lines.append(f"-l{name[3:-2]}")
            else:
                lines.append(f"{R}/libs/{name}")
        else:
            lines.append(token)

    # Ensure gcc/stdc++ at end
    if "-lgcc" not in lines:
        lines.append("-lgcc")

    rsp_path = os.path.join(KIT_DIR, "link.rsp")
    with open(rsp_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Written {len(lines)} lines to link.rsp")

def create_build_script():
    """Create the on-device build script."""
    print("Creating build script...")
    script = r"""#!/system/bin/sh
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
"""
    script_path = os.path.join(KIT_DIR, "build.sh")
    with open(script_path, "w") as f:
        f.write(script)
    os.chmod(script_path, 0o755)

def report_size():
    """Report total size of the build kit."""
    total = 0
    for dirpath, _, filenames in os.walk(KIT_DIR):
        for f in filenames:
            total += os.path.getsize(os.path.join(dirpath, f))
    print(f"\nBuild kit total: {total / 1024 / 1024:.1f} MB")

    # Breakdown by directory
    for d in sorted(os.listdir(KIT_DIR)):
        dp = os.path.join(KIT_DIR, d)
        if os.path.isdir(dp):
            sz = sum(os.path.getsize(os.path.join(dirpath, f))
                     for dirpath, _, filenames in os.walk(dp) for f in filenames)
            print(f"  {d}/: {sz / 1024 / 1024:.1f} MB")

if __name__ == "__main__":
    clean()
    extract_toolchain()
    collect_libs()
    collect_linker_scripts()
    collect_boot()
    collect_obj()
    collect_headers()
    create_link_response_file()
    create_build_script()
    report_size()
    print("\nDone! Next: push p9a-buildkit/ to device via ADB")
