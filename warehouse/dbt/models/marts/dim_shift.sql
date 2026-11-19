-- Distinct shifts from plan, cycles, status intervals, and plant tags.
with shifts as (
    select distinct shift_id from {{ ref('stg_truck_cycles') }}
    union
    select distinct shift_id from {{ ref('stg_plan') }}
    union
    select distinct shift_id from {{ ref('int_equipment_status_intervals') }}
    union
    select distinct shift_id from {{ ref('stg_plant_tags') }}
),
parsed as (
    select
        shift_id,
        left(shift_id, 10)::date as shift_date,
        right(shift_id, 1) as day_night_code
    from shifts
    where shift_id ~ '^\d{4}-\d{2}-\d{2}-[DN]$'
)
select
    shift_id,
    shift_date,
    case when day_night_code = 'D' then 'day' else 'night' end as day_night,
    day_night_code,
    case when day_night_code = 'D'
        then (shift_date::timestamp + interval '6 hours') at time zone 'America/Los_Angeles'
        else (shift_date::timestamp + interval '18 hours') at time zone 'America/Los_Angeles'
    end as start_ts,
    case when day_night_code = 'D'
        then (shift_date::timestamp + interval '18 hours') at time zone 'America/Los_Angeles'
        else ((shift_date + 1)::timestamp + interval '6 hours') at time zone 'America/Los_Angeles'
    end as end_ts,
    (array['A', 'B', 'C', 'D'])[
        ((shift_date - date '2026-01-01') / 2) % 4 + 1
    ] as crew
from parsed
