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
