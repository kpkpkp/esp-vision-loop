#!/data/data/com.termux/files/usr/bin/bash
#
# ESP Vision Loop — One-time environment setup for Termux
#
# Run this once: bash setup.sh
#
set -e

echo "============================================"
echo "  ESP Vision Loop — Environment Setup"
echo "============================================"

# -----------------------------------------------
# 1. System packages
# -----------------------------------------------
echo ""
echo "[1/6] Installing system packages..."
pkg update -y
pkg install -y python git cmake ninja wget clang make termux-api

# -----------------------------------------------
# 2. Python dependencies
# -----------------------------------------------
echo ""
echo "[2/6] Installing Python packages..."
pip install --upgrade pip
pip install pyyaml requests Pillow esptool

# -----------------------------------------------
# 3. Ollama
# -----------------------------------------------
echo ""
echo "[3/6] Installing Ollama..."
if command -v ollama &>/dev/null; then
    echo "  Ollama already installed."
else
    # Ollama provides an install script; try it first.
    # If it fails on Termux, fall back to manual binary download.
    echo "  Attempting Ollama install..."
    if curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null; then
        echo "  Ollama installed via install script."
    else
        echo "  Install script failed. Trying manual ARM64 binary..."
        OLLAMA_VERSION="0.3.12"
        wget -q "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-arm64" \
            -O "$PREFIX/bin/ollama"
        chmod +x "$PREFIX/bin/ollama"
        echo "  Ollama binary installed to $PREFIX/bin/ollama"
    fi
fi

echo ""
echo "  Starting Ollama server in background..."
ollama serve &
OLLAMA_PID=$!
sleep 5

echo "  Pulling vision model (bakllava)..."
ollama pull bakllava

echo "  Pulling coding model (deepseek-coder:6.7b)..."
ollama pull deepseek-coder:6.7b

echo "  Models downloaded. Ollama server running (PID: $OLLAMA_PID)."
echo "  NOTE: You'll need 8GB+ RAM to run these models."

# -----------------------------------------------
# 4. ESP-IDF
# -----------------------------------------------
echo ""
echo "[4/6] Setting up ESP-IDF..."
ESP_DIR="$HOME/esp"
IDF_DIR="$ESP_DIR/esp-idf"

if [ -d "$IDF_DIR" ]; then
    echo "  ESP-IDF already cloned at $IDF_DIR"
else
    mkdir -p "$ESP_DIR"
    echo "  Cloning ESP-IDF v5.2 (this may take a while)..."
    git clone --recursive https://github.com/espressif/esp-idf.git \
        --branch v5.2 --depth 1 "$IDF_DIR"
fi

echo ""
echo "  Installing ESP-IDF tools..."
echo "  IMPORTANT: The default install downloads x86_64 toolchains."
echo "  On ARM64 Termux, you may need to manually install the toolchain."
echo ""
echo "  Attempting standard install (may fail on ARM64)..."
cd "$IDF_DIR"
if ./install.sh esp32 2>/dev/null; then
    echo "  ESP-IDF tools installed successfully."
else
    echo ""
    echo "  *** ESP-IDF standard install failed (expected on ARM64). ***"
    echo ""
    echo "  MANUAL STEP REQUIRED:"
    echo "  1. Download the Xtensa ESP32 toolchain for linux-arm64 from:"
    echo "     https://github.com/espressif/crosstool-NG/releases"
    echo "  2. Extract to ~/.espressif/tools/xtensa-esp32-elf/"
    echo "  3. Then run: source $IDF_DIR/export.sh"
    echo ""
    echo "  Alternative: If your ESP32 is a C3 or S3 (RISC-V mode),"
    echo "  the RISC-V toolchain can be built natively in Termux."
fi

# -----------------------------------------------
# 5. USB setup notes
# -----------------------------------------------
echo ""
echo "[5/6] USB Serial Access Notes"
echo "  On unrooted Android, Termux uses termux-usb for USB access."
echo "  Steps:"
echo "  1. Connect ESP32 via USB-OTG cable"
echo "  2. Run: termux-usb -l              (list devices)"
echo "  3. Run: termux-usb -r <device>     (request permission)"
echo "  4. Grant USB permission in the Android dialog"
echo ""
echo "  The orchestrator handles this automatically via build/flasher.py."

# -----------------------------------------------
# 6. Project scaffold verification
# -----------------------------------------------
echo ""
echo "[6/6] Verifying project structure..."
PROJECT="$HOME/esp-vision-loop"
for dir in config codegen/templates build capture/photos vision esp_project/main logs; do
    mkdir -p "$PROJECT/$dir"
done
echo "  Project structure OK at $PROJECT"

# -----------------------------------------------
# Done
# -----------------------------------------------
echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "Before running the orchestrator, source ESP-IDF:"
echo "  source ~/esp/esp-idf/export.sh"
echo ""
echo "Ensure Ollama is running:"
echo "  ollama serve &"
echo ""
echo "Then run:"
echo "  cd ~/esp-vision-loop"
echo "  python3 orchestrator.py --goal 'draw a red circle centered on screen'"
echo ""
echo "For a dry run (no hardware needed):"
echo "  python3 orchestrator.py --goal 'draw a red circle' --dry-run"
echo ""
