from pathlib import Path
import os

import cocotb
from copra.discovery import discover
from copra.generation import generate_stub


@cocotb.test()
async def generate_dut_stub(dut):
    out_dir = Path(os.getenv("COPRA_STUB_DIR", str(Path.cwd())))
    stub_path = generate_stub(await discover(dut), out_dir)
    cocotb.log.info("Copra stub written to %s", stub_path)
