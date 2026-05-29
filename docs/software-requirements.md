# Bonds-eye software requirements

## Development machine: Windows

Install these tools on Windows:

1. Git for Windows
2. Python 3.12 or newer
3. Node.js LTS
4. Docker Desktop
5. Visual Studio Code
6. ESP-IDF Windows installer from Espressif
7. ESP-IDF VS Code extension, optional
8. CP210x or CH340 USB serial driver, depending on the ESP32-S3 board USB chip
9. Expo Go mobile app for quick mobile testing

## Firmware toolchain

Recommended firmware stack:

- ESP-IDF
- Target: esp32s3
- Language: C
- Transport: UDP JSON first, binary CSI packet later
- Serial monitor: ESP-IDF PowerShell

## Backend stack

- Python
- FastAPI
- Uvicorn
- WebSocket live feed
- Docker container
- Optional PostgreSQL later

## Gateway stack

- Python UDP listener
- HTTP relay to cloud API
- Simulator mode for testing without ESP32 boards

## Mobile stack

- React Native
- Expo
- WebSocket client
- Stick avatar visualization

## Hostinger KVM 2 runtime

Current placeholder:

- IP: 31.220.48.185
- RAM: 2 GB
- Storage: 100 GB
- Domain: pending

Keep the first deployment lightweight. Avoid heavy ML models until raw ESP32 data quality is validated.

## Official references

- ESP-IDF Windows setup: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/get-started/windows-setup.html
- Expo setup: https://docs.expo.dev/get-started/set-up-your-environment/
- Docker Ubuntu install: https://docs.docker.com/engine/install/ubuntu/
