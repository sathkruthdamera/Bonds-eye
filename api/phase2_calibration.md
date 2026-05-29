# Phase 2 calibration guide

Calibration is required because RSSI and CSI behavior changes by room, wall material, furniture, node placement, and hotspot position.

## Node placement

Recommended 3-node placement:

- esp32s3-node-01: left side of the sensing area
- esp32s3-node-02: center or opposite side
- esp32s3-node-03: right side of the sensing area

Keep the hotspot and all ESP32 nodes fixed during calibration.

## Calibration stages

### Stage 1: Empty room

Duration: 60 seconds

Purpose:

- capture baseline RSSI
- capture baseline RSSI variance
- capture baseline CSI variance
- measure packet loss

### Stage 2: Person still

Duration: 60 seconds

Purpose:

- learn stationary presence signature
- tune presence confidence threshold

### Stage 3: Person walking

Duration: 60 seconds

Purpose:

- learn motion signature
- tune motion intensity threshold
- tune zone estimator behavior

## Threshold outputs

Calibration should produce:

- baseline_rssi_by_node
- baseline_rssi_variance_by_node
- baseline_csi_variance_by_node
- presence_threshold
- motion_threshold
- disturbance_threshold
- node_packet_loss_warning_threshold

## MVP defaults

Use these defaults until real calibration data is collected:

- presence_threshold: 0.58
- motion_threshold: 0.35
- disturbance_threshold: 0.30
- node_timeout_seconds: 15
- max_packet_loss_for_active_node: 0.35

## Validation checklist

After calibration:

- each node reports online
- packet loss is under 10 percent when close to hotspot
- empty room confidence stays below presence threshold
- walking increases motion intensity
- left, center, and right movement changes zone state

## Recalibration triggers

Recalibrate when:

- ESP32 node placement changes
- hotspot location changes
- room layout changes significantly
- walls or large furniture are added
- confidence becomes unstable
