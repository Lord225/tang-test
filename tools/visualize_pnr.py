#!/usr/bin/env python3
import argparse
import collections
import html
import json
import re
from pathlib import Path


BEL_RE = re.compile(r"X(\d+)Y(\d+)/(.+)")
IO_LOC_RE = re.compile(r'IO_LOC\s+"([^"]+)"\s+(\d+);')


def load_cst(path):
    pins = {}
    for line in path.read_text().splitlines():
        match = IO_LOC_RE.search(line)
        if match:
            pins[match.group(1)] = int(match.group(2))
    return pins


def summarize_cells(cells):
    placed = []
    for name, cell in cells.items():
        bel = cell.get("attributes", {}).get("NEXTPNR_BEL", "")
        match = BEL_RE.search(bel)
        if not match:
            continue
        x, y, site = match.groups()
        placed.append(
            {
                "name": name,
                "type": cell.get("type", "?"),
                "x": int(x),
                "y": int(y),
                "site": site,
                "bel": bel,
            }
        )
    return placed


def classify(cell_type):
    if cell_type in {"IBUF", "OBUF", "BUFG"}:
        return "io"
    if cell_type.startswith("DFF"):
        return "ff"
    if cell_type.startswith("LUT") or cell_type == "MUX2_LUT5":
        return "lut"
    if cell_type == "ALU":
        return "carry"
    if cell_type in {"GOWIN_GND", "GOWIN_VCC", "GSR"}:
        return "special"
    return "other"


def render(args):
    pnr = json.loads(args.pnr.read_text())
    module_name, module = next(iter(pnr["modules"].items()))
    settings = module.get("settings", {})
    cells = module.get("cells", {})
    ports = module.get("ports", {})
    pins = load_cst(args.cst)
    placed = summarize_cells(cells)
    counts = collections.Counter(cell["type"] for cell in placed)
    classes = collections.Counter(classify(cell["type"]) for cell in placed)
    min_x = min(cell["x"] for cell in placed)
    max_x = max(cell["x"] for cell in placed)
    min_y = min(cell["y"] for cell in placed)
    max_y = max(cell["y"] for cell in placed)

    by_coord = collections.defaultdict(list)
    for cell in placed:
        by_coord[(cell["x"], cell["y"])].append(cell)

    grid = []
    for y in range(max_y, min_y - 1, -1):
        row = []
        for x in range(min_x, max_x + 1):
            here = by_coord.get((x, y), [])
            if not here:
                row.append('<span class="tile empty"></span>')
                continue
            klass = classify(collections.Counter(c["type"] for c in here).most_common(1)[0][0])
            title = f'X{x}Y{y}: ' + ", ".join(f'{c["type"]} {c["site"]}' for c in here[:5])
            if len(here) > 5:
                title += f", +{len(here) - 5} more"
            row.append(f'<span class="tile {klass}" title="{html.escape(title)}">{len(here)}</span>')
        grid.append(f'<div class="grid-row">{"".join(row)}</div>')

    pin_rows = []
    for port, pin in sorted(pins.items(), key=lambda item: item[1]):
        direction = "output" if port.startswith("led") else "input"
        pin_rows.append(f"<tr><td>{html.escape(port)}</td><td>{pin}</td><td>{direction}</td><td>LVCMOS33</td></tr>")

    cell_rows = []
    for cell_type, count in counts.most_common():
        cell_rows.append(f"<tr><td>{html.escape(cell_type)}</td><td>{count}</td><td>{html.escape(classify(cell_type))}</td></tr>")

    port_chips = []
    for port, meta in ports.items():
        width = len(meta.get("bits", []))
        label = f"{port}[{width}]" if width > 1 else port
        port_chips.append(f'<span class="chip {meta.get("direction", "")}">{html.escape(label)} <b>{html.escape(meta.get("direction", ""))}</b></span>')

    html_out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tang Nano 20K Synthesis Visualization</title>
