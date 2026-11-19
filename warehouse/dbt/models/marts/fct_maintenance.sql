-- One row per work order with equipment-level MTBF / MTTR context.
with wo as (
    select
        wo_number,
        equipment_id,
        wo_type,
        description,
        opened_at,
        closed_at,
        downtime_hours,
        failure_code,
        case
            when upper(wo_type) in ('PLANNED', 'PM') then 'planned'
            else 'unplanned'
        end as planned_unplanned,
        {{ shift_id('opened_at') }} as shift_id
    from {{ ref('stg_work_orders') }}
),
ops as (
    select equipment_id, sum(operating_hours) as operating_hours
    from {{ ref('fct_equipment_shift') }}
    group by 1
),
agg as (
    select
        equipment_id,
        count(*) as repair_count,
        count(*) filter (where planned_unplanned = 'unplanned') as unplanned_failures,
        sum(downtime_hours) as total_repair_hours,
        sum(downtime_hours) filter (where planned_unplanned = 'planned') as planned_downtime_hours,
        sum(downtime_hours) filter (where planned_unplanned = 'unplanned') as unplanned_downtime_hours
    from wo
    group by 1
)
select
    w.wo_number,
    w.equipment_id,
    e.equipment_class,
    w.wo_type,
    w.planned_unplanned,
    w.description,
    w.opened_at,
    w.closed_at,
    w.downtime_hours,
    w.failure_code,
    w.shift_id,
    o.operating_hours as equipment_operating_hours,
    a.repair_count,
    a.unplanned_failures,
    a.planned_downtime_hours,
    a.unplanned_downtime_hours,
    {{ safe_divide('o.operating_hours', 'a.unplanned_failures') }} as mtbf_hours,
    {{ safe_divide('a.total_repair_hours', 'a.repair_count') }} as mttr_hours
from wo w
left join ops o on o.equipment_id = w.equipment_id
left join agg a on a.equipment_id = w.equipment_id
left join {{ ref('dim_equipment') }} e on e.equipment_id = w.equipment_id
