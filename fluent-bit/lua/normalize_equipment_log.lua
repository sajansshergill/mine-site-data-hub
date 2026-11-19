-- Normalize vendor equipment log records into canonical fields for Kafka.
local status_map
do
  local ok, mod = pcall(require, "status_map")
  if ok then
    status_map = mod
  else
    status_map = dofile("/fluent-bit/etc/lua/status_map.lua")
  end
end

local function trim(s)
  if s == nil then
    return nil
  end
  return (tostring(s):gsub("^%s+", ""):gsub("%s+$", ""))
end

local function detect_vendor(tag, record)
  if record.vendor then
    return tostring(record.vendor)
  end
  if tag and tag:find("vendor_a") then
    return "VENDOR_A"
  end
  if tag and tag:find("vendor_b") then
    return "VENDOR_B"
  end
  if tag and tag:find("vendor_c") then
    return "VENDOR_C"
  end
  -- heuristic from raw_code shape
  local code = tostring(record.raw_code or "")
  if code:match("^%d+$") then
    return "VENDOR_A"
  end
  if #code <= 5 and code:match("^[A-Z]+$") then
    if code == "OK" or code == "STBY" or code == "DLY" or code == "BRKDN" or code == "SVC" then
      return "VENDOR_C"
    end
    return "VENDOR_B"
  end
  return "UNKNOWN"
end

local function to_utc_iso(record, offset_min)
  offset_min = tonumber(offset_min) or 0
  -- Prefer Fluent Bit parsed timestamp (seconds) when present as record["ts"] string kept.
  if record.ts_utc then
    return tostring(record.ts_utc)
  end
  if type(record.timestamp_unix) == "number" then
    return os.date("!%Y-%m-%dT%H:%M:%SZ", math.floor(record.timestamp_unix))
  end
  -- Fallback: treat string ts as local site time and shift by SITE_UTC_OFFSET_MIN.
  local ts = trim(record.ts)
  if not ts then
    return os.date("!%Y-%m-%dT%H:%M:%SZ")
  end
  -- If already has Z or offset, keep as-is (Fluent Bit may leave original).
  if ts:find("Z") or ts:find("[+-]%d%d:?%d%d$") then
    return ts
  end
  -- Store original; stream consumers interpret with site offset when needed.
  record.site_utc_offset_min = offset_min
  return ts
end

function normalize(tag, timestamp, record)
  local equipment_id = trim(record.equipment_id)
  local raw_code = trim(record.raw_code)
  if not equipment_id or not raw_code then
    record.malformed = true
    record.reason = "missing_fields"
    return 1, timestamp, record
  end

  local vendor = detect_vendor(tag, record)
  local mapped = status_map.lookup(vendor, raw_code)
  if not mapped then
    record.malformed = true
    record.reason = "unknown_status_code"
    record.vendor = vendor
    record.raw_code = raw_code
    return 1, timestamp, record
  end

  local offset_min = os.getenv("SITE_UTC_OFFSET_MIN") or "-480"
  local out = {
    ts = to_utc_iso(record, offset_min),
    equipment_id = equipment_id,
    status = mapped.status,
    reason = mapped.reason,
    vendor = vendor,
    raw_code = tostring(raw_code),
    fault_code = record.fault_code,
  }
  return 1, timestamp, out
end
