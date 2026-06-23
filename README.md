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
- Abstract stick-figure avatar (pose state + zone state, RF-derived — not a real skeleton)
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

## Local testing without hardware

You can exercise the full pipeline (simulated nodes -> gateway -> API -> mobile)
with no ESP32 boards using the node simulator.

```bash
# terminal 1: API
cd api && uvicorn main:app --port 8080

# terminal 2: gateway (relays UDP -> API)
cd gateway && python udp_gateway.py --api-url http://127.0.0.1:8080/api/telemetry

# terminal 3: simulate the 3 nodes (rotates pose/zone states)
cd gateway && python simulator.py --scenario cycle
```

The simulator can also POST straight to the API, skipping the gateway:

```bash
python simulator.py --api-url http://127.0.0.1:8080/api/telemetry --api-key dev-change-me
```

Scenarios: `empty` (NO_PERSON), `still` (STANDING_STILL), `walking` (MOVING),
`crouch` (CROUCH_LIKE), and `cycle` (rotates them and sweeps zones). Use
`--sweep` with a fixed scenario to move the active node across LEFT/CENTER/RIGHT.

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

The Phase-2 scoring engine is now wired into the live API: each snapshot emits
`pose_state`, `zone_state`, and a `stick_figure` object, and the mobile app
renders the avatar. The pose/zone thresholds in `api/phase2_scoring_engine.py`
are heuristic and should be calibrated in your real room.
