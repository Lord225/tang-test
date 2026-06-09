from __future__ import annotations

from pathlib import Path
import os
import shutil
from typing import Any

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb_tools.runner import get_runner


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RTL_DIR = PROJECT_ROOT / "rtl"
STACK_DEPTH4_SIM_BUILD = PROJECT_ROOT / "build" / "sim" / "stack_depth4"
STACK_DEPTH300_SIM_BUILD = PROJECT_ROOT / "build" / "sim" / "stack_depth300"

WIDTH = 8
DEPTH4_PARAMETERS = {
    "DEPTH": 4,
    "WIDTH": WIDTH,
}
DEPTH300_DEFAULT_IDX_PARAMETERS = {
    "DEPTH": 300,
    "WIDTH": WIDTH,
}
WAVES = bool(os.getenv("WAVES"))


async def _reset(dut: Any):
    dut.data_i.value = 0
    dut.data_push_i.value = 0
    dut.data_pop_i.value = 0
    dut.nrst_i.value = 1
    await Timer(1, unit="ns")

    dut.nrst_i.value = 0
    await Timer(1, unit="ns")
    assert int(dut.empty_o.value) == 1
    assert int(dut.full_o.value) == 0

    dut.nrst_i.value = 1
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")


async def _push(dut: Any, value: int):
    dut.data_i.value = value
    dut.data_push_i.value = 1
    dut.data_pop_i.value = 0
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.data_push_i.value = 0


async def _pop(dut: Any) -> int:
    dut.data_push_i.value = 0
    dut.data_pop_i.value = 1
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.data_pop_i.value = 0
    return int(dut.data_o.value)


async def _push_and_pop(dut: Any, value: int) -> int:
    dut.data_i.value = value
    dut.data_push_i.value = 1
    dut.data_pop_i.value = 1
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.data_push_i.value = 0
    dut.data_pop_i.value = 0
    return int(dut.data_o.value)


def _start_clock(dut: Any):
    clock = Clock(dut.clk_i, 10, unit="ns")
    cocotb.start_soon(clock.start(start_high=False))


@cocotb.test()
async def stack_preserves_lifo_order(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    values = [0x11, 0x22, 0x33]
    for value in values:
        await _push(dut, value)

    for expected in reversed(values):
        observed = await _pop(dut)
        assert observed == expected, (
            f"stack must pop in LIFO order: expected 0x{expected:02x}, "
            f"observed 0x{observed:02x}"
        )


@cocotb.test()
async def stack_depth_entries_fit_before_full(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in [0x10, 0x20, 0x30]:
        await _push(dut, value)
        assert int(dut.full_o.value) == 0, (
            "DEPTH=4 stack asserted full before accepting four entries"
        )

    await _push(dut, 0x40)
    assert int(dut.full_o.value) == 1


@cocotb.test()
async def stack_push_when_full_preserves_contents(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    values = [0x10, 0x20, 0x30, 0x40]
    for value in values:
        await _push(dut, value)

    assert int(dut.full_o.value) == 1

    await _push(dut, 0x99)

    for expected in reversed(values):
        observed = await _pop(dut)
        assert observed == expected, (
            f"push while full must preserve stack contents: "
            f"expected 0x{expected:02x}, observed 0x{observed:02x}"
        )


@cocotb.test()
async def stack_pop_when_empty_preserves_empty_state_and_output(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    before = int(dut.data_o.value)
    observed = await _pop(dut)

    assert observed == before
    assert int(dut.empty_o.value) == 1
    assert int(dut.full_o.value) == 0


@cocotb.test()
async def stack_simultaneous_push_pop_replaces_top(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    await _push(dut, 0x11)

    observed = await _push_and_pop(dut, 0x22)
    assert observed == 0x11, "simultaneous push/pop should pop the old top element"
    assert int(dut.empty_o.value) == 0

    observed = await _pop(dut)
    assert observed == 0x22, (
        "simultaneous push/pop should leave the pushed element on top"
    )


@cocotb.test()
async def stack_default_idx_bits_scale_with_depth(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in range(43):
        await _push(dut, value)

    assert int(dut.full_o.value) == 0, (
        "DEPTH=300 stack asserted full after 43 entries because IDX_BITS "
        "defaults to $clog2(256) instead of scaling with DEPTH"
    )


def _build_runner(build_dir: Path, parameters: dict[str, int]):
    sim = os.getenv("SIM", "verilator")
    runner = get_runner(sim)

    if build_dir.exists():
        shutil.rmtree(build_dir)

    runner.build(
        sources=[RTL_DIR / "stack.sv"],
        includes=[RTL_DIR],
        hdl_toplevel="stack",
        parameters=parameters,
        build_args=["-Wno-WIDTHTRUNC", "-Wno-WIDTHEXPAND"],
        build_dir=build_dir,
        always=True,
        waves=WAVES,
    )

    return runner


def _run_cocotb_test(
    runner: Any,
    build_dir: Path,
    testcase: str,
    parameters: dict[str, int],
):
    runner.test(
        hdl_toplevel="stack",
        test_module=__name__,
        build_dir=build_dir,
        testcase=testcase,
        parameters=parameters,
        waves=WAVES,
    )


@pytest.fixture(scope="module")
def stack_depth4_runner():
    return _build_runner(STACK_DEPTH4_SIM_BUILD, DEPTH4_PARAMETERS)


@pytest.fixture(scope="module")
def stack_depth300_runner():
    return _build_runner(STACK_DEPTH300_SIM_BUILD, DEPTH300_DEFAULT_IDX_PARAMETERS)


def test_stack_preserves_lifo_order(stack_depth4_runner):
    _run_cocotb_test(
        stack_depth4_runner,
        STACK_DEPTH4_SIM_BUILD,
        "stack_preserves_lifo_order",
        DEPTH4_PARAMETERS,
    )


def test_stack_depth_entries_fit_before_full(stack_depth4_runner):
    _run_cocotb_test(
        stack_depth4_runner,
        STACK_DEPTH4_SIM_BUILD,
        "stack_depth_entries_fit_before_full",
        DEPTH4_PARAMETERS,
    )


def test_stack_push_when_full_preserves_contents(stack_depth4_runner):
    _run_cocotb_test(
        stack_depth4_runner,
        STACK_DEPTH4_SIM_BUILD,
        "stack_push_when_full_preserves_contents",
        DEPTH4_PARAMETERS,
    )


def test_stack_pop_when_empty_preserves_empty_state_and_output(stack_depth4_runner):
    _run_cocotb_test(
        stack_depth4_runner,
        STACK_DEPTH4_SIM_BUILD,
        "stack_pop_when_empty_preserves_empty_state_and_output",
        DEPTH4_PARAMETERS,
    )


def test_stack_simultaneous_push_pop_replaces_top(stack_depth4_runner):
    _run_cocotb_test(
        stack_depth4_runner,
        STACK_DEPTH4_SIM_BUILD,
        "stack_simultaneous_push_pop_replaces_top",
        DEPTH4_PARAMETERS,
    )


def test_stack_default_idx_bits_scale_with_depth(stack_depth300_runner):
    _run_cocotb_test(
        stack_depth300_runner,
        STACK_DEPTH300_SIM_BUILD,
        "stack_default_idx_bits_scale_with_depth",
        DEPTH300_DEFAULT_IDX_PARAMETERS,
    )
