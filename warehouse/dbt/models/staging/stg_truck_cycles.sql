select cycle_id, truck_id, shift_id, load_start, load_end, dump_start, dump_end,
       source_location, dest_location, payload_t, queue_load_s, queue_dump_s, haul_full_s, haul_empty_s,
       extract(epoch from (load_end - load_start)) as load_s,
       extract(epoch from (dump_end - dump_start)) as dump_s,
       revision
from {{ source('raw', 'truck_cycles') }}