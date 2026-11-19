select
    t.equipment_id,
    t.shift_id,
    e.equipment_class,
    t.calendar_hours,
    t.available_hours,
    t.operating_hours,
    t.delay_hours,
    t.downtime_hours,
    t.standby_hours,
    {{ safe_divide('t.calendar_hours - t.downtime_hours', 't.calendar_hours') }} as availability,
    {{ safe_divide('t.operating_hours', 't.available_hours') }} as utilization
from {{ ref('int_time_usage_model') }} t
left join {{ ref('dim_equipment') }} e on e.equipment_id = t.equipment_id
