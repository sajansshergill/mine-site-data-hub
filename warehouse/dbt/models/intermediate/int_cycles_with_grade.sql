-- Attach source-location material and tonne-weighted assay grade to each cycle.
with loc_grade as (
    select
        location,
        {{ safe_divide('sum(au_gpt * tonnes_represented)', 'sum(tonnes_represented)') }} as au_gpt
    from {{ ref('stg_assays') }}
    group by location
)
select
    c.cycle_id,
    c.truck_id,
    c.shift_id,
    c.load_start,
    c.load_end,
    c.dump_start,
    c.dump_end,
    c.source_location,
    c.dest_location,
    c.payload_t,
    c.spot_load_s,
    c.spot_dump_s,
    c.haul_full_s,
    c.haul_empty_s,
    c.load_s,
    c.dump_s,
    c.revision,
    coalesce(loc.material, 'ORE') as material,
    g.au_gpt as estimated_au_gpt
from {{ ref('stg_truck_cycles') }} c
left join {{ ref('locations') }} loc on loc.location = c.source_location
left join loc_grade g on g.location = c.source_location
