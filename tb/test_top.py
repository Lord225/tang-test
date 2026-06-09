from __future__ import annotations

from pathlib import Path
import os
from typing import TYPE_CHECKING

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb_tools.runner import get_runner

if TYPE_CHECKING:
    from tb.copra_stubs.top import Top


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RTL_DIR = PROJECT_ROOT / "rtl"
SIM_BUILD = PROJECT_ROOT / "build" / "sim" / "top"


async def _reset(dut: Top):
    dut.btn1.value = 1
    dut.btn2.value = 0
    await Timer(1, unit="ns")
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert int(dut.led.value) == 0x3F

    dut.btn1.value = 0
    await RisingEdge(dut.clk)


async def _press_count_button(dut: Top):
    dut.btn2.value = 1
    await RisingEdge(dut.clk)
    dut.btn2.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


@cocotb.test()
async def top_resets_and_counts_on_btn2_edges(dut: Top):
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start(start_high=False))

    await _reset(dut)

    for expected_count in range(1, 5):
        await _press_count_button(dut)
        assert int(dut.led.value) == ((~expected_count) & 0x3F)

    dut.btn1.value = 1
    await Timer(1, unit="ns")
    assert int(dut.led.value) == 0x3F


def test_top_runner():
    sim = os.getenv("SIM", "verilator")
    runner = get_runner(sim)

    runner.build(
        sources=[
            RTL_DIR / "top.sv",
        ],
        includes=[RTL_DIR],
        hdl_toplevel="top",
        build_dir=SIM_BUILD,
        always=True,
    )

    runner.test(
        hdl_toplevel="top",
        test_module=__name__,
        build_dir=SIM_BUILD,
    )
