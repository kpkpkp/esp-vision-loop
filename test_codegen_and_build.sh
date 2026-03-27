#!/bin/bash
# Test the new split architecture: codegen (drawing only) + build
# Run OUTSIDE Claude Code to have enough RAM for Ollama.
# Usage: bash test_codegen_and_build.sh

set -e
cd ~/esp-vision-loop

LOG="logs/codegen_build_test.log"
mkdir -p logs

echo "=== Codegen + Build Test ===" | tee "$LOG"
echo "$(date)" | tee -a "$LOG"
free -h | tee -a "$LOG"

# Step 1: Start Ollama and generate code
echo "" | tee -a "$LOG"
echo "=== Step 1: Code Generation ===" | tee -a "$LOG"
pkill -f ollama 2>/dev/null; sleep 2
ollama serve &>/dev/null &
sleep 5

python3 -c "
import yaml
from codegen.generator import generate_code

config = yaml.safe_load(open('config/device.yaml'))
prompts = yaml.safe_load(open('config/prompts.yaml'))

code = generate_code(
    config=config,
    goal='draw a red filled circle centered on screen',
    previous_code=None,
    vision_feedback=None,
    prompts=prompts,
)

# Write to main.c
with open('esp_project/main/main.c', 'w') as f:
    f.write(code)
print(f'Generated {len(code.splitlines())} lines')
print('--- CODE ---')
print(code)
" 2>&1 | tee -a "$LOG"

# Step 2: Stop Ollama, run build
echo "" | tee -a "$LOG"
echo "=== Step 2: Build ===" | tee -a "$LOG"
pkill -f ollama 2>/dev/null; sleep 2
free -h | tee -a "$LOG"

proot-distro login debian -- bash -c "
cd /root/esp/esp-idf && . ./export.sh 2>/dev/null &&
cd /data/data/com.termux/files/home/esp-vision-loop/esp_project/build &&
ninja -j1 2>&1
" 2>&1 | tee -a "$LOG"

RC=${PIPESTATUS[0]}
echo "" | tee -a "$LOG"
echo "=== Build exit code: $RC ===" | tee -a "$LOG"
echo "$(date)" | tee -a "$LOG"

if [ $RC -eq 0 ]; then
    echo "=== SUCCESS: Code compiles! ===" | tee -a "$LOG"
else
    echo "=== Build failed — check errors above ===" | tee -a "$LOG"
fi
