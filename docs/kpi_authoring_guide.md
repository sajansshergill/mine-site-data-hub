# KPI authoring guide

Site engineers define KPIs as YAML files in `config/kpis/`. The engine loads them, binds read-only shift inputs, runs the Lua body inside a sandbox (`lupa`), and stores results in `ops.kpi_runs`.

## File format

```yaml
name: strip_ratio          # unique id
version: 2                 # bump when logic changes
owner: mine-engineering
unit: ratio
description: Waste tonnes divided by ore tonnes for the shift
inputs: [tonnes_by_material]
params: {}                 # optional constants exposed as `params`
lua: |
  local waste = inputs.tonnes_by_material["WASTE"] or 0
  local ore = inputs.tonnes_by_material["ORE"] or 0
  if ore == 0 then return nil end
  return waste / ore
```

## Available inputs

Declared in `kpi_engine/data_bindings.py`:

| Input | Shape |
|---|---|
| `tonnes_by_material` | `{ MATERIAL: tonnes }` |
| `total_tonnes` | number |
| `truck_operating_hours` | `{ truck_id: hours }` |
| `shovel_idle_minutes` | `{ shovel_id: minutes }` |

Request new bindings from the data team rather than querying the warehouse from Lua.

## Sandbox limits

- Whitelisted globals only (`math`, `string`, `table`, …). No `os`, `io`, `require`, `dofile`, `debug`.
- Instruction budget and memory cap enforced per run.
- Return a **number** or **nil** (nil = insufficient data, not an error).

## Workflow

1. Add `config/kpis/<name>.yaml`.
2. Dry-run via API: `POST /kpis/validate` with Lua + inputs + `shift_id` (engineer key).
3. Commit; Dagster / `python -m kpi_engine.engine --shift latest` evaluates all KPIs.
4. Ad-hoc: `POST /kpis/{name}/run?shift_id=...`.

## Testing

- Unit: `kpi_engine/tests/test_kpis.py` for expected values on fixture inputs.
- Security: `test_sandbox_escape.py` asserts forbidden libraries stay unreachable.
