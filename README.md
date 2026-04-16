# esp-vision-loop

An ESP32-based vision processing system with autonomous code generation and on-device model coaching. The pipeline captures images, runs vision analysis, generates firmware code improvements, builds them, and deploys via OTA — with minimal human intervention.

## Overview

esp-vision-loop targets the Pixel 9a (8GB, Tensor G4) as an edge compute host. It uses Ollama for local model inference, orchestrates capture-analyze-generate-build-deploy cycles, and maintains chronicles of each iteration for debugging and model improvement.

Built using [TAC (Tactical Agentic Coding)](https://github.com/kpkpkp) methodology with Claude as co-developer.

## Architecture

```
orchestrator.py
├── capture/        → camera image acquisition
├── vision/         → image analysis and model coaching
├── codegen/        → autonomous C/C++ code generation
├── build/          → cross-compilation (ESP-IDF toolchain)
├── esp_project/    → ESP32 firmware source
├── p9a-buildkit/   → on-device build toolchain for Pixel 9a
├── chronicles/     → iteration logs and model feedback
├── config/         → pipeline configuration
├── logs/           → build and runtime logs
└── specs/          → architecture documentation
```

`orchestrator.py` manages the full pipeline: capture → analyze → generate → build → flash → evaluate → iterate.

## Key Details

- **Local inference** via Ollama — no cloud dependency for vision analysis
- **Build server architecture** — cross-compiles ESP-IDF firmware on the mobile device
- **On-device model coaching** — vision model improves through iterative feedback loops
- **OTA deployment** — built firmware is flashed to ESP32 targets over-the-air
- **Chronicle system** — each iteration is logged for reproducibility and debugging

## Tech Stack

- **C++** (84%) / **C** (14%) — ESP32 firmware and vision processing
- **Python** — Orchestrator, codegen pipeline, analysis scripts
- **Shell** — Build automation, toolchain setup
- **ESP-IDF** — Espressif IoT Development Framework
- **Ollama** — Local LLM inference

## Companion App

[esp-vision-loop-app](https://github.com/kpkpkp) (Kotlin, private) — Android companion app for camera control and pipeline management.

## Part of WitnessMark

This project is part of the broader [WitnessMark](https://github.com/kpkpkp) ecosystem. The vision loop enables autonomous calibration and quality verification for WitnessMark reflector displays.
