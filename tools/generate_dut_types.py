from pathlib import Path
import os
import sys

from cocotb_tools.runner import get_runner


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RTL_DIR = PROJECT_ROOT / "rtl"
STUB_DIR = PROJECT_ROOT / "tb" / "copra_stubs"
SIM_BUILD = PROJECT_ROOT / "build" / "sim" / "copra"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _run_stubgen(
    *,
    hdl_toplevel: str,
    sources: list[Path],
    build_dir: Path,
    stub_filename: str,
    parameters: dict[str, int] | None = None,
) -> None:
    sim = os.getenv("SIM", "verilator")
    runner = get_runner(sim)

    runner.build(
        sources=sources,
        includes=[RTL_DIR],
        hdl_toplevel=hdl_toplevel,
        parameters=parameters or {},
        build_dir=build_dir,
        always=True,
    )

    runner.test(
        hdl_toplevel=hdl_toplevel,
        test_module="tb.copra_autostub",
        build_dir=build_dir,
        parameters=parameters or {},
        extra_env={
            "COPRA_STUB_DIR": str(STUB_DIR),
            "COPRA_STUB_FILENAME": stub_filename,
        },
    )


def main() -> None:
    _run_stubgen(
        hdl_toplevel="fixedpoint_dut",
        sources=[RTL_DIR / "fixedpoint_dut.sv"],
        build_dir=SIM_BUILD / "fixedpoint",
        stub_filename="fixedpoint_dut.pyi",
        parameters={"FRAC_BITS": 8},
    )
    _run_stubgen(
        hdl_toplevel="math_utils_dut",
        sources=[RTL_DIR / "math_utils_dut.sv"],
        build_dir=SIM_BUILD / "math_utils",
        stub_filename="math_utils_dut.pyi",
    )
    _run_stubgen(
        hdl_toplevel="top",
        sources=[RTL_DIR / "top.sv"],
        build_dir=SIM_BUILD / "top",
        stub_filename="top.pyi",
    )


if __name__ == "__main__":
    main()
