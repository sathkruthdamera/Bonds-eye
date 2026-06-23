from __future__ import annotations

import asyncio
import json
import os
import queue
import sqlite3
import threading
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from time import time
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from phase2_scoring_engine import NodeFeature, score_nodes

app = FastAPI(title="Bonds-eye", version="0.3.0")

EXPECTED_NODES = [node.strip() for node in os.getenv("BONDSEYE_EXPECTED_NODES", "esp32s3-node-01,esp32s3-node-02,esp32s3-node-03").split(",") if node.strip()]
API_KEY = os.getenv("BONDSEYE_API_KEY", "dev-change-me")
DB_PATH = Path(os.getenv("BONDSEYE_DB_PATH", "/data/bondseye.sqlite3"))
READING_LIMIT = int(os.getenv("BONDSEYE_READING_LIMIT", "500"))
EVENT_LIMIT = int(os.getenv("BONDSEYE_EVENT_LIMIT", "100"))
NODE_OFFLINE_SECONDS = int(os.getenv("BONDSEYE_NODE_OFFLINE_SECONDS", "20"))
MIN_EVENT_GAP_MS = int(os.getenv("BONDSEYE_MIN_EVENT_GAP_MS", "2500"))
BROADCAST_MIN_INTERVAL_MS = int(os.getenv("BONDSEYE_BROADCAST_MIN_INTERVAL_MS", "150"))
WRITE_QUEUE_MAX = int(os.getenv("BONDSEYE_WRITE_QUEUE_MAX", "10000"))
WRITE_BATCH_MAX = int(os.getenv("BONDSEYE_WRITE_BATCH_MAX", "200"))

readings: deque[dict[str, Any]] = deque(maxlen=READING_LIMIT)
events: deque[dict[str, Any]] = deque(maxlen=EVENT_LIMIT)
clients: set[WebSocket] = set()
node_state: dict[str, dict[str, Any]] = {}
rssi_windows: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=20))
last_sequences: dict[str, int] = {}
last_event_ms = 0
last_broadcast_ms = 0
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


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if API_KEY and API_KEY != "dev-change-me" and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


_db_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL + NORMAL sync keeps high-rate telemetry writes cheap without a new
    # connection per packet (the previous bottleneck).
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS readings (id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT NOT NULL, rssi INTEGER NOT NULL, rssi_variance REAL NOT NULL, csi_variance REAL NOT NULL, packet_loss REAL NOT NULL, sequence INTEGER, timestamp_ms INTEGER NOT NULL, received_at_ms INTEGER NOT NULL)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_node_time ON readings(node_id, received_at_ms)")
    conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, timestamp_ms INTEGER NOT NULL, confidence REAL, payload TEXT)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp_ms)")
    conn.commit()


# One shared connection, initialised at import time so the schema always exists
# (including under the test client, where startup events do not fire).
CONN = _connect()
init_db(CONN)

# Reading writes are pushed onto a queue and flushed in batches by a background
# daemon thread, so the request path never blocks on disk I/O or commit().
_write_queue: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=WRITE_QUEUE_MAX)


def _writer_loop() -> None:
    while True:
        batch = [_write_queue.get()]
        while len(batch) < WRITE_BATCH_MAX:
            try:
                batch.append(_write_queue.get_nowait())
            except queue.Empty:
                break
        rows = [
            (r["node_id"], r["rssi"], r["rssi_variance"], r["csi_variance"], r["packet_loss"], r.get("sequence"), r["timestamp_ms"], r["received_at_ms"])
            for r in batch
        ]
        try:
            with _db_lock:
                CONN.executemany(
                    "INSERT INTO readings(node_id,rssi,rssi_variance,csi_variance,packet_loss,sequence,timestamp_ms,received_at_ms) VALUES(?,?,?,?,?,?,?,?)",
                    rows,
                )
                CONN.commit()
        except Exception:  # pragma: no cover - background writer must not die
            pass


_writer_thread = threading.Thread(target=_writer_loop, name="bondseye-db-writer", daemon=True)
_writer_thread.start()


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


def persist_reading(reading: dict[str, Any]) -> None:
    # Non-blocking: hand off to the background writer. Shed load instead of
    # stalling ingest if the queue is ever saturated.
    try:
        _write_queue.put_nowait(reading)
    except queue.Full:
        pass


def add_event(event: dict[str, Any]) -> None:
    events.append(event)
    with _db_lock:
        CONN.execute("INSERT INTO events(type,timestamp_ms,confidence,payload) VALUES(?,?,?,?)", (event["type"], event["timestamp_ms"], event.get("confidence"), json.dumps(event)))
        CONN.commit()


