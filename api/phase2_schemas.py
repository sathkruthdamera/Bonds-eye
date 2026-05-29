from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


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


class TelemetryPacket(BaseModel):
    node_id: str = Field(..., description="ESP32-S3 node id")
    rssi: float = Field(..., description="Current RSSI value")
    rssi_variance: float = 0.0
    csi_variance: float = 0.0
    packet_loss: float = 0.0
    sequence: int = 0
    timestamp_ms: int | None = None


class NodeState(BaseModel):
    node_id: str
    rssi: float
    rssi_variance: float
    csi_variance: float
    packet_loss: float
    sequence: int
    status: str
    last_seen_ms: int


class StickFigure(BaseModel):
    mode: PoseState
    zone: ZoneState
    x: float
    y: float
    motion: float
    confidence: float


class LiveSnapshot(BaseModel):
    presence: bool
    confidence: float
    motion_intensity: float
    signal_disturbance: float
    pose_state: PoseState
    zone_state: ZoneState
    node_count: int
    nodes: list[NodeState]
    stick_figure: StickFigure
    events: list[dict[str, Any]]
    server_time_ms: int
