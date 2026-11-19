-- Overlapping status intervals for the same equipment indicate a broken interval build.
select
    a.equipment_id,
    a.shift_id,
    a.start_ts as a_start,
    a.end_ts as a_end,
    b.start_ts as b_start,
    b.end_ts as b_end
from {{ ref('int_equipment_status_intervals') }} a
join {{ ref('int_equipment_status_intervals') }} b
  on a.equipment_id = b.equipment_id
 and a.start_ts < b.start_ts
 and a.end_ts > b.start_ts
