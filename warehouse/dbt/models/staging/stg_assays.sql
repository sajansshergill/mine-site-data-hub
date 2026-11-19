select sample_id, location, block_id, sampled_on, au_gpt, tonnes_represented
from {{ source('raw', 'assays') }}