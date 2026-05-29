# Gateway packet format

The gateway receives ESP32-S3 telemetry and forwards normalized packets to the Bonds-eye backend.

## Recommended transport

MVP:

- ESP32-S3 to gateway: UDP JSON
- Gateway to backend: HTTP POST
- Backend to mobile: WebSocket

Later optimization:

- ESP32-S3 to gateway: compact binary packet
- Gateway to backend: MQTT or WebSocket

## ESP32 UDP JSON packet

Required fields:

- node_id
- rssi
- sequence

Optional fields:

- rssi_variance
- csi_variance
- packet_loss
- timestamp_ms

Example packet:

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

## Gateway responsibilities

- listen for UDP packets
- validate node_id
- add timestamp when missing
- estimate RSSI variance when missing
- calculate packet loss from sequence gaps
- forward normalized telemetry to backend
- log malformed packets without crashing

## Packet loss calculation

For each node:

- store last sequence number
- compare incoming sequence number
- if sequence jumps, count missing packets
- rolling packet loss window: last 100 packets

## Node naming

Use fixed names:

- esp32s3-node-01
- esp32s3-node-02
- esp32s3-node-03

## Backend endpoint

Gateway forwards to:

```text
POST /api/telemetry
```

## Security later

Before public exposure, add device token validation between gateway and backend.
