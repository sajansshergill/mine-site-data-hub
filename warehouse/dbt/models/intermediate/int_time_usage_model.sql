-- Time usage per equipment × shift. Calendar is a fixed 12 h shift;
-- any unobserved remainder is counted as standby so hours sum to calendar.
with rolled as (
    select
        equipment_id,
        shift_id,
        sum(case when status = 'RUNNING' then hours else 0 end) as operating_hours,
        sum(case when status = 'STANDBY' then hours else 0 end) as standby_raw,
        sum(case when status = 'DELAY' then hours else 0 end) as delay_hours,
        sum(case when status = 'DOWN' then hours else 0 end) as downtime_hours
    from {{ ref('int_equipment_status_intervals') }}
    group by 1, 2
)
select
    equipment_id,
    shift_id,
    12.0::numeric as calendar_hours,
    operating_hours,
    delay_hours,
    downtime_hours,
    standby_raw
        + greatest(0::numeric, 12.0 - (operating_hours + standby_raw + delay_hours + downtime_hours))
        as standby_hours,
    operating_hours
        + standby_raw
        + greatest(0::numeric, 12.0 - (operating_hours + standby_raw + delay_hours + downtime_hours))
        + delay_hours
        as available_hours
from rolled
