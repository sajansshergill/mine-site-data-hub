-- KEYS[1] = live:queues
-- ARGV[1] = location
-- ARGV[2] = delta (integer, may be negative)
local queues = KEYS[1]
local location = ARGV[1]
local delta = tonumber(ARGV[2])

local current = tonumber(redis.call('HGET', queues, location) or '0')
local next_val = current + delta
if next_val < 0 then
  next_val = 0
end
redis.call('HSET', queues, location, next_val)
return next_val
