set shell := ["zsh", "-cu"]

default:
    mkdir -p build
    yosys -p "read_verilog -sv rtl/top.sv; synth_gowin -top top -json build/top.json -family gw2a"
    nextpnr-himbaechel --json build/top.json --write build/top_pnr.json --device GW2AR-LV18QN88C8/I7 --vopt family=GW2A-18C --vopt cst=constraints/tangnano20k.cst
    gowin_pack -d GW2A-18C -o build/top.fs build/top_pnr.json

test:
    mkdir -p waves
    verilator --binary --timing --assert --trace -Wall -Wno-DECLFILENAME -Wno-PROCASSINIT --top-module top_tb rtl/top.sv tb/top_tb.sv
    ./obj_dir/Vtop_tb

wave: test
    if command -v surfer >/dev/null; then surfer waves/top_tb.vcd; elif command -v gtkwave >/dev/null; then gtkwave waves/top_tb.vcd; else echo "Waveform written to waves/top_tb.vcd"; fi

program: default
    openFPGALoader -b tangnano20k build/top.fs

flash: default
    openFPGALoader -b tangnano20k -f build/top.fs

clean:
    rm -rf build
