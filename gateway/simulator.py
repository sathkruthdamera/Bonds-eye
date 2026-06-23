"""Bonds-eye node simulator.

Emulates the 3 ESP32-S3 nodes so the full pipeline (gateway -> API -> mobile)
can be exercised on a laptop with no hardware. By default it sends UDP JSON
packets to the gateway, exactly like the firmware does; it can also POST
straight to the API.

Scenarios drive the scoring engine into specific states:

    empty    -> NO_PERSON
    still    -> STANDING_STILL
    walking  -> MOVING
    crouch   -> CROUCH_LIKE
    cycle    -> rotates the above and sweeps the active node across zones

Examples:
    python simulator.py --scenario cycle
    python simulator.py --scenario walking --rate 5 --duration 30
    python simulator.py --api-url http://127.0.0.1:8080/api/telemetry --api-key dev-change-me
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import socket
import time
from typing import Any
from urllib import request

LOGGER = logging.getLogger("bondseye.simulator")

DEFAULT_NODES = ["esp32s3-node-01", "esp32s3-node-02", "esp32s3-node-03"]
SCENARIOS = ("empty", "still", "walking", "crouch")

# Per-scenario synthetic feature profiles, chosen so the scoring engine in
# api/phase2_scoring_engine.py resolves to the matching pose state. "active" is
# the node a person is nearest, which gets stronger motion/disturbance so the
# zone resolves to it.
PROFILES: dict[str, dict[str, float]] = {
    #            base rssi   rssi_var   csi (idle)   csi (active)
    "empty":   {"rssi": -59, "rssi_var": 0.02, "csi_idle": 0.02, "csi_active": 0.03},
    "still":   {"rssi": -45, "rssi_var": 0.04, "csi_idle": 0.12, "csi_active": 0.20},
    "walking": {"rssi": -50, "rssi_var": 0.10, "csi_idle": 0.45, "csi_active": 0.88},
    "crouch":  {"rssi": -34, "rssi_var": 0.04, "csi_idle": 0.10, "csi_active": 0.16},
}


def clamp_rssi(value: float) -> int:
    return int(max(-120, min(0, round(value))))


def build_packet(node_id: str, scenario: str, sequence: int, active: bool, rng: random.Random) -> dict[str, Any]:
    profile = PROFILES[scenario]
    rssi = clamp_rssi(profile["rssi"] + rng.uniform(-2.0, 2.0))
    rssi_variance = max(0.0, profile["rssi_var"] + rng.uniform(-0.01, 0.02))
    csi_variance = (profile["csi_active"] if active else profile["csi_idle"]) + rng.uniform(-0.03, 0.03)
    return {
        "node_id": node_id,
        "rssi": rssi,
        "sequence": sequence,
        "timestamp_ms": int(time.time() * 1000),
        "rssi_variance": round(rssi_variance, 4),
        "csi_variance": round(max(0.0, csi_variance), 4),
    }


def send_udp(sock: socket.socket, target: tuple[str, int], packet: dict[str, Any]) -> None:
    sock.sendto(json.dumps(packet).encode("utf-8"), target)


def post_api(api_url: str, api_key: str | None, packet: dict[str, Any], timeout: float) -> None:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    req = request.Request(api_url, data=json.dumps(packet).encode("utf-8"), headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout):
        pass


def run(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    nodes = [n.strip() for n in args.nodes.split(",") if n.strip()]
    sequences = {node: 0 for node in nodes}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) if not args.api_url else None
    target = (args.host, args.port)
    interval = 1.0 / max(0.1, args.rate)
    started = time.time()
    tick = 0
    # cycle: change scenario every `phase_seconds`, sweeping the active node.
    cycle_order = list(SCENARIOS)

    LOGGER.info(
        "simulating %s nodes -> %s at %.1f Hz (scenario=%s)",
        len(nodes),
        args.api_url or f"udp://{args.host}:{args.port}",
        args.rate,
        args.scenario,
    )
    try:
        while True:
            elapsed = time.time() - started
            if args.duration and elapsed >= args.duration:
                break

            if args.scenario == "cycle":
                phase = int(elapsed // args.phase_seconds)
                scenario = cycle_order[phase % len(cycle_order)]
                active_index = phase % len(nodes)
            else:
                scenario = args.scenario
                active_index = (tick // 4) % len(nodes) if args.sweep else args.active

            for index, node in enumerate(nodes):
                sequences[node] += 1
                packet = build_packet(node, scenario, sequences[node], index == active_index, rng)
                try:
                    if args.api_url:
                        post_api(args.api_url, args.api_key, packet, args.timeout)
                    else:
                        send_udp(sock, target, packet)
                except Exception:
                    LOGGER.exception("send failed for %s", node)

            active_node = nodes[active_index] if 0 <= active_index < len(nodes) else "-"
            LOGGER.info("tick=%s scenario=%s active=%s", tick, scenario, active_node)
            tick += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        LOGGER.info("simulator stopped")
    finally:
        if sock is not None:
            sock.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bonds-eye ESP32-S3 node simulator")
    parser.add_argument("--host", default="127.0.0.1", help="gateway UDP host")
    parser.add_argument("--port", type=int, default=45454, help="gateway UDP port")
    parser.add_argument("--api-url", default=None, help="POST directly to this API URL instead of UDP")
    parser.add_argument("--api-key", default=None, help="x-api-key header for --api-url mode")
    parser.add_argument("--nodes", default=",".join(DEFAULT_NODES))
    parser.add_argument("--scenario", choices=(*SCENARIOS, "cycle"), default="cycle")
    parser.add_argument("--active", type=int, default=1, help="active node index for fixed scenarios")
    parser.add_argument("--sweep", action="store_true", help="rotate the active node across zones")
    parser.add_argument("--phase-seconds", type=float, default=6.0, help="seconds per scenario in cycle mode")
    parser.add_argument("--rate", type=float, default=2.0, help="packets per node per second")
    parser.add_argument("--duration", type=float, default=0.0, help="run seconds (0 = forever)")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(message)s")
    run(args)


if __name__ == "__main__":
    main()
