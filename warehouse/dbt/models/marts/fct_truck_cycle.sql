select
    cycle_id,
    truck_id,
    truck_id as equipment_id,
    shift_id,
    load_start,
    load_end,
    dump_start,
    dump_end,
    source_location,
    dest_location,
    material,
    payload_t,
    estimated_au_gpt as au_gpt,
    spot_load_s,
    load_s,
    haul_full_s,
    spot_dump_s,
    dump_s,
    haul_empty_s,
    coalesce(spot_load_s, 0) + coalesce(load_s, 0) + coalesce(haul_full_s, 0)
        + coalesce(spot_dump_s, 0) + coalesce(dump_s, 0) + coalesce(haul_empty_s, 0) as cycle_time_s,
    revision
from {{ ref('int_cycles_with_grade') }}
