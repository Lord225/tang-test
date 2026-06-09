from __future__ import annotations

from pathlib import Path
import os
from typing import TYPE_CHECKING

import cocotb
import pytest
from cocotb.triggers import Timer
from cocotb_tools.runner import get_runner

if TYPE_CHECKING:
    from tb.copra_stubs.fixedpoint_dut import FixedpointDut


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RTL_DIR = PROJECT_ROOT / "rtl"
SIM_BUILD = PROJECT_ROOT / "build" / "sim" / "fixedpoint"
TOTAL_BITS = 16
FRAC_BITS = 8
MAX_VALUE = (1 << TOTAL_BITS) - 1
CASES = [
    (0x0000, 0x0000),  # 0.0, 0.0
    (0x0001, 0x0001),  # 
    (0x0080, 0x0080),  # 0.5, 0.5
    (0x0100, 0x0100),  # 1.0, 1.0
    (0x0180, 0x0200),  # 1.5, 2.0
    (0x1000, 0x0010),  # 16.0, 0.0625
    (0x1234, 0x4321),  # 
    (0x7F00, 0x0200),  # 127.0, 2.0
    (0x8000, 0x8000),  # -128.0, -128.0
    (0xF000, 0x1000),  # -16.0, 16.0
    (0xFFFF, 0x0001),  # -0.0039, 0.0039
    (0xFFFF, 0x0100),  # -0.0039, 1.0
    (0xFFFF, 0xFFFF),  # -0.0039, -0.0039
]
WAVES = bool(os.getenv("WAVES"))


def _mask(value: int) -> int:
    return value & MAX_VALUE


def _saturate(value: int) -> int:
    return min(value, MAX_VALUE)


def _overflow_flag(a: int, b: int) -> bool:
    return a + b > MAX_VALUE


def _fixed_mul(a: int, b: int) -> int:
    return _mask((a * b) >> FRAC_BITS)


def _fixed_saturating_mul(a: int, b: int) -> int:
    return _saturate((a * b) >> FRAC_BITS)


async def _drive_inputs(dut: FixedpointDut, a: int, b: int):
    dut.a.value = a
    dut.b.value = b
    await Timer(1, unit="ns")


@cocotb.test()
async def fixedpoint_add_wraps(dut: FixedpointDut):
    for a, b in CASES:
        await _drive_inputs(dut, a, b)
        assert int(dut.sum.value) == _mask(a + b)


@cocotb.test()
async def fixedpoint_saturating_add_clamps(dut: FixedpointDut):
    for a, b in CASES:
        await _drive_inputs(dut, a, b)
        assert int(dut.sat_sum.value) == _saturate(a + b)


@cocotb.test()
async def fixedpoint_overflowing_add_reports_result_and_overflow(dut: FixedpointDut):
    for a, b in CASES:
        await _drive_inputs(dut, a, b)
        assert int(dut.overflow_sum_result.value) == _mask(a + b)
        assert bool(dut.overflow_sum_overflow.value) == _overflow_flag(a, b)


@cocotb.test()
async def fixedpoint_mul_scales_product(dut: FixedpointDut):
    for a, b in CASES:
        await _drive_inputs(dut, a, b)
        assert int(dut.product.value) == _fixed_mul(a, b)


@cocotb.test()
async def fixedpoint_saturating_mul_clamps(dut: FixedpointDut):
    for a, b in CASES:
        await _drive_inputs(dut, a, b)
        assert int(dut.sat_product.value) == _fixed_saturating_mul(a, b)


@pytest.fixture(scope="module")
def fixedpoint_runner():
    sim = os.getenv("SIM", "verilator")
    runner = get_runner(sim)

    runner.build(
        sources=[RTL_DIR / "fixedpoint_dut.sv"],
        includes=[RTL_DIR],
        hdl_toplevel="fixedpoint_dut",
        parameters={
            "FRAC_BITS": FRAC_BITS,
        },
        build_dir=SIM_BUILD,
        always=True,
        waves=WAVES,
    )

    return runner


def _run_cocotb_test(runner, testcase: str):
    runner.test(
        hdl_toplevel="fixedpoint_dut",
        test_module=__name__,
        build_dir=SIM_BUILD,
        testcase=testcase,
        parameters={
            "FRAC_BITS": FRAC_BITS,
        },
        waves=WAVES,
    )


def test_fixedpoint_add_wraps(fixedpoint_runner):
    _run_cocotb_test(fixedpoint_runner, "fixedpoint_add_wraps")


def test_fixedpoint_saturating_add_clamps(fixedpoint_runner):
    _run_cocotb_test(fixedpoint_runner, "fixedpoint_saturating_add_clamps")


def test_fixedpoint_overflowing_add_reports_result_and_overflow(fixedpoint_runner):
    _run_cocotb_test(
        fixedpoint_runner,
        "fixedpoint_overflowing_add_reports_result_and_overflow",
    )

def test_fixedpoint_mul_scales_product(fixedpoint_runner):
    _run_cocotb_test(fixedpoint_runner, "fixedpoint_mul_scales_product")


def test_fixedpoint_saturating_mul_clamps(fixedpoint_runner):
    _run_cocotb_test(fixedpoint_runner, "fixedpoint_saturating_mul_clamps")
