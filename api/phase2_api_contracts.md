# Phase 2 API contracts

## GET /health

Returns backend health.

Response:

```json
{
  "status": "ok",
  "nodes": 3
}
```

## POST /api/telemetry

Receives telemetry from the gateway or ESP32 node.

Request:

```json
{
  "node_id": "esp32s3-node-01",
  "rssi": -58,
  "rssi_variance": 0.12,
  "csi_variance": 0.18,
  "packet_loss": 0.01,
  "sequence": 1042,
  "timestamp_ms": 1710000000000
}
```

Response:

```json
{
  "accepted": true
}
```

## GET /api/latest

Returns latest processed live snapshot.

Response fields:

- presence
- confidence
- motion_intensity
- signal_disturbance
- pose_state
- zone_state
- node_count
- nodes
- stick_figure
- events
- server_time_ms

## GET /api/nodes

Returns node health and latest signal values.

## GET /api/events

Returns recent event timeline.

## POST /api/calibrate/start

Starts calibration mode.

Request:

```json
{
  "mode": "EMPTY_ROOM",
  "duration_seconds": 60
}
```

Supported modes:

- EMPTY_ROOM
- PERSON_STILL
- PERSON_WALKING

## POST /api/calibrate/stop

Stops calibration and stores threshold suggestions.
