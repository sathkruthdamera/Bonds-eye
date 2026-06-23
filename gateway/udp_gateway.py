from __future__ import annotations

import argparse
import json
import logging
import queue
import socket
import threading
import time
from collections import defaultdict, deque
from typing import Any
from urllib import request

LOGGER = logging.getLogger("bondseye.gateway")
REQUIRED_FIELDS = {"node_id", "rssi", "sequence"}
DEFAULT_NODES = {"esp32s3-node-01", "esp32s3-node-02", "esp32s3-node-03"}
RSSI_WINDOWS: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=20))
LAST_SEQUENCE: dict[str, int] = {}


def now_ms() -> int:
    return int(time.time() * 1000)


def variance(values: deque[int]) -> float:
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    return sum((value - avg) ** 2 for value in values) / len(values)


def packet_loss(node_id: str, sequence: int) -> float:
    previous = LAST_SEQUENCE.get(node_id)
    LAST_SEQUENCE[node_id] = sequence
    if previous is None or sequence <= previous + 1:
        return 0.0
    missing = sequence - previous - 1
    return min(missing / max(sequence - previous, 1), 1.0)


def validate_packet(packet: dict[str, Any], allowed_nodes: set[str]) -> tuple[bool, str]:
    missing = REQUIRED_FIELDS - set(packet)
    if missing:
        return False, f"missing required fields: {sorted(missing)}"
    if packet["node_id"] not in allowed_nodes:
        return False, f"unknown node_id: {packet['node_id']}"
    try:
        rssi = int(packet["rssi"])
        sequence = int(packet["sequence"])
    except (TypeError, ValueError):
        return False, "rssi and sequence must be integers"
    if not -120 <= rssi <= 0:
        return False, "rssi must be between -120 and 0 dBm"
    if sequence < 0:
        return False, "sequence must be non-negative"
    return True, "ok"


def normalize_packet(packet: dict[str, Any]) -> dict[str, Any]:
    node_id = str(packet["node_id"])
    rssi = int(packet["rssi"])
    sequence = int(packet["sequence"])
    RSSI_WINDOWS[node_id].append(rssi)
    return {
        "node_id": node_id,
        "rssi": rssi,
        "sequence": sequence,
        "timestamp_ms": int(packet.get("timestamp_ms") or now_ms()),
        "rssi_variance": float(packet.get("rssi_variance") or variance(RSSI_WINDOWS[node_id])),
        "csi_variance": float(packet.get("csi_variance") or 0.0),
        "packet_loss": float(packet.get("packet_loss") or packet_loss(node_id, sequence)),
    }


def relay_packet(api_url: str, packet: dict[str, Any], timeout_seconds: float) -> None:
    body = json.dumps(packet).encode("utf-8")
    req = request.Request(api_url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=timeout_seconds) as response:
        if response.status >= 300:
            raise RuntimeError(f"backend returned HTTP {response.status}")


def _relay_worker(relay_queue: "queue.Queue[dict[str, Any]]", api_url: str, timeout_seconds: float) -> None:
    while True:
        packet = relay_queue.get()
        try:
            relay_packet(api_url, packet, timeout_seconds)
            LOGGER.info("relayed %s seq=%s rssi=%s", packet["node_id"], packet["sequence"], packet["rssi"])
        except Exception:
            LOGGER.exception("relay error for %s", packet.get("node_id"))
        finally:
            relay_queue.task_done()


def run_gateway(host: str, port: int, api_url: str, allowed_nodes: set[str], timeout_seconds: float, workers: int = 4, queue_size: int = 1000) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    relay_queue: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=queue_size)
    for index in range(max(1, workers)):
        threading.Thread(target=_relay_worker, args=(relay_queue, api_url, timeout_seconds), name=f"relay-{index}", daemon=True).start()
    LOGGER.info("listening for UDP telemetry on %s:%s", host, port)
    LOGGER.info("relaying valid packets to %s with %s workers", api_url, workers)
    while True:
        # recvfrom must never block on backend latency; relay happens off-thread.
        data, addr = sock.recvfrom(4096)
        try:
            packet = json.loads(data.decode("utf-8"))
            valid, reason = validate_packet(packet, allowed_nodes)
            if not valid:
                LOGGER.warning("dropped packet from %s: %s", addr, reason)
                continue
            normalized = normalize_packet(packet)
            try:
                relay_queue.put_nowait(normalized)
            except queue.Full:
                LOGGER.warning("relay queue full, dropping packet from %s", normalized["node_id"])
        except Exception:
            LOGGER.exception("gateway parse error")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bonds-eye UDP-to-HTTP telemetry gateway")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=45454)
    parser.add_argument("--api-url", default="http://127.0.0.1:8080/api/telemetry")
    parser.add_argument("--nodes", default=",".join(sorted(DEFAULT_NODES)))
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--queue-size", type=int, default=1000)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(message)s")
    allowed_nodes = {node.strip() for node in args.nodes.split(",") if node.strip()}
    run_gateway(args.host, args.port, args.api_url, allowed_nodes, args.timeout, args.workers, args.queue_size)


if __name__ == "__main__":
    main()
