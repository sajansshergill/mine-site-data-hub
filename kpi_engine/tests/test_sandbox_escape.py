import pytest

from kpi_engine.sandbox import KpiError, run_kpi


@pytest.mark.parametrize("code", [
    "return os.time()",
    "return io.open('/etc/passwd')",
    "return require('os')",
    "return load('return 1')()",
    "return dofile('/etc/passwd')",
    "return debug.getinfo(1)",
    "return package.path",
    "return string.dump(function() end)",
    "return getmetatable('').__index.rep('x', 10)",
])
def test_dangerous_globals_unavailable(code):
    with pytest.raises(KpiError):
        run_kpi(code, {})


def test_infinite_loop_is_stopped():
    with pytest.raises(KpiError, match="budget"):
        run_kpi("while true do end", {}, max_instructions=100_000)


def test_memory_bomb_is_stopped():
    with pytest.raises(KpiError):
        run_kpi("local t = {} for i = 1, 1e8 do t[i] = string.rep('x', 100) end return 1", {},
                max_memory=4 * 1024 * 1024, max_instructions=10**9)


def test_non_numeric_result_rejected():
    with pytest.raises(KpiError, match="number"):
        run_kpi("return 'hello'", {})


def test_syntax_error_reported():
    with pytest.raises(KpiError, match="compile"):
        run_kpi("return (", {})