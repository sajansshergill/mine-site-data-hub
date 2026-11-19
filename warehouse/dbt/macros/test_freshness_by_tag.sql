{% test freshness_by_tag(model, column_name, max_age_minutes=10) %}
select tag, max({{ column_name }}) as last_seen
from {{ model }}
group by tag
having max({{ column_name }}) < now() - interval '{{ max_age_minutes }} minutes'
{% endtest %}