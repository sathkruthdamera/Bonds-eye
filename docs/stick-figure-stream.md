# Stick figure stream design

Bonds-eye streams an abstract stick figure state from RF activity. This is not true DensePose and not exact body tracking.

## Purpose

The mobile app uses signal features to show a simple visual state:

- no person
- standing still
- moving
- crouch-like activity
- left zone activity
- center zone activity
- right zone activity

## Backend output contract

The live WebSocket payload should include these fields:

```json
{
  "presence": true,
  "confidence": 0.72,
  "motion_intensity": 0.44,
  "signal_disturbance": 0.39,
  "pose_state": "MOVING",
  "zone_state": "CENTER_ZONE",
  "stick_figure": {
    "mode": "MOVING",
    "x": 0.5,
    "y": 0.5,
    "motion": 0.44
  }
}
```

## Pose state rules

Initial MVP rules:

- confidence below threshold: NO_PERSON
- high motion: MOVING
- low motion and presence true: STANDING_STILL
- high disturbance with low RSSI delta: CROUCH_LIKE
- strongest disturbance on node 1: LEFT_ZONE
- strongest disturbance on node 2: CENTER_ZONE
- strongest disturbance on node 3: RIGHT_ZONE

These are heuristic states and must be calibrated in the real room.

## Mobile rendering

The mobile app should draw a stick figure using simple line segments.

State examples:

- NO_PERSON: dim outline
- STANDING_STILL: centered standing figure
- MOVING: animated arm/leg offset
- CROUCH_LIKE: shorter torso and bent legs
- LEFT_ZONE: figure shifted left
- RIGHT_ZONE: figure shifted right

## Safe interpretation

The figure represents RF activity and approximate zone, not a verified human skeleton.
