-- latest plan version per shift wins
select shift_id, location, material, planned_tonnes, planned_grade_gpt, planned_truck_hours, plan_version
from (
    select *, rank() over (partition by shift_id order by plan_version desc) as rk
    from {{ source('raw', 'mine_plan') }}
) p where rk = 1