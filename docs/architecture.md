# Architecture

Mine Site Data Hub is an on-prem, event-driven platform that reconciles mine plan against actual production every shift and serves the results through an API, Grafana, automated PDF reports, and a sandboxed Lua KPI engine.

## Layers

1. **Simulated sources** — haul fleet (MQTT), plant OPC UA / Modbus, equipment log writer, and batch plan / CMMS / assay files.
2. **Edge connectors** — Mosquitto + MQTT/OPC UA/Modbus connectors validate against Pydantic contracts and publish Avro to Redpanda; Fluent Bit + Lua normalizes vendor logs.
3. **Streaming** — Redpanda topics with schema registry; stream-processor detects truck cycles, enriches with shift/location, updates Redis live state via Lua, and routes bad records to DLQ.
4. **Warehouse** — TimescaleDB raw hypertables → dbt staging / intermediate / marts (plan vs actual, equipment shift, grade, maintenance).
5. **Orchestration** — Dagster loads batch files, runs dbt, DQ checks, KPI engine, and shift reports on shift change.
6. **Serving** — FastAPI (roles), Grafana dashboards as code, HTML/PDF shift report + SMTP.
7. **Observability** — Prometheus / Alertmanager / Loki / Promtail with runbook-linked alerts.

## Design choices

| Choice | Why |
|---|---|
| Redpanda | Kafka API with simpler ops for a single site host — see ADR 0001 |
| TimescaleDB | SQL + hypertables + continuous aggregates on one Postgres — see ADR 0002 |
| Lua KPIs | Small sandbox via `lupa`, editable by site engineers — see ADR 0003 |
| Redis Lua | Atomic multi-key live shift counters without race conditions |

## Data flow (shift close)

```
shift boundary → stream-processor close_shift.lua snapshot
              → Dagster shift_change sensor
              → dbt run → DQ checks → KPI engine → shift PDF/email
```

Live dashboards read Redis; historical reconciliation reads `marts.fct_plan_vs_actual`.
