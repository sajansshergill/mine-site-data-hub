-- Status event -> gap-free, non-overlapping intervals, split at shift boundaries (12 h shifts at 06/18 local).
with events as (
    select equipment_id, status, reason, ts as start_ts,
            coalesce(lead(ts) over (partition by equipment_id order by ts), now()) as end_ts
    from {{ ref('stg_equipment_events') }}
),
boundaries as (
    select generate_series(
        date_trunc('day', (select min(start_ts) from events) at time zone 'America/Los_Angeles') + interval '6 hours',
        now() at time zone 'America/Los_Angeles' + interval '12 hours',
        interval '12 hours'
    ) at time zone 'America/Los_Angeles' as shift_start
),
split as (
    select e.equipment_id, e.status, e.reason,
            greatest(e.start_ts, b.shift_start) as start_ts,
            least(e.end_ts, b.shift_start + interval '12 hours') as end_ts,
            b.shift_start
    from events e
    join boundaries b on e.start_ts < b.shift_start + interval '12 hours' and e.end_ts > b.shift_start
)
select equipment_id, status, reason, start_ts, end_ts,
        {{ shift_id('start_ts') }} as shift_id,
        extract(epoch from (end_ts - start_ts)) / 3600.0 as hours
from split
where end_ts > start_ts