from __future__ import annotations

from pathlib import Path
import os
from random import Random
import shutil
from typing import Any

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb_tools.runner import get_runner


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RTL_DIR = PROJECT_ROOT / "rtl"
QUEUE_CAPACITY1_SIM_BUILD = PROJECT_ROOT / "build" / "sim" / "queue_capacity1"
QUEUE_CAPACITY3_SIM_BUILD = PROJECT_ROOT / "build" / "sim" / "queue_capacity3"
QUEUE_CAPACITY4_SIM_BUILD = PROJECT_ROOT / "build" / "sim" / "queue_capacity4"
QUEUE_CAPACITY300_SIM_BUILD = PROJECT_ROOT / "build" / "sim" / "queue_capacity300"

WIDTH = 8
CAPACITY1_PARAMETERS = {
    "CAPACITY": 1,
    "WIDTH": WIDTH,
}
CAPACITY3_PARAMETERS = {
    "CAPACITY": 3,
    "WIDTH": WIDTH,
}
CAPACITY4_PARAMETERS = {
    "CAPACITY": 4,
    "WIDTH": WIDTH,
}
CAPACITY300_PARAMETERS = {
    "CAPACITY": 300,
    "WIDTH": 16,
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


async def _cycle(dut: Any, *, push: bool, pop: bool, value: int = 0) -> int:
    dut.data_i.value = value
    dut.data_push_i.value = int(push)
    dut.data_pop_i.value = int(pop)
    await RisingEdge(dut.clk_i)
    await Timer(1, unit="ns")
    dut.data_push_i.value = 0
    dut.data_pop_i.value = 0
    return int(dut.data_o.value)


def _start_clock(dut: Any):
    clock = Clock(dut.clk_i, 10, unit="ns")
    cocotb.start_soon(clock.start(start_high=False))


def _assert_indices_in_range(dut: Any, capacity: int):
    start_idx = int(dut.start_idx.value)
    end_idx = int(dut.end_idx.value)

    assert 0 <= start_idx < capacity, (
        f"start_idx must stay inside 0..{capacity - 1}, got {start_idx}"
    )
    assert 0 <= end_idx < capacity, (
        f"end_idx must stay inside 0..{capacity - 1}, got {end_idx}"
    )


def _assert_flags_match_model(dut: Any, model: list[int], capacity: int):
    assert int(dut.empty_o.value) == int(len(model) == 0), (
        f"empty_o mismatch: model length is {len(model)}"
    )
    assert int(dut.full_o.value) == int(len(model) == capacity), (
        f"full_o mismatch: model length is {len(model)}"
    )


async def _run_model_sequence(dut: Any, *, capacity: int, seed: int):
    rng = Random(seed)
    model: list[int] = []

    _start_clock(dut)
    await _reset(dut)

    directed_ops = [
        (True, False),
        (True, False),
        (False, True),
        (True, True),
        (False, False),
        (False, True),
        (True, True),
    ]
    random_ops = [
        (bool(rng.getrandbits(1)), bool(rng.getrandbits(1))) for _ in range(80)
    ]

    for step, (push, pop) in enumerate(directed_ops + random_ops):
        value = (0x80 + step) & 0xFF
        expected_pop = None

        if push and pop:
            if model:
                expected_pop = model.pop(0)
                model.append(value)
            else:
                model.append(value)
        elif push:
            if len(model) < capacity:
                model.append(value)
        elif pop and model:
            expected_pop = model.pop(0)

        observed = await _cycle(dut, push=push, pop=pop, value=value)

        if expected_pop is not None:
            assert observed == expected_pop, (
                f"model mismatch at step {step}: push={push} pop={pop}, "
                f"expected pop 0x{expected_pop:02x}, observed 0x{observed:02x}"
            )

        _assert_flags_match_model(dut, model, capacity)
        _assert_indices_in_range(dut, capacity)


@cocotb.test()
async def queue_pops_all_entries_then_reports_empty(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    values = [0x11, 0x22, 0x33]
    for value in values:
        await _push(dut, value)

    for expected in values:
        observed = await _pop(dut)
        assert observed == expected, (
            f"queue must pop in FIFO order: expected 0x{expected:02x}, "
            f"observed 0x{observed:02x}"
        )

    assert int(dut.empty_o.value) == 1, (
        "queue must assert empty after every queued entry has been popped"
    )
    assert int(dut.full_o.value) == 0


@cocotb.test()
async def queue_pop_when_empty_preserves_state_and_output(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    before = int(dut.data_o.value)
    observed = await _pop(dut)

    assert observed == before
    assert int(dut.empty_o.value) == 1
    assert int(dut.full_o.value) == 0
    _assert_indices_in_range(dut, capacity=4)


@cocotb.test()
async def queue_simultaneous_push_pop_when_empty_enqueues_value(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    before = int(dut.data_o.value)
    observed = await _push_and_pop(dut, 0x5A)

    assert observed == before
    assert int(dut.empty_o.value) == 0
    assert int(dut.full_o.value) == 0

    observed = await _pop(dut)
    assert observed == 0x5A
    assert int(dut.empty_o.value) == 1


@cocotb.test()
async def queue_pop_from_full_clears_full(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in [0x10, 0x20, 0x30, 0x40]:
        await _push(dut, value)

    assert int(dut.full_o.value) == 1

    observed = await _pop(dut)

    assert observed == 0x10
    assert int(dut.full_o.value) == 0, (
        "a pop from a full queue must clear full_o because one slot is free"
    )
    assert int(dut.empty_o.value) == 0


@cocotb.test()
async def queue_simultaneous_push_pop_keeps_length_when_not_full(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in [0x10, 0x20, 0x30]:
        await _push(dut, value)

    observed = await _push_and_pop(dut, 0x40)

    assert observed == 0x10, (
        "simultaneous push/pop must pop the oldest existing entry"
    )
    assert int(dut.full_o.value) == 0, (
        "simultaneous push/pop on a non-full queue must keep the occupancy "
        "unchanged instead of making the queue full"
    )
    assert int(dut.empty_o.value) == 0


@cocotb.test()
async def queue_simultaneous_push_pop_keeps_full_when_full(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in [0x10, 0x20, 0x30, 0x40]:
        await _push(dut, value)

    assert int(dut.full_o.value) == 1

    observed = await _push_and_pop(dut, 0x50)

    assert observed == 0x10, (
        "simultaneous push/pop while full must pop the oldest existing entry"
    )
    assert int(dut.full_o.value) == 1, (
        "simultaneous push/pop while full must keep occupancy at capacity"
    )
    assert int(dut.empty_o.value) == 0


@cocotb.test()
async def queue_push_wraps_after_tail_reaches_capacity(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in [0x10, 0x20, 0x30, 0x40]:
        await _push(dut, value)

    for expected in [0x10, 0x20, 0x30]:
        observed = await _pop(dut)
        assert observed == expected

    await _push(dut, 0x50)

    for expected in [0x40, 0x50]:
        observed = await _pop(dut)
        assert observed == expected, (
            "queue must write new data to index 0 when the logical tail "
            f"reaches capacity: expected 0x{expected:02x}, "
            f"observed 0x{observed:02x}"
        )

    assert int(dut.empty_o.value) == 1


@cocotb.test()
async def queue_accepts_push_after_full_drain_at_wrap_boundary(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in [0x10, 0x20, 0x30, 0x40]:
        await _push(dut, value)

    for expected in [0x10, 0x20, 0x30, 0x40]:
        observed = await _pop(dut)
        assert observed == expected

    assert int(dut.empty_o.value) == 1

    await _push(dut, 0x50)

    observed = await _pop(dut)
    assert observed == 0x50, (
        "queue must remain usable after the read pointer advances exactly "
        f"to capacity: expected 0x50, observed 0x{observed:02x}"
    )
    assert int(dut.empty_o.value) == 1


@cocotb.test()
async def queue_simultaneous_push_pop_full_preserves_new_tail(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in [0x10, 0x20, 0x30, 0x40]:
        await _push(dut, value)

    observed = await _push_and_pop(dut, 0x50)
    assert observed == 0x10
    assert int(dut.full_o.value) == 1

    for expected in [0x20, 0x30, 0x40, 0x50]:
        observed = await _pop(dut)
        assert observed == expected, (
            "simultaneous push/pop while full must append the new value at "
            f"the wrapped tail: expected 0x{expected:02x}, "
            f"observed 0x{observed:02x}"
        )

    assert int(dut.empty_o.value) == 1


@cocotb.test()
async def queue_capacity3_wraparound_preserves_fifo_order(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in [0x10, 0x20, 0x30]:
        await _push(dut, value)

    assert int(dut.full_o.value) == 1

    for expected in [0x10, 0x20]:
        observed = await _pop(dut)
        assert observed == expected

    await _push(dut, 0x40)

    for expected in [0x30, 0x40]:
        observed = await _pop(dut)
        assert observed == expected, (
            "CAPACITY=3 queue must preserve FIFO order after tail wrap: "
            f"expected 0x{expected:02x}, observed 0x{observed:02x}"
        )

    assert int(dut.empty_o.value) == 1


@cocotb.test()
async def queue_capacity3_full_push_pop_preserves_new_tail(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in [0x10, 0x20, 0x30]:
        await _push(dut, value)

    observed = await _push_and_pop(dut, 0x40)
    assert observed == 0x10
    assert int(dut.full_o.value) == 1

    for expected in [0x20, 0x30, 0x40]:
        observed = await _pop(dut)
        assert observed == expected, (
            "CAPACITY=3 simultaneous push/pop while full must retain the "
            f"new tail: expected 0x{expected:02x}, observed 0x{observed:02x}"
        )

    assert int(dut.empty_o.value) == 1


@cocotb.test()
async def queue_end_index_stays_in_range_when_full(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in [0x10, 0x20, 0x30, 0x40]:
        await _push(dut, value)

    assert int(dut.full_o.value) == 1
    _assert_indices_in_range(dut, capacity=4)
    assert int(dut.end_idx.value) == 0, (
        "end_idx should wrap to 0 when the queue is full from index 0"
    )


@cocotb.test()
async def queue_start_index_stays_in_range_after_full_drain(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in [0x10, 0x20, 0x30, 0x40]:
        await _push(dut, value)

    for expected in [0x10, 0x20, 0x30, 0x40]:
        observed = await _pop(dut)
        assert observed == expected

    assert int(dut.empty_o.value) == 1
    _assert_indices_in_range(dut, capacity=4)
    assert int(dut.start_idx.value) == 0, (
        "start_idx should wrap to 0 after popping the entry at index 3"
    )


@cocotb.test()
async def queue_end_index_stays_in_range_after_partial_drain(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in [0x10, 0x20, 0x30, 0x40]:
        await _push(dut, value)

    for expected in [0x10, 0x20, 0x30]:
        observed = await _pop(dut)
        assert observed == expected

    _assert_indices_in_range(dut, capacity=4)
    assert int(dut.end_idx.value) == 0, (
        "end_idx should wrap to 0 when start_idx + len equals capacity"
    )


@cocotb.test()
async def queue_capacity1_model_sequence(dut: Any):
    await _run_model_sequence(dut, capacity=1, seed=0xC001)


@cocotb.test()
async def queue_capacity3_model_sequence(dut: Any):
    await _run_model_sequence(dut, capacity=3, seed=0xC003)


@cocotb.test()
async def queue_capacity4_model_sequence(dut: Any):
    await _run_model_sequence(dut, capacity=4, seed=0xC004)


@cocotb.test()
async def queue_default_idx_bits_scale_with_capacity(dut: Any):
    _start_clock(dut)
    await _reset(dut)

    for value in range(300):
        await _push(dut, value)
        if value < 299:
            assert int(dut.full_o.value) == 0, (
                "CAPACITY=300 queue asserted full before accepting 300 entries"
            )

    assert int(dut.full_o.value) == 1
    _assert_indices_in_range(dut, capacity=300)

    await _push(dut, 0xCAFE)

    for expected in range(300):
        observed = await _pop(dut)
        assert observed == expected, (
            "CAPACITY=300 queue must preserve all entries after reaching full: "
            f"expected 0x{expected:04x}, observed 0x{observed:04x}"
        )

    assert int(dut.empty_o.value) == 1


def _build_runner(build_dir: Path, parameters: dict[str, int]):
    sim = os.getenv("SIM", "verilator")
    runner = get_runner(sim)

    if build_dir.exists():
        shutil.rmtree(build_dir)

    runner.build(
        sources=[RTL_DIR / "queue.sv"],
        includes=[RTL_DIR],
        hdl_toplevel="queue",
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
        hdl_toplevel="queue",
        test_module=__name__,
        build_dir=build_dir,
        testcase=testcase,
        parameters=parameters,
        waves=WAVES,
    )


@pytest.fixture(scope="module")
def queue_capacity1_runner():
    return _build_runner(QUEUE_CAPACITY1_SIM_BUILD, CAPACITY1_PARAMETERS)


@pytest.fixture(scope="module")
def queue_capacity3_runner():
    return _build_runner(QUEUE_CAPACITY3_SIM_BUILD, CAPACITY3_PARAMETERS)


@pytest.fixture(scope="module")
def queue_capacity4_runner():
    return _build_runner(QUEUE_CAPACITY4_SIM_BUILD, CAPACITY4_PARAMETERS)


def test_queue_pops_all_entries_then_reports_empty(queue_capacity4_runner):
    _run_cocotb_test(
        queue_capacity4_runner,
        QUEUE_CAPACITY4_SIM_BUILD,
        "queue_pops_all_entries_then_reports_empty",
        CAPACITY4_PARAMETERS,
    )


def test_queue_pop_when_empty_preserves_state_and_output(queue_capacity4_runner):
    _run_cocotb_test(
        queue_capacity4_runner,
        QUEUE_CAPACITY4_SIM_BUILD,
        "queue_pop_when_empty_preserves_state_and_output",
        CAPACITY4_PARAMETERS,
    )


def test_queue_simultaneous_push_pop_when_empty_enqueues_value(queue_capacity4_runner):
    _run_cocotb_test(
        queue_capacity4_runner,
        QUEUE_CAPACITY4_SIM_BUILD,
        "queue_simultaneous_push_pop_when_empty_enqueues_value",
        CAPACITY4_PARAMETERS,
    )


def test_queue_pop_from_full_clears_full(queue_capacity4_runner):
    _run_cocotb_test(
        queue_capacity4_runner,
        QUEUE_CAPACITY4_SIM_BUILD,
        "queue_pop_from_full_clears_full",
        CAPACITY4_PARAMETERS,
    )


def test_queue_simultaneous_push_pop_keeps_length_when_not_full(
    queue_capacity4_runner,
):
    _run_cocotb_test(
        queue_capacity4_runner,
        QUEUE_CAPACITY4_SIM_BUILD,
        "queue_simultaneous_push_pop_keeps_length_when_not_full",
        CAPACITY4_PARAMETERS,
    )


def test_queue_simultaneous_push_pop_keeps_full_when_full(queue_capacity4_runner):
    _run_cocotb_test(
        queue_capacity4_runner,
        QUEUE_CAPACITY4_SIM_BUILD,
        "queue_simultaneous_push_pop_keeps_full_when_full",
        CAPACITY4_PARAMETERS,
    )


def test_queue_push_wraps_after_tail_reaches_capacity(queue_capacity4_runner):
    _run_cocotb_test(
        queue_capacity4_runner,
        QUEUE_CAPACITY4_SIM_BUILD,
        "queue_push_wraps_after_tail_reaches_capacity",
        CAPACITY4_PARAMETERS,
    )


def test_queue_accepts_push_after_full_drain_at_wrap_boundary(queue_capacity4_runner):
    _run_cocotb_test(
        queue_capacity4_runner,
        QUEUE_CAPACITY4_SIM_BUILD,
        "queue_accepts_push_after_full_drain_at_wrap_boundary",
        CAPACITY4_PARAMETERS,
    )


def test_queue_simultaneous_push_pop_full_preserves_new_tail(queue_capacity4_runner):
    _run_cocotb_test(
        queue_capacity4_runner,
        QUEUE_CAPACITY4_SIM_BUILD,
        "queue_simultaneous_push_pop_full_preserves_new_tail",
        CAPACITY4_PARAMETERS,
    )


def test_queue_capacity3_wraparound_preserves_fifo_order(queue_capacity3_runner):
    _run_cocotb_test(
        queue_capacity3_runner,
        QUEUE_CAPACITY3_SIM_BUILD,
        "queue_capacity3_wraparound_preserves_fifo_order",
        CAPACITY3_PARAMETERS,
    )


def test_queue_capacity3_full_push_pop_preserves_new_tail(queue_capacity3_runner):
    _run_cocotb_test(
        queue_capacity3_runner,
        QUEUE_CAPACITY3_SIM_BUILD,
        "queue_capacity3_full_push_pop_preserves_new_tail",
        CAPACITY3_PARAMETERS,
    )


def test_queue_end_index_stays_in_range_when_full(queue_capacity4_runner):
    _run_cocotb_test(
        queue_capacity4_runner,
        QUEUE_CAPACITY4_SIM_BUILD,
        "queue_end_index_stays_in_range_when_full",
        CAPACITY4_PARAMETERS,
    )


def test_queue_start_index_stays_in_range_after_full_drain(queue_capacity4_runner):
    _run_cocotb_test(
        queue_capacity4_runner,
        QUEUE_CAPACITY4_SIM_BUILD,
        "queue_start_index_stays_in_range_after_full_drain",
        CAPACITY4_PARAMETERS,
    )


def test_queue_end_index_stays_in_range_after_partial_drain(queue_capacity4_runner):
    _run_cocotb_test(
        queue_capacity4_runner,
        QUEUE_CAPACITY4_SIM_BUILD,
        "queue_end_index_stays_in_range_after_partial_drain",
        CAPACITY4_PARAMETERS,
    )


def test_queue_capacity1_model_sequence(queue_capacity1_runner):
    _run_cocotb_test(
        queue_capacity1_runner,
        QUEUE_CAPACITY1_SIM_BUILD,
        "queue_capacity1_model_sequence",
        CAPACITY1_PARAMETERS,
    )


def test_queue_capacity3_model_sequence(queue_capacity3_runner):
    _run_cocotb_test(
        queue_capacity3_runner,
        QUEUE_CAPACITY3_SIM_BUILD,
        "queue_capacity3_model_sequence",
        CAPACITY3_PARAMETERS,
    )


def test_queue_capacity4_model_sequence(queue_capacity4_runner):
    _run_cocotb_test(
        queue_capacity4_runner,
        QUEUE_CAPACITY4_SIM_BUILD,
        "queue_capacity4_model_sequence",
        CAPACITY4_PARAMETERS,
    )
