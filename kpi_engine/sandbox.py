"""Run untrusted Lua KPI code safely.

- Fresh LuaRuntime per run, with only a whitelisted set of globals.
- No os, io, require, load, dofile, debug, package, collectgarbage, string.dump.
- Instruction budget enforced with a debug hook set from Python before the sandbox is locked.
- Memory capped via lupa's max_memory.
"""
from __future__ import annotations

from typing import Any

from lupa import LuaError, LuaMemoryError, LuaRuntime


class KpiError(Exception):
    pass


SAFE_GLOBALS = ["assert", "error", "ipairs", "next", "pairs", "pcall", "select", "tonumber", "tostring",
                "type", "unpack", "math", "string", "table"]

_BOOT = """
local budget = ...
local count = 0
debug.sethook(function()
  count = count + 1000
  if count > budget then error("instruction budget exceeded", 2) end
end, "", 1000)
"""

_LOCK = """
local safe = {}
for _, name in ipairs({%s}) do safe[name] = _G[name] end
safe.string = { byte = string.byte, char = string.char, find = string.find, format = string.format,
  gmatch = string.gmatch, gsub = string.gsub, len = string.len, lower = string.lower, match = string.match,
  rep = string.rep, reverse = string.reverse, sub = string.sub, upper = string.upper }
return safe
"""


def _to_lua(lua: LuaRuntime, value: Any) -> Any:
    if isinstance(value, dict):
        t = lua.table()
        for k, v in value.items():
            t[k] = _to_lua(lua, v)
        return t
    if isinstance(value, (list, tuple)):
        return lua.table(*[_to_lua(lua, v) for v in value])
    return value


def run_kpi(code: str, inputs: dict[str, Any], params: dict[str, Any] | None = None,
            max_instructions: int = 1_000_000, max_memory: int = 16 * 1024 * 1024) -> float | None:
    lua = LuaRuntime(unpack_returned_tuples=True, register_eval=False, register_builtins=False,
                     max_memory=max_memory)
    try:
        lua.execute(_BOOT, max_instructions)
        safe_env = lua.execute(_LOCK % ", ".join(f'"{g}"' for g in SAFE_GLOBALS))
        safe_env["inputs"] = _to_lua(lua, inputs)
        safe_env["params"] = _to_lua(lua, params or {})
        compiled = lua.eval("function(src, env) return load(src, 'kpi', 't', env) end")(code, safe_env)
        chunk, err = compiled if isinstance(compiled, tuple) else (compiled, None)
        if chunk is None:
            raise KpiError(f"KPI code failed to compile: {err}")
        result = chunk()
    except (LuaError, LuaMemoryError) as exc:
        raise KpiError(str(exc)) from exc
    if result is None:
        return None
    if isinstance(result, bool) or not isinstance(result, (int, float)):
        raise KpiError(f"KPI must return a number or nil, got {type(result).__name__}")
    return float(result)