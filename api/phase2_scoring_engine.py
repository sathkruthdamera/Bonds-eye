from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PoseState(str, Enum):
    UNKNOWN = "UNKNOWN"
    NO_PERSON = "NO_PERSON"
    STANDING_STILL = "STANDING_STILL"
    MOVING = "MOVING"
    CROUCH_LIKE = "CROUCH_LIKE"


class ZoneState(str, Enum):
    UNKNOWN = "UNKNOWN"
    LEFT_ZONE = "LEFT_ZONE"
    CENTER_ZONE = "CENTER_ZONE"
    RIGHT_ZONE = "RIGHT_ZONE"


@dataclass
class NodeFeature:
    node_id: str
    rssi: float
    rssi_variance: float = 0.0
    csi_variance: float = 0.0
    packet_loss: float = 0.0


@dataclass
class ScoreResult:
    presence: bool
    confidence: float
    motion_intensity: float
    signal_disturbance: float
    pose_state: PoseState
    zone_state: ZoneState
    stick_x: float
    stick_y: float


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def estimate_zone(nodes: list[NodeFeature]) -> ZoneState:
    if not nodes:
        return ZoneState.UNKNOWN
    strongest = max(nodes, key=lambda n: n.rssi_variance + n.csi_variance)
    if strongest.node_id.endswith("01"):
        return ZoneState.LEFT_ZONE
    if strongest.node_id.endswith("02"):
        return ZoneState.CENTER_ZONE
    if strongest.node_id.endswith("03"):
        return ZoneState.RIGHT_ZONE
    return ZoneState.UNKNOWN


def zone_to_x(zone: ZoneState) -> float:
    if zone == ZoneState.LEFT_ZONE:
        return 0.25
    if zone == ZoneState.RIGHT_ZONE:
        return 0.75
    return 0.50


def score_nodes(nodes: list[NodeFeature]) -> ScoreResult:
    if not nodes:
        return ScoreResult(False, 0.0, 0.0, 0.0, PoseState.NO_PERSON, ZoneState.UNKNOWN, 0.5, 0.5)

    usable = [n for n in nodes if n.packet_loss < 0.35]
    if not usable:
        return ScoreResult(False, 0.0, 0.0, 0.0, PoseState.UNKNOWN, ZoneState.UNKNOWN, 0.5, 0.5)

    motion = clamp(sum(n.rssi_variance + n.csi_variance for n in usable) / len(usable))
    disturbance = clamp(sum(abs(n.rssi + 55.0) / 50.0 + n.csi_variance for n in usable) / len(usable))
    node_quality = clamp(len(usable) / 3.0)
    confidence = clamp((motion * 0.55) + (disturbance * 0.35) + (node_quality * 0.10))
    presence = confidence >= 0.58 or motion >= 0.35 or disturbance >= 0.30

    if not presence:
        pose = PoseState.NO_PERSON
    elif motion >= 0.55:
        pose = PoseState.MOVING
    elif disturbance >= 0.50 and motion < 0.25:
        pose = PoseState.CROUCH_LIKE
    else:
        pose = PoseState.STANDING_STILL

    zone = estimate_zone(usable) if presence else ZoneState.UNKNOWN
    return ScoreResult(presence, round(confidence, 3), round(motion, 3), round(disturbance, 3), pose, zone, zone_to_x(zone), 0.5)
