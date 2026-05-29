# Hostinger KVM 2 deployment notes

Current placeholder VPS details:

- Provider: Hostinger
- Plan: KVM 2
- Public IP: 31.220.48.185
- RAM: 2 GB
- Storage: 100 GB
- Domain: pending

## Recommended runtime mode

Use the VPS for cloud processing, API, event storage, and mobile WebSocket feed.

Because 2 GB RAM is limited, keep the stack small:

- FastAPI backend
- PostgreSQL or SQLite for MVP
- Nginx only after domain is ready
- No heavy ML model during MVP

## Open ports

- 22 TCP: SSH
- 80 TCP: HTTP after domain is ready
- 443 TCP: HTTPS after domain is ready
- 8080 TCP: temporary API access before domain
- 5005 UDP: optional direct ESP telemetry, only if needed

## Recommended first deployment

```bash
git clone https://github.com/sathkruthdamera/Bonds-eye.git
cd Bonds-eye/deploy
docker compose up -d --build
curl http://31.220.48.185:8080/health
```

## Production domain later

After buying or assigning a domain, update mobile config from:

```text
ws://31.220.48.185:8080/ws/live
```

to:

```text
wss://your-domain.com/ws/live
```
