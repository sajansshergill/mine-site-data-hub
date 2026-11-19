-- Generated from config/status_codes.yaml (keep in sync).
local M = {}

M.VENDOR_A = {
  ["0"] = { status = "RUNNING", reason = nil },
  ["1"] = { status = "STANDBY", reason = "NO_OPERATOR" },
  ["2"] = { status = "DELAY", reason = "QUEUE" },
  ["3"] = { status = "DOWN", reason = "UNPLANNED_BREAKDOWN" },
  ["4"] = { status = "DOWN", reason = "PLANNED_MAINTENANCE" },
}

M.VENDOR_B = {
  RUN = { status = "RUNNING", reason = nil },
  IDLE = { status = "STANDBY", reason = "NO_OPERATOR" },
  WAIT = { status = "DELAY", reason = "QUEUE" },
  FAULT = { status = "DOWN", reason = "UNPLANNED_BREAKDOWN" },
  PM = { status = "DOWN", reason = "PLANNED_MAINTENANCE" },
  REFUEL = { status = "DELAY", reason = "REFUEL" },
}

M.VENDOR_C = {
  OK = { status = "RUNNING", reason = nil },
  STBY = { status = "STANDBY", reason = "SHIFT_CHANGE" },
  DLY = { status = "DELAY", reason = "OPERATIONAL" },
  BRKDN = { status = "DOWN", reason = "UNPLANNED_BREAKDOWN" },
  SVC = { status = "DOWN", reason = "PLANNED_MAINTENANCE" },
}

function M.lookup(vendor, raw_code)
  local table_for_vendor = M[vendor]
  if not table_for_vendor then
    return nil
  end
  return table_for_vendor[tostring(raw_code)]
end

return M
