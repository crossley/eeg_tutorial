# eeg_tutorial

A teaching website that walks new students through EEG analysis as the
lab does it, on a small de-identified subset of one category-learning
experiment. Built with Quarto; the pages are in `chapters/`.

## Layout

| path | what |
|---|---|
| `index.qmd`, `chapters/*.qmd` | The pages. Each is prose with a few Python cells. |
| `references.bib` | The bibliography. Entries are taken from Crossref by DOI; check any you add by hand. |
| `tools/make_demo_data.py` | Builds the demo dataset from the lab's recordings. |
| `tools/DATA_README.md` | The dataset's own description, copied into it. |
| `tools/run_chapter.py` | Runs a page's code cells without Quarto, as a quick check. |
| `data/` | The built dataset. Not versioned. |
| `private/` | Source paths and the key to lab participant codes. Not versioned, never shared. |
| `_freeze/` | Executed results of the pages. Versioned; the site is rendered from it. |

## Working on a page

```bash
python tools/run_chapter.py chapters/02-raw-data.qmd   # does the code run?
quarto preview                                         # see the page
quarto render                                          # execute and update _freeze/
```

Use a Python with the packages in `requirements.txt`. Commit `_freeze/`
along with the page: the GitHub workflow renders the site from it and
runs no Python.

## The demo dataset

`python tools/make_demo_data.py` rebuilds `data/eeg_tutorial_data_v1/`
(about 320 MB, under a minute) from the source experiment, which it
only reads. It needs `private/sources.toml`. The script copies only
allow-listed channels and columns, writes everything under tutorial
labels, removes recording dates, and ends by scanning every output file
for lab codes, dates and source paths.

The pages read the data by the relative path
`data/eeg_tutorial_data_v1/...`. To publish the data, zip that folder
and upload it; the Colab notebooks will then start with a cell that
downloads and unzips it to the same path.

## Writing rules

- The audience knows little programming. Show only the lines that are
  the EEG step, and keep them short.
- Use the standard libraries directly (MNE, NumPy, pandas, Matplotlib,
  scikit-learn). No custom helper module: students should be able to
  reuse every line on their own data. Prefer MNE's built-in plots; where
  one does not exist, a few plain Matplotlib lines.
- Support factual and historical claims with a citation
  (`[@key]`, from `references.bib`).
- Exercises change a number and rerun. They never ask for new code.
- Teach the method on one participant. No findings from the lab's
  unpublished work.
- Give a short rationale for each comparison before showing it: what we
  might see, where and when, and why. Keep it light; the aim is
  familiarity, not formal hypothesis testing. Prefer well-known effects,
  and interpret cautiously.
- Check every number and description in the prose against the figure the
  code actually produces.
- End each page with how the lab's real pipeline does the same step.
