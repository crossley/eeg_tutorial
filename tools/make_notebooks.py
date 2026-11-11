#!/usr/bin/env python3
"""Turn each chapter into a notebook that runs in Google Colab.

    python tools/make_notebooks.py

Writes notebooks/<chapter>.ipynb for every chapter in chapters/ that
has Python cells. Each notebook starts with a cell that installs MNE
and downloads only the data files that chapter reads, from the release
named DATA_RELEASE, to the same relative paths the pages use. Run from
the top of the repository after editing a chapter, and commit the
notebooks.
"""

from pathlib import Path
import re

import nbformat
import pandas as pd

REPO = "crossley/eeg_tutorial"
DATA_RELEASE = "data-v1"
DATA_DIR = "data/eeg_tutorial_data_v1"
SITE = f"https://{REPO.split('/')[0]}.github.io/{REPO.split('/')[1]}"

REPO_DIR = Path(__file__).resolve().parent.parent
MANIFEST = pd.read_csv(REPO_DIR / DATA_DIR / "manifest.csv")

CELL = re.compile(r"^```\{python\}\n(.*?)^```\n", re.DOTALL | re.MULTILINE)
CALLOUT_OPEN = re.compile(r"^::: \{\.callout-(\w+)[^}]*\}\n## (.*)\n", re.MULTILINE)
CITATION = re.compile(r"\s*\[(?:@[\w]+(?:;\s*)?)+\]")
INLINE_CITATION = re.compile(r"@(\w+\d{4})")


def colab_url(stem):
    return f"https://colab.research.google.com/github/{REPO}/blob/main/notebooks/{stem}.ipynb"


def files_read_by(text):
    """Data files a chapter reads: the paths it names, and every group file if it uses the group folder."""
    files = [f for f in MANIFEST.file if f in text]
    # A path written with {visit} inside a loop over a list of visits.
    visits = re.search(r"for visit in \[([\d, ]+)\]", text)
    if visits:
        for visit in visits.group(1).split(","):
            files += [f for f in MANIFEST.file if f.replace(f"visit-{visit.strip()}_", "visit-{visit}_") in text]
    if '"group' in text or "/group" in text:
        files += [f for f in MANIFEST.file if f.startswith("group/")]
    return sorted(set(files))


def setup_cell(files, packages):
    megabytes = MANIFEST[MANIFEST.file.isin(files)].bytes.sum() / 1e6
    lines = [f"# Run this cell first. It installs MNE and downloads this chapter's data (about {megabytes:.0f} MB).",
             f"!pip -q install {packages}",
             "",
             "import urllib.request",
             "from pathlib import Path",
             "",
             f'release = "https://github.com/{REPO}/releases/download/{DATA_RELEASE}/"',
             "files = ["]
    lines += [f'    "{f}",' for f in files]
    lines += ["]",
              "for file in files:",
              f'    target = Path("{DATA_DIR}") / file',
              "    if not target.exists():",
              "        target.parent.mkdir(parents=True, exist_ok=True)",
              "        urllib.request.urlretrieve(release + Path(file).name, target)",
              "",
              "import mne",
              'mne.set_log_level("WARNING")',
              'mne.viz.set_browser_backend("matplotlib")  # plots appear in the notebook',
              "",
              "# MNE's data browser switches off automatic display of later plots; switch it back on before every cell.",
              "import matplotlib.pyplot as plt",
              'get_ipython().events.register("pre_run_cell", lambda *args: plt.ion())',
              'print("Ready.")']
    return "\n".join(lines)


def tidy_markdown(text):
    """Quarto-only syntax to plain Markdown: callouts become quoted blocks, citations are dropped."""
    text = re.sub(r"^.*colab-badge.*$\n?", "", text, flags=re.MULTILINE)
    text = CALLOUT_OPEN.sub(lambda m: f"**{m.group(2)}**\n\n", text)
    text = re.sub(r"^:::\s*$\n?", "", text, flags=re.MULTILINE)
    text = CITATION.sub("", text)
    text = INLINE_CITATION.sub(lambda m: f"{m.group(1)[:-4].capitalize()} ({m.group(1)[-4:]})", text)
    return text.strip()


def convert(chapter):
    text = chapter.read_text()
    header, body = re.match(r"---\n(.*?)\n---\n(.*)", text, re.DOTALL).groups()
    title = re.search(r'title: "(.*)"', header).group(1)
    pieces = CELL.split(body)  # markdown, code, markdown, code, ...
    codes = [code for code in pieces[1::2] if "#| include: false" not in code]
    if not codes:
        return None
    notebook = nbformat.v4.new_notebook()
    intro = (f"# {title}\n\nThis is the runnable version of a chapter of the EEG tutorial. "
             f"The page, with its references, is at {SITE}/chapters/{chapter.stem}.html\n\n"
             "Run the cells from the top, in order (Shift+Enter runs a cell and moves to the next).")
    notebook.cells.append(nbformat.v4.new_markdown_cell(intro))
    packages = "mne mne-connectivity" if "mne_connectivity" in text else "mne"
    notebook.cells.append(nbformat.v4.new_code_cell(setup_cell(files_read_by(text), packages)))
    for index, piece in enumerate(pieces):
        if index % 2 == 0:
            if tidy_markdown(piece):
                notebook.cells.append(nbformat.v4.new_markdown_cell(tidy_markdown(piece)))
        elif "#| include: false" not in piece:  # the page's hidden display settings
            notebook.cells.append(nbformat.v4.new_code_cell(piece.strip()))
    notebook.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    return notebook


if __name__ == "__main__":
    out = REPO_DIR / "notebooks"
    out.mkdir(exist_ok=True)
    for chapter in sorted((REPO_DIR / "chapters").glob("*.qmd")):
        notebook = convert(chapter)
        if notebook is None:
            continue
        # Fixed cell ids, so that regenerating an unchanged chapter changes nothing.
        for number, cell in enumerate(notebook.cells):
            cell["id"] = f"cell-{number:03d}"
        nbformat.write(notebook, out / f"{chapter.stem}.ipynb")
        print(chapter.stem, len(notebook.cells), "cells")
