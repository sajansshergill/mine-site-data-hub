select wo_number, equipment_id, wo_type, description, opened_at, closed_at,
        coalesce(downtime_hours, extract(epoch from (closed_at - opened_at)) / 3600) as downtime_hours,
        nullif(failure_code, '') as failure_code
from {{ source('raw', 'work_orders') }}