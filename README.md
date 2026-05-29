# Bonds-eye

Bonds-eye is a lightweight ESP32-S3 WiFi sensing MVP for live presence, motion intensity, signal disturbance, node health, RSSI/CSI variance, event alerts, and confidence scoring.

This project intentionally removes vitals, breathing, heart-rate, and skeleton/pose claims. It focuses on practical telemetry from 3 ESP32-S3 nodes through a T-Mobile hotspot into a Docker backend and mobile app.

## Target architecture

```text
ESP32-S3 Node 1  \
ESP32-S3 Node 2   ---> T-Mobile Hotspot ---> Local Gateway ---> Hostinger KVM Docker ---> Mobile App
ESP32-S3 Node 3  /
```

## What this MVP provides

- Live presence
- Motion intensity
- Signal disturbance
- Node health
- RSSI/CSI variance
- Event alerts
- Confidence score
- WebSocket live feed for mobile
- Docker-ready backend for Hostinger KVM
- ESP32-S3 firmware template
- React Native / Expo mobile app scaffold

## Repo layout

```text
api/                  FastAPI cloud backend
firmware/esp32-s3/    ESP32-S3 firmware template
mobile/               React Native Expo mobile app
gateway/              Optional local UDP-to-cloud gateway
deploy/               Docker Compose and Nginx config
docs/                 Setup, calibration, bottlenecks, deployment notes
```

## Fast start on Hostinger KVM

```bash
git clone https://github.com/sathkruthdamera/Bonds-eye.git
cd Bonds-eye/deploy
cp .env.example .env
nano .env
docker compose up -d --build
```

Then check:

```bash
curl http://YOUR_SERVER_IP:8080/health
```

## ESP32-S3 target behavior

Each ESP32-S3 connects to the T-Mobile hotspot, samples RSSI/CSI features, and sends compact telemetry packets to either:

1. the local gateway over UDP, recommended, or
2. the cloud backend if direct UDP/TCP works from the hotspot.

## Mobile live feed

The mobile app connects to:

```text
ws://YOUR_SERVER_IP:8080/ws/live
```

For production, put Nginx + TLS in front and use:

```text
wss://your-domain.com/ws/live
```

## Status

This is a configured MVP scaffold. Hardware-specific CSI extraction may require adjustment based on your exact ESP32-S3 board, ESP-IDF version, and antenna behavior.