<style>
:root {{ color-scheme: light; --ink:#1f2933; --muted:#667085; --line:#d8dee8; --paper:#f7f9fc; --panel:#ffffff; --lut:#4f8cff; --ff:#16a085; --carry:#f59e0b; --io:#d9467a; --special:#7c3aed; --other:#64748b; }}
* {{ box-sizing:border-box; }} body {{ margin:0; font:14px/1.45 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color:var(--ink); background:var(--paper); }}
header {{ padding:28px 32px 18px; background:#102033; color:white; }} h1 {{ margin:0 0 8px; font-size:28px; letter-spacing:0; }} header p {{ margin:0; color:#cbd5e1; }}
main {{ max-width:1180px; margin:0 auto; padding:24px; }} section {{ margin:0 0 22px; }} h2 {{ font-size:17px; margin:0 0 12px; }}
.stats {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }} .stat, .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; box-shadow:0 1px 2px #1018280d; }}
.stat b {{ display:block; font-size:26px; }} .stat span {{ color:var(--muted); }}
.layout {{ display:grid; grid-template-columns:1.4fr .8fr; gap:18px; align-items:start; }} .map-wrap {{ overflow:auto; padding:14px; }}
.grid-row {{ height:12px; white-space:nowrap; }} .tile {{ display:inline-flex; width:12px; height:12px; margin:0 1px 1px 0; align-items:center; justify-content:center; border-radius:2px; font-size:7px; color:white; }}
.empty {{ background:#e9eef6; }} .lut {{ background:var(--lut); }} .ff {{ background:var(--ff); }} .carry {{ background:var(--carry); }} .io {{ background:var(--io); }} .special {{ background:var(--special); }} .other {{ background:var(--other); }}
.legend {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:12px; color:var(--muted); }} .legend i {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px; }}
table {{ width:100%; border-collapse:collapse; }} th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); }} th {{ color:var(--muted); font-weight:650; }}
.chips {{ display:flex; gap:8px; flex-wrap:wrap; }} .chip {{ display:inline-flex; gap:8px; align-items:center; border:1px solid var(--line); border-radius:999px; padding:6px 10px; background:white; }} .chip b {{ color:var(--muted); font-weight:600; }}
.flow {{ display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:10px; align-items:stretch; }} .node {{ border:1px solid var(--line); border-radius:8px; background:white; padding:14px; min-height:92px; }} .node strong {{ display:block; margin-bottom:6px; }} .node span {{ color:var(--muted); }}
.arrow {{ text-align:center; color:#64748b; font-weight:700; margin:-4px 0 12px; }}
@media (max-width:850px) {{ main {{ padding:16px; }} .stats, .layout, .flow {{ grid-template-columns:1fr; }} header {{ padding:22px 18px; }} }}
</style>
</head>
<body>
<header><h1>Tang Nano 20K Synthesized Configuration</h1><p>{html.escape(module_name)} on {html.escape(settings.get("packer.partno", "unknown device"))} from {html.escape(args.pnr.as_posix())}</p></header>
<main>
<section class="stats">
<div class="stat"><b>{len(cells)}</b><span>placed cells</span></div>
<div class="stat"><b>{len(module.get("netnames", {}))}</b><span>named nets</span></div>
<div class="stat"><b>{len(pins)}</b><span>constrained I/O pins</span></div>
<div class="stat"><b>{max_x-min_x+1} x {max_y-min_y+1}</b><span>occupied coordinate window</span></div>
</section>
<section class="flow">
<div class="node"><strong>Inputs</strong><span>clk, btn1, btn2 enter through constrained LVCMOS33 pins.</span></div>
<div class="node"><strong>Reset Logic</strong><span>btn1 or btn2 drives the asynchronous reset path.</span></div>
<div class="node"><strong>Counter Core</strong><span>{classes["ff"]} flip-flops, {classes["lut"]} LUT/MUX cells, and {classes["carry"]} carry cells implement the half-second divider.</span></div>
<div class="node"><strong>Outputs</strong><span>Six OBUF outputs drive led[0] through led[5].</span></div>
</section>
<section class="layout">
<div class="panel"><h2>Placement Heatmap</h2><div class="map-wrap">{"".join(grid)}</div><div class="legend"><span><i class="lut"></i>LUT/MUX</span><span><i class="ff"></i>flip-flop</span><span><i class="carry"></i>carry/ALU</span><span><i class="io"></i>I/O/clock</span><span><i class="special"></i>special</span><span><i class="other"></i>other</span></div></div>
<div class="panel"><h2>Ports</h2><div class="chips">{"".join(port_chips)}</div><h2 style="margin-top:18px">Build Settings</h2><table><tr><td>Target freq</td><td>{html.escape(settings.get("target_freq", "?"))}</td></tr><tr><td>Device</td><td>{html.escape(settings.get("packer.partno", "?"))}</td></tr><tr><td>Arch</td><td>{html.escape(settings.get("packer.arch", "?"))}</td></tr><tr><td>Placer</td><td>{html.escape(settings.get("placer", "?"))}</td></tr><tr><td>Router</td><td>{html.escape(settings.get("router", "?"))}</td></tr></table></div>
</section>
<section class="layout">
<div class="panel"><h2>I/O Pin Map</h2><table><thead><tr><th>Signal</th><th>Pin</th><th>Direction</th><th>I/O type</th></tr></thead><tbody>{"".join(pin_rows)}</tbody></table></div>
<div class="panel"><h2>Cell Types</h2><table><thead><tr><th>Type</th><th>Count</th><th>Class</th></tr></thead><tbody>{"".join(cell_rows)}</tbody></table></div>
</section>
</main>
</body>
</html>
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_out)


def main():
    parser = argparse.ArgumentParser(description="Generate an HTML visualization from a nextpnr JSON file.")
    parser.add_argument("--pnr", type=Path, default=Path("build/top_pnr.json"))
    parser.add_argument("--cst", type=Path, default=Path("constraints/tangnano20k.cst"))
    parser.add_argument("--output", type=Path, default=Path("build/top_visualization.html"))
    render(parser.parse_args())


if __name__ == "__main__":
    main()
