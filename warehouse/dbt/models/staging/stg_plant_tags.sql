select ts, tag, split_part(tag, '.', 1) as equipment_id, source, value, quality,
        {{ shift_id('ts') }} as shift_id
from {{ source('raw', 'plant_tags') }}