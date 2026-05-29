# Phase 2 WebSocket protocol

Live endpoint: /ws/live

Events endpoint: /ws/events

The mobile app connects to /ws/live for live processed Bonds-eye updates.

Recommended MVP frequency:

- dashboard mode: 1 update per second
- stick figure mode: up to 5 updates per second

Do not stream raw CSI to the mobile app. Stream processed scores only.

Live message fields:

- type
- presence
- confidence
- motion_intensity
- signal_disturbance
- pose_state
- zone_state
- node_count
- stick_figure
- server_time_ms

Stick figure fields:

- mode
- zone
- x
- y
- motion
- confidence

Event message types:

- presence_detected
- presence_cleared
- motion_detected
- node_online
- node_offline
- calibration_started
- calibration_completed

Mobile reconnect policy:

- reconnect after 2 seconds
- then 5 seconds
- then 10 seconds
- show disconnected state after 15 seconds without server data

Security later:

Before public deployment, add token authentication to the WebSocket handshake.
