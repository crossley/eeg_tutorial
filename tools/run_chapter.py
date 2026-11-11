#!/usr/bin/env python3
"""Run the Python cells of one or more chapters, top to bottom, without Quarto.

A quick check that a page's code works on the demo data:

    python tools/run_chapter.py chapters/02-raw-data.qmd

Figures are saved to the folder given by --figures (default: not saved).
"""

from pathlib import Path
import argparse
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


CELL = re.compile(r"^```\{python\}\n(.*?)^```", re.DOTALL | re.MULTILINE)

parser = argparse.ArgumentParser()
parser.add_argument("chapters", nargs="+", type=Path)
parser.add_argument("--figures", type=Path)
args = parser.parse_args()

for chapter in args.chapters:
    namespace = {}
    for number, cell in enumerate(CELL.findall(chapter.read_text()), start=1):
        print(f"--- {chapter.name} cell {number}")
        lines = cell.rstrip().split("\n")
        # Show the value of a trailing expression, as a notebook would.
        try:
            compile(lines[-1], "<last>", "eval")
            last = lines[-1] if not lines[-1].startswith((" ", ")", "]", "#")) else None
        except SyntaxError:
            last = None
        if last is not None:
            exec("\n".join(lines[:-1]), namespace)
            value = eval(last, namespace)
            if value is not None and not isinstance(value, (plt.Figure, list)):
                print(value)
        else:
            exec(cell, namespace)
        if args.figures is not None:
            args.figures.mkdir(parents=True, exist_ok=True)
            for index, fignum in enumerate(plt.get_fignums()):
                plt.figure(fignum).savefig(args.figures / f"{chapter.stem}_cell{number:02d}_{index}.png", dpi=80)
        plt.close("all")
