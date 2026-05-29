# Deployment Checklist

## API
- Set BONDSEYE_API_KEY
- Verify SQLite volume mounted
- Verify /health endpoint

## Gateway
- Verify UDP port 45454 reachable
- Verify packets reach /api/telemetry

## ESP32 Nodes
- Unique node IDs
- Hotspot connectivity
- RSSI telemetry observed

## Mobile
- WebSocket URL configured
- Live feed connected
- Node cards updating

## Security
- Change default API key
- Restrict inbound firewall rules
