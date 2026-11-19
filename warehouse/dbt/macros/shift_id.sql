{# Site-local 06:00-18:00 = D, 18:00-06:00 = N (labelled with the date it starts). #}
{% macro shift_id(ts, tz="'America/Los_Angeles'") -%}
  case
    when extract(hour from ({{ ts }} at time zone {{ tz }})) between 6 and 17
      then to_char(({{ ts }} at time zone {{ tz }})::date, 'YYYY-MM-DD') || '-D'
    when extract(hour from ({{ ts }} at time zone {{ tz }})) >= 18
      then to_char(({{ ts }} at time zone {{ tz }})::date, 'YYYY-MM-DD') || '-N'
    else to_char(({{ ts }} at time zone {{ tz }})::date - 1, 'YYYY-MM-DD') || '-N'
  end
{%- endmacro %}