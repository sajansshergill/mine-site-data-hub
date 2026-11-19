-- Failing rows: mined (loaded) tonnes diverge from dumped tonnes in a shift.
-- Cycles with both load_end and dump_end contribute equally; incomplete cycles skew the balance.
with by_shift as (
    select
        shift_id,
        sum(payload_t) filter (where load_end is not null) as mined_t,
        sum(payload_t) filter (where dump_end is not null) as dumped_t
    from {{ ref('stg_truck_cycles') }}
    group by shift_id
)
select
    shift_id,
    mined_t,
    dumped_t,
    abs(coalesce(mined_t, 0) - coalesce(dumped_t, 0)) as delta_t
from by_shift
where abs(coalesce(mined_t, 0) - coalesce(dumped_t, 0)) > 1.0
