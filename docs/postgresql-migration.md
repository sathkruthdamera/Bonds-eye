# PostgreSQL Migration Path

When SQLite becomes a bottleneck:

1. Deploy PostgreSQL.
2. Replace sqlite3 connection layer with SQLAlchemy.
3. Store telemetry and events in PostgreSQL.
4. Add retention policies.
5. Add read replicas if required.

Recommended future extensions:
- TimescaleDB
- Grafana
- Prometheus
