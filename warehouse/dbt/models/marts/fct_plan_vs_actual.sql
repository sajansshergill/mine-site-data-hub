with actual as (
    select
        shift_id,
        source_location as location,
        material,
        sum(payload_t) as actual_tonnes
    from {{ ref('fct_truck_cycle') }}
    group by 1, 2, 3
)
select
    coalesce(p.shift_id, a.shift_id) as shift_id,
    coalesce(p.location, a.location) as location,
    coalesce(p.material, a.material) as material,
    coalesce(p.planned_tonnes, 0)::double precision as planned_tonnes,
    coalesce(a.actual_tonnes, 0)::double precision as actual_tonnes,
    coalesce(a.actual_tonnes, 0) - coalesce(p.planned_tonnes, 0) as variance_t,
    100.0 * {{ safe_divide('coalesce(a.actual_tonnes, 0) - coalesce(p.planned_tonnes, 0)', 'p.planned_tonnes') }}
        as variance_pct,
    p.planned_grade_gpt,
    p.planned_truck_hours,
    p.plan_version
from {{ ref('stg_plan') }} p
full outer join actual a
    on a.shift_id = p.shift_id
   and a.location = p.location
   and a.material = p.material
