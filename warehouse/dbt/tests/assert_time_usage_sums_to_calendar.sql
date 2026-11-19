-- Every unit's status hours must sum to the 12 h calendar for the shift.
select
    equipment_id,
    shift_id,
    calendar_hours,
    operating_hours + standby_hours + delay_hours + downtime_hours as accounted_hours
from {{ ref('int_time_usage_model') }}
where abs(
    calendar_hours - (operating_hours + standby_hours + delay_hours + downtime_hours)
) > 0.01
