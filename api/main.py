from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from time import time
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

app = FastAPI(title="Bonds-eye", version="0.2.0")

EXPECTED_NODES = ["esp32s3-node-01", "esp32s3-node-02", "esp32s3-node-03"]
READING_LIMIT = 500
EVENT_LIMIT = 100
NODE_OFFLINE_SECONDS = 20

readings: deque[dict[str, Any]] = deque(maxlen=READING_LIMIT)
events: deque[dict[str, Any]] = deque(maxlen=EVENT_LIMIT)
clients: set[WebSocket] = set()
node_state: dict[str, dict[str, Any]] = {}
rssi_windows: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=20))
last_sequences: dict[str, int] = {}
calibration_state: dict[str, Any] = {"active": False, "mode": None, "started_at_ms": None}


class TelemetryIn(BaseModel):
    node_id: str = Field(..., examples=["esp32s3-node-01"])
    rssi: int = Field(..., ge=-120, le=0)
    rssi_variance: float | None = Field(default=None, ge=0)
    csi_variance: float | None = Field(default=None, ge=0)
    packet_loss: float | None = Field(default=None, ge=0, le=1)
    sequence: int | None = Field(default=None, ge=0)
    timestamp_ms: int | None = Field(default=None, ge=0)


class CalibrationStart(BaseModel):
    mode: str = Field(..., pattern="^(EMPTY_ROOM|PERSON_STILL|PERSON_WALKING)$")
    duration_seconds: int = Field(default=60, ge=5, le=600)


def now_ms() -> int:
    return int(time() * 1000)


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def calculate_variance(values: deque[int]) -> float:
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    return sum((value - avg) ** 2 for value in values) / len(values)


def estimate_packet_loss(node_id: str, sequence: int | None, provided: float | None) -> float:
    if provided is not None:
        return provided
    if sequence is None:
        return 0.0
    previous = last_sequences.get(node_id)
    last_sequences[node_id] = sequence
    if previous is None or sequence <= previous + 1:
        return 0.0
    missing = sequence - previous - 1
    return min(missing / max(sequence - previous, 1), 1.0)


def process_snapshot() -> dict[str, Any]:
    active_nodes = []
    signal_disturbance = 0.0
    motion_intensity = 0.0
    current_ms = now_ms()

    for node_id, state in node_state.items():
        age_seconds = (current_ms - state["last_seen_ms"]) / 1000
        online = age_seconds <= NODE_OFFLINE_SECONDS
        state["online"] = online
        if online:
            active_nodes.append(node_id)
            signal_disturbance += float(state.get("rssi_variance", 0)) + float(state.get("csi_variance", 0))
            motion_intensity += max(0, min(100, abs(state.get("rssi", -80) + 70) * 2))

    node_count = len(active_nodes)
    normalized_disturbance = round(signal_disturbance / max(node_count, 1), 3)
    normalized_motion = round(motion_intensity / max(node_count, 1), 2)
    confidence = round(min(1.0, 0.25 + (node_count / max(len(EXPECTED_NODES), 1)) * 0.55 + min(normalized_disturbance / 20, 0.2)), 3)
    presence = node_count > 0 and (normalized_disturbance > 1.5 or normalized_motion > 8)

    return {
        "presence": presence,
        "confidence": confidence,
        "motion_intensity": normalized_motion,
        "signal_disturbance": normalized_disturbance,
        "pose_state": "not_supported_mvp",
        "zone_state": "unknown",
        "node_count": node_count,
        "nodes": node_state,
        "stick_figure": None,
        "events": list(events)[-20:],
        "calibration": calibration_state,
        "server_time_ms": current_ms,
    }


async def broadcast(payload: dict[str, Any]) -> None:
    disconnected = []
    for websocket in clients:
        try:
            await websocket.send_json(payload)
        except Exception:
            disconnected.append(websocket)
    for websocket in disconnected:
        clients.discard(websocket)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "nodes": len(node_state),
        "expected_nodes": len(EXPECTED_NODES),
        "server_time": utc_iso(),
    }


@app.post("/api/telemetry")
async def ingest_telemetry(packet: TelemetryIn) -> dict[str, bool]:
    timestamp_ms = packet.timestamp_ms or now_ms()
    rssi_windows[packet.node_id].append(packet.rssi)
    rssi_variance = packet.rssi_variance if packet.rssi_variance is not None else calculate_variance(rssi_windows[packet.node_id])
    packet_loss = estimate_packet_loss(packet.node_id, packet.sequence, packet.packet_loss)

    normalized = {
        "node_id": packet.node_id,
        "rssi": packet.rssi,
        "rssi_variance": round(rssi_variance, 4),
        "csi_variance": round(packet.csi_variance or 0.0, 4),
        "packet_loss": round(packet_loss, 4),
        "sequence": packet.sequence,
        "timestamp_ms": timestamp_ms,
        "received_at_ms": now_ms(),
    }
    readings.append(normalized)
    node_state[packet.node_id] = {
        **normalized,
        "last_seen_ms": now_ms(),
        "online": True,
        "health": "ok" if packet_loss < 0.15 else "degraded",
    }

    snapshot = process_snapshot()
    if snapshot["presence"]:
        events.append({"type": "presence_or_motion", "timestamp_ms": now_ms(), "confidence": snapshot["confidence"]})

    await broadcast({"type": "telemetry", "reading": normalized, "snapshot": snapshot})
    return {"accepted": True}


@app.post("/telemetry")
async def legacy_ingest(packet: TelemetryIn) -> dict[str, bool]:
    return await ingest_telemetry(packet)


@app.get("/api/latest")
def latest() -> dict[str, Any]:
    return process_snapshot()


@app.get("/api/nodes")
def nodes() -> dict[str, Any]:
    process_snapshot()
    return {"nodes": node_state, "expected_nodes": EXPECTED_NODES}


@app.get("/api/events")
def recent_events() -> dict[str, Any]:
    return {"events": list(events)}


@app.get("/readings/recent")
def recent_readings() -> list[dict[str, Any]]:
    return list(readings)[-100:]


@app.post("/api/calibrate/start")
def start_calibration(request: CalibrationStart) -> dict[str, Any]:
    calibration_state.update({
        "active": True,
        "mode": request.mode,
        "duration_seconds": request.duration_seconds,
        "started_at_ms": now_ms(),
    })
    events.append({"type": "calibration_started", "mode": request.mode, "timestamp_ms": now_ms()})
    return {"started": True, "calibration": calibration_state}


@app.post("/api/calibrate/stop")
def stop_calibration() -> dict[str, Any]:
    calibration_state.update({"active": False, "stopped_at_ms": now_ms()})
    events.append({"type": "calibration_stopped", "timestamp_ms": now_ms()})
    return {"stopped": True, "calibration": calibration_state}


@app.websocket("/ws/live")
async def live(websocket: WebSocket) -> None:
    await websocket.accept()
    clients.add(websocket)
    await websocket.send_json({"type": "snapshot", "snapshot": process_snapshot()})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.discard(websocket)
