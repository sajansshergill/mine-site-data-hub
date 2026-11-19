select *
from (
    values
        ('ORE'::text, 'ore'::text, null::text, 'CRUSHER'::text),
        ('WASTE', 'waste', null, 'WASTE_DUMP_N')
) as t(material, material_group, grade_band, destination_rule)
