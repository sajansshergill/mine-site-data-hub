-- Aggregate throughput / feed rate tags to shift × equipment (and tag).
-- Rate tags (t/h): mean value × 12 h ≈ shift tonnes. Increment tags: sum of values.
with tagged as (
    select
        shift_id,
        equipment_id,
        tag,
        value,
        case
            when tag ilike '%\\_INC' escape '\\' then 'inc'
            when tag ilike '%THROUGHPUT%'
              or tag ilike '%FEED%'
              or tag ilike '%BELT_RATE%' then 'rate'
            else 'other'
        end as tag_kind
    from {{ ref('stg_plant_tags') }}
    where quality is distinct from 'BAD'
      and (
          tag ilike '%THROUGHPUT%'
          or tag ilike '%FEED%'
          or tag ilike '%BELT_RATE%'
          or tag ilike '%\\_INC' escape '\\'
      )
)
select
    shift_id,
    equipment_id,
    tag,
    tag_kind,
    count(*) as sample_count,
    avg(value) as avg_value,
    case
        when tag_kind = 'inc' then sum(value)
        when tag_kind = 'rate' then avg(value) * 12.0
        else null
    end as tonnes_estimate
from tagged
group by 1, 2, 3, 4
