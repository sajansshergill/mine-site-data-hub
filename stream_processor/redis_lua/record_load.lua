-- KEYS[1] = shift:{id}:totals
-- KEYS[2] = shift:{id}:truck_loads
-- KEYS[3] = shift:{id}:last_payload
-- ARGV[1] = truck_id
-- ARGV[2] = payload (tonnes)
-- ARGV[3] = material
-- ARGV[4] = location
local totals = KEYS[1]
local truck_loads = KEYS[2]
local last_payload = KEYS[3]
local truck_id = ARGV[1]
local payload = tonumber(ARGV[2])
local material = ARGV[3]
local location = ARGV[4]

redis.call('HINCRBYFLOAT', totals, 'tonnes_total', payload)
redis.call('HINCRBYFLOAT', totals, 'tonnes:' .. material, payload)
redis.call('HINCRBYFLOAT', totals, 'tonnes_loc:' .. location, payload)
redis.call('HINCRBY', totals, 'loads', 1)
redis.call('HINCRBY', truck_loads, truck_id, 1)
redis.call('HSET', last_payload, truck_id, payload)
return 1
