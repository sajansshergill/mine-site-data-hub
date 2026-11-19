# ADR 0002: TimescaleDB over InfluxDB

## Status

Accepted

## Context

We need high-resolution plant tags, fleet events, relational dimensions (equipment, locations, plans), dbt transformations, and Grafana SQL panels on one host.

## Decision

Use **PostgreSQL 16 + TimescaleDB** (hypertables, compression, continuous aggregates) instead of InfluxDB (or a split SQL + TSDB pair).

## Consequences

- One datastore for raw series, ops tables, and marts; Alembic + dbt stay first-class.
- Continuous aggregates cover 1-minute / 1-hour plant rollups without a separate rollup job.
- Team SQL skills transfer; no Flux-only query path.
- Write throughput is lower than a purpose-built TSDB at extreme scale — fine for a single pit’s tag count.
