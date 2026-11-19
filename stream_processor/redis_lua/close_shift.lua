-- KEYS[1] = live:current_shift
-- KEYS[2] = shift:{old}:totals
-- KEYS[3] = shift:{old}:truck_loads
-- KEYS[4] = shift:{old}:last_payload
-- KEYS[5] = shift:{old}:snapshot
-- KEYS[6] = live:queues  (optional reset)
-- ARGV[1] = new_shift_id
local current_key = KEYS[1]
local totals = KEYS[2]
local truck_loads = KEYS[3]
local last_payload = KEYS[4]
local snapshot = KEYS[5]
local queues = KEYS[6]
local new_shift = ARGV[1]

-- Snapshot active counters into a hash for the closed shift.
local tot = redis.call('HGETALL', totals)
if #tot > 0 then
  for i = 1, #tot, 2 do
    redis.call('HSET', snapshot, 'totals:' .. tot[i], tot[i + 1])
  end
end
local loads = redis.call('HGETALL', truck_loads)
if #loads > 0 then
  for i = 1, #loads, 2 do
    redis.call('HSET', snapshot, 'truck_loads:' .. loads[i], loads[i + 1])
  end
end
local payloads = redis.call('HGETALL', last_payload)
if #payloads > 0 then
  for i = 1, #payloads, 2 do
    redis.call('HSET', snapshot, 'last_payload:' .. payloads[i], payloads[i + 1])
  end
end
redis.call('HSET', snapshot, 'closed_at', tostring(redis.call('TIME')[1]))

-- Point live pointer at the new shift, then clear old active counters.
redis.call('SET', current_key, new_shift)
redis.call('DEL', totals)
redis.call('DEL', truck_loads)
redis.call('DEL', last_payload)

-- Reset live queues at shift boundary so lengths do not carry over.
if queues and queues ~= '' then
  redis.call('DEL', queues)
end

return new_shift
