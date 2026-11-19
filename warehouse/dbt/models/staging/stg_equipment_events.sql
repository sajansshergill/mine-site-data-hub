-- drop consecutive duplicate statuses so intervals start only on real changes
with ordered as (
    select *, lag(status) over (partition by equipment_id order by ts) as prev_status
    from {{ source('raw', 'equipment_events') }}
)
select ts, equipment_id, status, coalesce(reason, 'NONE') as reason, fault_code, vendor
from ordered
where prev_status is distinct from status