-- Planned vs mined vs milled (ore to crusher) grade per shift.
with planned as (
    select
        shift_id,
        sum(planned_tonnes) as planned_ore_t,
        {{ safe_divide('sum(planned_grade_gpt * planned_tonnes)', 'sum(planned_tonnes)') }} as planned_grade_gpt
    from {{ ref('stg_plan') }}
    where material = 'ORE'
    group by 1
),
mined as (
    select
        shift_id,
        sum(payload_t) as mined_ore_t,
        {{ safe_divide('sum(estimated_au_gpt * payload_t)', 'sum(payload_t)') }} as mined_grade_gpt
    from {{ ref('int_cycles_with_grade') }}
    where material = 'ORE'
    group by 1
),
milled as (
    select
        shift_id,
        sum(payload_t) as milled_ore_t,
        {{ safe_divide('sum(estimated_au_gpt * payload_t)', 'sum(payload_t)') }} as milled_grade_gpt
    from {{ ref('int_cycles_with_grade') }}
    where material = 'ORE' and dest_location = 'CRUSHER'
    group by 1
),
plant as (
    select
        shift_id,
        sum(tonnes_estimate) as plant_feed_t
    from {{ ref('int_plant_throughput_by_shift') }}
    where tag ilike 'ML01.FEED%' or tag ilike 'CR01.THROUGHPUT%'
    group by 1
)
select
    coalesce(p.shift_id, m.shift_id, l.shift_id, pl.shift_id) as shift_id,
    p.planned_ore_t,
    p.planned_grade_gpt,
    m.mined_ore_t,
    m.mined_grade_gpt,
    l.milled_ore_t,
    l.milled_grade_gpt,
    pl.plant_feed_t,
    m.mined_grade_gpt - p.planned_grade_gpt as mined_vs_plan_gpt,
    l.milled_grade_gpt - m.mined_grade_gpt as mill_vs_mined_gpt
from planned p
full outer join mined m using (shift_id)
full outer join milled l using (shift_id)
full outer join plant pl using (shift_id)
