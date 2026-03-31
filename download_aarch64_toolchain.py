#!/usr/bin/env python3
"""Download Espressif aarch64-linux Xtensa toolchain for on-device ESP32 compilation."""
import urllib.request
import os
import sys

URL = "https://github.com/espressif/crosstool-NG/releases/download/esp-13.2.0_20240530/xtensa-esp-elf-13.2.0_20240530-aarch64-linux-gnu.tar.xz"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(OUT_DIR, "xtensa-esp-elf-aarch64.tar.xz")

def progress(count, block_size, total_size):
    pct = count * block_size * 100 // total_size if total_size > 0 else 0
    mb = count * block_size / (1024 * 1024)
    total_mb = total_size / (1024 * 1024)
    sys.stdout.write(f"\r  {mb:.1f}/{total_mb:.1f} MB ({pct}%)")
    sys.stdout.flush()

if os.path.exists(OUT_FILE):
    sz = os.path.getsize(OUT_FILE)
    if sz > 100_000_000:
        print(f"Already downloaded: {OUT_FILE} ({sz / 1024 / 1024:.1f} MB)")
        sys.exit(0)
    else:
        print(f"Partial download found ({sz} bytes), re-downloading...")

print(f"Downloading aarch64 Xtensa toolchain...")
print(f"  URL: {URL}")
print(f"  To:  {OUT_FILE}")
urllib.request.urlretrieve(URL, OUT_FILE, progress)
print(f"\nDone: {os.path.getsize(OUT_FILE) / 1024 / 1024:.1f} MB")
