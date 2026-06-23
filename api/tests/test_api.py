import os
import sys
from pathlib import Path

os.environ.setdefault("BONDSEYE_API_KEY", "test-key")
os.environ.setdefault("BONDSEYE_DB_PATH", "/tmp/bondseye-test.sqlite3")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_telemetry_requires_key():
    response = client.post("/api/telemetry", json={"node_id": "esp32s3-node-01", "rssi": -55, "sequence": 1})
    assert response.status_code == 401


def test_telemetry_accepts_valid_packet():
    response = client.post(
        "/api/telemetry",
        headers={"x-api-key": "test-key"},
        json={"node_id": "esp32s3-node-01", "rssi": -55, "sequence": 2},
    )
    assert response.status_code == 200
    assert response.json()["accepted"] is True
    latest = client.get("/api/latest").json()
    assert latest["node_count"] >= 1


def test_snapshot_includes_stick_figure():
    latest = client.get("/api/latest").json()
    assert latest["stick_figure"] is not None
    figure = latest["stick_figure"]
    for field in ("mode", "zone", "x", "y", "motion", "confidence"):
        assert field in figure
    assert latest["pose_state"] in {
        "UNKNOWN",
        "NO_PERSON",
        "STANDING_STILL",
        "MOVING",
        "CROUCH_LIKE",
    }


def test_motion_drives_presence_and_moving_pose():
    # High CSI variance reads as motion -> presence + MOVING. The value must
    # dominate the average across any still-online idle nodes from prior tests.
    response = client.post(
        "/api/telemetry",
        headers={"x-api-key": "test-key"},
        json={"node_id": "esp32s3-node-02", "rssi": -50, "csi_variance": 2.0, "sequence": 3},
    )
    assert response.status_code == 200
    latest = client.get("/api/latest").json()
    assert latest["presence"] is True
    assert latest["pose_state"] == "MOVING"
    assert latest["stick_figure"]["mode"] == "MOVING"
