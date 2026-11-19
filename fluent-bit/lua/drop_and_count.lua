-- Tag malformed records for the DLQ topic and count them.
local malformed_total = 0

function drop_or_route(tag, timestamp, record)
  if record.malformed then
    malformed_total = malformed_total + 1
    record.dlq = "true"
    record.malformed_total = malformed_total
    -- Keep the record; Rewrite_Tag routes it to equipment.dlq.
    return 1, timestamp, record
  end
  record.dlq = "false"
  return 1, timestamp, record
end