def process_snapshot() -> dict[str, Any]:
    current_ms = now_ms()
    features: list[NodeFeature] = []
    for node_id, state in node_state.items():
        age_seconds = (current_ms - state["last_seen_ms"]) / 1000
        online = age_seconds <= NODE_OFFLINE_SECONDS
        state["online"] = online
        if online:
            features.append(
                NodeFeature(
                    node_id=node_id,
                    rssi=float(state.get("rssi", -80)),
                    rssi_variance=float(state.get("rssi_variance", 0.0)),
                    csi_variance=float(state.get("csi_variance", 0.0)),
                    packet_loss=float(state.get("packet_loss", 0.0)),
                )
            )

    result = score_nodes(features)
    stick_figure = {
        "mode": result.pose_state.value,
        "zone": result.zone_state.value,
        "x": result.stick_x,
        "y": result.stick_y,
        "motion": result.motion_intensity,
        "confidence": result.confidence,
    }
    return {
        "presence": result.presence,
        "confidence": result.confidence,
        "motion_intensity": result.motion_intensity,
        "signal_disturbance": result.signal_disturbance,
        "pose_state": result.pose_state.value,
        "zone_state": result.zone_state.value,
        "node_count": len(features),
        "nodes": node_state,
        "stick_figure": stick_figure,
        "events": list(events)[-20:],
        "calibration": calibration_state,
        "server_time_ms": current_ms,
    }


async def broadcast(payload: dict[str, Any]) -> None:
    targets = list(clients)
    if not targets:
        return
    results = await asyncio.gather(*(ws.send_json(payload) for ws in targets), return_exceptions=True)
    for websocket, result in zip(targets, results):
        if isinstance(result, Exception):
            clients.discard(websocket)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "nodes": len(node_state), "expected_nodes": len(EXPECTED_NODES), "db_path": str(DB_PATH), "server_time": utc_iso()}


@app.post("/api/telemetry", dependencies=[Depends(require_api_key)])
async def ingest_telemetry(packet: TelemetryIn) -> dict[str, bool]:
    global last_event_ms, last_broadcast_ms
    timestamp_ms = packet.timestamp_ms or now_ms()
    rssi_windows[packet.node_id].append(packet.rssi)
    rssi_variance = packet.rssi_variance if packet.rssi_variance is not None else calculate_variance(rssi_windows[packet.node_id])
    packet_loss = estimate_packet_loss(packet.node_id, packet.sequence, packet.packet_loss)
    normalized = {"node_id": packet.node_id, "rssi": packet.rssi, "rssi_variance": round(rssi_variance, 4), "csi_variance": round(packet.csi_variance or 0.0, 4), "packet_loss": round(packet_loss, 4), "sequence": packet.sequence, "timestamp_ms": timestamp_ms, "received_at_ms": now_ms()}
    readings.append(normalized)
    persist_reading(normalized)
    node_state[packet.node_id] = {**normalized, "last_seen_ms": now_ms(), "online": True, "health": "ok" if packet_loss < 0.15 else "degraded"}
    snapshot = process_snapshot()
    event_added = False
    if snapshot["presence"] and now_ms() - last_event_ms >= MIN_EVENT_GAP_MS:
        last_event_ms = now_ms()
        add_event({"type": "presence_or_motion", "timestamp_ms": last_event_ms, "confidence": snapshot["confidence"]})
        event_added = True
    # Decouple the live fan-out rate from the ingest rate: push on a capped
    # interval, but always push immediately when a presence event fires.
    if event_added or now_ms() - last_broadcast_ms >= BROADCAST_MIN_INTERVAL_MS:
        last_broadcast_ms = now_ms()
        await broadcast({"type": "telemetry", "reading": normalized, "snapshot": snapshot})
    return {"accepted": True}


@app.post("/telemetry", dependencies=[Depends(require_api_key)])
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
    calibration_state.update({"active": True, "mode": request.mode, "duration_seconds": request.duration_seconds, "started_at_ms": now_ms()})
    add_event({"type": "calibration_started", "mode": request.mode, "timestamp_ms": now_ms()})
    return {"started": True, "calibration": calibration_state}


@app.post("/api/calibrate/stop")
def stop_calibration() -> dict[str, Any]:
    calibration_state.update({"active": False, "stopped_at_ms": now_ms()})
    add_event({"type": "calibration_stopped", "timestamp_ms": now_ms()})
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
