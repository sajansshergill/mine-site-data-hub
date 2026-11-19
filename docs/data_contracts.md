# Data contracts

Contracts exist in two forms that must stay aligned:

1. **Pydantic** models under `libs/minehub_common/minehub_common/contracts/` — used at ingest and in batch loaders.
2. **Avro** schemas under `schemas/*.avsc` — registered in Redpanda Schema Registry for streaming topics.

Validation failures go to dead-letter topics and `ops.quarantine`.

## Streaming (Avro + Pydantic)

### TruckTelemetry (`truck_telemetry.v1`)

| Field | Type | Notes |
|---|---|---|
| ts | timestamp-millis | Event time |
| msg_id | string | Idempotency key |
| truck_id | string | Required |
| x_m, y_m | double | Site coordinates |
| speed_kmh | double | 0–120 |
| payload_t | double | 0–400 |
| engine_on | boolean | |
| fuel_pct | double \| null | 0–100 |

### PlantTag (`plant_tag.v1`)

`tag`, `ts`, `value`, `source`, `quality` ∈ {GOOD, UNCERTAIN, BAD}.

### EquipmentEvent (`equipment_event.v1`)

`equipment_id`, `status` ∈ {RUNNING, STANDBY, DELAY, DOWN}, `reason`, `fault_code`, `vendor`, `raw_code`.

### TruckCycle (`truck_cycle.v1`)

Derived by the stream processor: load/dump windows, source/dest locations, payload, queue and haul durations, `revision` for late corrections.

## Batch (Pydantic only)

### PlanRow

`shift_date`, `shift_code` (D\|N), `location`, `material` (ORE\|WASTE), `planned_tonnes`, optional grade / truck hours, `plan_version`. `shift_id` is derived as `{date}-{code}`.

### WorkOrder

`wo_number`, `equipment_id`, `wo_type` (PLANNED\|UNPLANNED), open/close timestamps, `downtime_hours`, `failure_code`.

### Assay

`sample_id`, `location`, `block_id`, `sampled_on`, `au_gpt`, `tonnes_represented`.

## Compatibility rules

- Additive optional Avro fields only; bump major version for breaking changes.
- Pydantic `to_avro()` is the single serialization path for connectors.
- Register schemas with `schemas/register_schemas.py` before connectors start.
