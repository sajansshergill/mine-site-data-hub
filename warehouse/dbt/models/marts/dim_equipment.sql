select
    equipment_id,
    equipment_class,
    fleet,
    model,
    cast(nullif(cast(nominal_payload_t as text), '') as double precision) as nominal_payload_t,
    null::date as commissioned_date
from {{ ref('equipment') }}
