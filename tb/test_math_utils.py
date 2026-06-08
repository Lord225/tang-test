from pathlib import Path
import os

import cocotb
import pytest
from cocotb.triggers import Timer
from cocotb_tools.runner import get_runner
import itertools

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RTL_DIR = PROJECT_ROOT / "rtl"
SIM_BUILD = PROJECT_ROOT / "build" / "sim" / "math_utils"
CASES = list(itertools.product(range(0, 0x10000, 0x1000), repeat=2))

WAVES = bool(os.getenv("WAVES"))


def _u16(value: int) -> int:
    return value & 0xFFFF


def _sat_u16_add(a: int, b: int) -> int:
    total = a + b
    return min(total, 0xFFFF)


def _overflow_flag(a: int, b: int) -> bool:
    total = a + b
    return total > 0xFFFF


async def _drive_inputs(dut, a: int, b: int):
    dut.a.value = a
    dut.b.value = b
    await Timer(1, unit="ns")


@cocotb.test()
async def add_wraps(dut):
    for a, b in CASES:
        await _drive_inputs(dut, a, b)
        assert int(dut.sum.value) == _u16(a + b)


@cocotb.test()
async def saturating_add(dut):
    for a, b in CASES:
        await _drive_inputs(dut, a, b)
        assert int(dut.sat_sum.value) == _sat_u16_add(a, b)


@cocotb.test()
async def overflowing_add(dut):
    for a, b in CASES:
        await _drive_inputs(dut, a, b)
        assert bool(dut.overflow_sum_overflow.value) == _overflow_flag(a, b)
        assert int(dut.overflow_sum_result.value) == _u16(a + b)


@pytest.fixture(scope="module")
def math_utils_runner():
    sim = os.getenv("SIM", "verilator")
    runner = get_runner(sim)

    runner.build(
        sources=[RTL_DIR / "math_utils_dut.sv"],
        includes=[RTL_DIR],
        hdl_toplevel="math_utils_dut",
        build_dir=SIM_BUILD,
        always=True,
    )

    return runner


def _run_cocotb_test(runner, testcase: str):
    runner.test(
        hdl_toplevel="math_utils_dut",
        test_module=__name__,
        build_dir=SIM_BUILD,
        testcase=testcase,
        waves=WAVES,
    )


def test_add_wraps(math_utils_runner):
    _run_cocotb_test(math_utils_runner, "add_wraps")


def test_saturating_add(math_utils_runner):
    _run_cocotb_test(math_utils_runner, "saturating_add")


def test_overflowing_add(math_utils_runner):
    _run_cocotb_test(math_utils_runner, "overflowing_add")
