select
    location,
    location_type,
    nullif(pit, '') as pit,
    material,
    null::text as geofence_wkt
from {{ ref('locations') }}
