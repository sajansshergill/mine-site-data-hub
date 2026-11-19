-- busted tests for equipment log normalization
package.path = package.path .. ";../lua/?.lua;./fluent-bit/lua/?.lua;lua/?.lua"

describe("status_map", function()
  local status_map = require("status_map")

  it("maps VENDOR_A numeric codes", function()
    local m = status_map.lookup("VENDOR_A", "3")
    assert.are.equal("DOWN", m.status)
    assert.are.equal("UNPLANNED_BREAKDOWN", m.reason)
  end)

  it("maps VENDOR_B words", function()
    local m = status_map.lookup("VENDOR_B", "RUN")
    assert.are.equal("RUNNING", m.status)
  end)

  it("maps VENDOR_C abbreviations", function()
    local m = status_map.lookup("VENDOR_C", "STBY")
    assert.are.equal("STANDBY", m.status)
    assert.are.equal("SHIFT_CHANGE", m.reason)
  end)

  it("returns nil for unknown codes", function()
    assert.is_nil(status_map.lookup("VENDOR_A", "99"))
  end)
end)

describe("normalize_equipment_log", function()
  -- load file and expose normalize; stub require for status_map already on path
  local chunk = assert(loadfile("../lua/normalize_equipment_log.lua") or loadfile("fluent-bit/lua/normalize_equipment_log.lua") or loadfile("lua/normalize_equipment_log.lua"))
  chunk()

  it("normalizes a VENDOR_A record", function()
    local code, _, out = normalize("equipment.vendor_a", 0, {
      ts = "2026-11-19 06:15:32",
      equipment_id = "HT01",
      raw_code = "0",
    })
    assert.are.equal(1, code)
    assert.are.equal("HT01", out.equipment_id)
    assert.are.equal("RUNNING", out.status)
    assert.are.equal("VENDOR_A", out.vendor)
    assert.are.equal("0", out.raw_code)
    assert.is_nil(out.malformed)
  end)

  it("normalizes a VENDOR_B record", function()
    local _, _, out = normalize("equipment.vendor_b", 0, {
      ts = "11/19/2026 06:15:32 AM PST",
      equipment_id = "SH01",
      raw_code = "FAULT",
    })
    assert.are.equal("DOWN", out.status)
    assert.are.equal("VENDOR_B", out.vendor)
  end)

  it("marks unknown codes malformed", function()
    local _, _, out = normalize("equipment.vendor_a", 0, {
      ts = "2026-11-19 06:15:32",
      equipment_id = "HT01",
      raw_code = "99",
    })
    assert.is_true(out.malformed)
  end)

  it("marks missing fields malformed", function()
    local _, _, out = normalize("equipment.vendor_a", 0, { ts = "2026-11-19 06:15:32" })
    assert.is_true(out.malformed)
  end)
end)
