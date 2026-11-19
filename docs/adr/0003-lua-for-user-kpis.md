# ADR 0003: Lua for user-defined KPIs

## Status

Accepted

## Context

Mine engineers need to iterate on site-specific metrics (strip ratio, hang time, fuel intensity) without redeploying the Python API. The same language is already used in Fluent Bit filters and Redis scripts.

## Decision

Expose a **sandboxed Lua** KPI engine via `lupa`, with YAML definitions under `config/kpis/`, read-only data bindings, and instruction/memory limits.

## Consequences

- Non-developers can edit KPI math with a short learning curve.
- Sandbox blocks `os`/`io`/`require`; escape attempts are regression-tested.
- KPI logic is versioned in git and results land in `ops.kpi_runs`.
- Complex analytics still belong in dbt/SQL — Lua is for small, auditable calculations only.
