import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "gateway"))
sys.path.insert(0, str(ROOT / "api"))

import simulator
import udp_gateway
from phase2_scoring_engine import NodeFeature, PoseState, ZoneState, score_nodes

NODES = simulator.DEFAULT_NODES
ALLOWED = set(NODES)


def _packets(scenario: str, active_index: int, seed: int = 1):
    rng = random.Random(seed)
    return [
        simulator.build_packet(node, scenario, sequence=i + 1, active=(i == active_index), rng=rng)
        for i, node in enumerate(NODES)
    ]


def test_packets_pass_gateway_validation():
    for scenario in simulator.SCENARIOS:
        for packet in _packets(scenario, active_index=1):
            valid, reason = udp_gateway.validate_packet(packet, ALLOWED)
            assert valid, f"{scenario}: {reason}"
            assert -120 <= packet["rssi"] <= 0
            assert isinstance(packet["rssi"], int)


def _score(scenario: str, active_index: int):
    features = [
        NodeFeature(
            node_id=p["node_id"],
            rssi=float(p["rssi"]),
            rssi_variance=float(p["rssi_variance"]),
            csi_variance=float(p["csi_variance"]),
        )
        for p in _packets(scenario, active_index)
    ]
    return score_nodes(features)


def test_scenarios_drive_expected_pose():
    assert _score("empty", 1).pose_state == PoseState.NO_PERSON
    assert _score("still", 1).pose_state == PoseState.STANDING_STILL
    assert _score("walking", 1).pose_state == PoseState.MOVING
    assert _score("crouch", 1).pose_state == PoseState.CROUCH_LIKE


def test_active_node_sets_zone():
    # active node index 1 -> esp32s3-node-02 -> CENTER zone (when present).
    assert _score("walking", 1).zone_state == ZoneState.CENTER_ZONE
    assert _score("walking", 0).zone_state == ZoneState.LEFT_ZONE
    assert _score("walking", 2).zone_state == ZoneState.RIGHT_ZONE
