#!/usr/bin/env python3
"""Build the de-identified demo dataset from the lab's recordings.

Reads the source experiment read-only and writes only to data/ in this
repository. The source paths and the key from tutorial labels (sub-01,
...) to lab participant codes live in private/sources.toml, which is
never versioned; nothing in this script names a participant.

Three tiers, all from one experiment:

  sub-01/raw/     about six minutes of continuous task recording (the
                  first N_RAW_TRIALS trials of visit 1) and one minute
                  of eyes-closed rest, downsampled to RAW_SFREQ and
                  otherwise untouched, with the matching behaviour rows
  sub-01/epochs/  the cleaned stimulus-locked epochs of every visit
  group/          each participant's average response per visit and
                  category

De-identification is by allow-list: only the channels, metadata columns
and behaviour columns named below are copied, every file is written
under a tutorial label, and recording dates are removed. The run ends
with a scan of every output file for lab codes, dates and source paths
and fails if one is found.

The task triggers are written fresh into the Status channel from the
source project's audited trigger table (trial by trial, with the codes
the task program intended), not copied from the recorded Status values.
"""

from pathlib import Path
import hashlib
import re
import shutil
import tomllib

import mne
import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parent.parent
SOURCES = tomllib.loads((REPO_DIR / "private" / "sources.toml").read_text())
SRC = Path(SOURCES["experiment_dir"])
CODES = SOURCES["participants"]  # tutorial label -> lab code
DEMO = "sub-01"

VERSION = "v1"
OUT = REPO_DIR / "data" / f"eeg_tutorial_data_{VERSION}"

RAW_VISIT = 1
N_RAW_TRIALS = 100
RAW_SFREQ = 512
RAW_MARGIN_S = (5, 2)  # kept before the first and after the last trigger
REST_WINDOW_S = (60, 120)
EYE_CHANNELS = ["EXG1", "EXG2"]  # beside and below the left eye
PULSE_S = 0.01  # length of each trigger pulse written to Status
VISITS = [1, 2, 3, 4, 5]

BEHAVIOUR_COLUMNS = ["trial", "phase", "cat", "x", "y", "resp", "fb", "rt"]
METADATA_COLUMNS = ["trial", "phase", "cat", "x", "y", "resp", "fb", "rt"]


def cap_channels(raw):
    return [ch for ch in raw.ch_names if ch[0] in "AB" and ch[1:].isdigit()]


def strip_identity(inst):
    """Remove the recording date and every subject field."""
    if isinstance(inst, mne.io.BaseRaw):
        inst.anonymize(verbose="ERROR")
        inst.set_meas_date(None)
    else:  # Epochs.anonymize fails on epochs without annotations (MNE 1.11)
        mne.io.anonymize_info(inst.info, verbose="ERROR")
        with inst.info._unlock():
            inst.info["meas_date"] = None
    with inst.info._unlock():  # anonymize leaves a placeholder id
        inst.info["subject_info"] = None
    return inst


def read_excerpt(bdf, tmin, tmax, with_status):
    """Crop a recording before loading it, keep the cap and the eye electrodes."""
    raw = mne.io.read_raw_bdf(bdf, preload=False, stim_channel="Status", verbose="ERROR")
    cap = cap_channels(raw)
    assert len(cap) == 64, f"{len(cap)} cap channels, expected 64"
    raw.pick(cap + EYE_CHANNELS + (["Status"] if with_status else []))
    raw.crop(tmin, tmax).load_data(verbose="ERROR")
    raw.set_channel_types({ch: "eog" for ch in EYE_CHANNELS})
    # A fresh object, so the excerpt's samples count from zero.
    return mne.io.RawArray(raw.get_data(), raw.info, verbose="ERROR")


def build_raw_task(label, code):
    audit = pd.read_csv(SRC / "output" / "trigger_audit.csv")
    row = audit[(audit.subject == code) & (audit.day == RAW_VISIT)].iloc[0]
    assert row.status == "ok"
    triggers = pd.read_csv(SRC / "output" / "trigger_events.csv")
    triggers = triggers[(triggers.subject == code) & (triggers.day == RAW_VISIT)
                        & (triggers.trial < N_RAW_TRIALS)]
    source_sfreq = row.sfreq
    step = source_sfreq / RAW_SFREQ
    assert step == int(step)
    tmin = np.floor(triggers["sample"].min() / source_sfreq) - RAW_MARGIN_S[0]
    tmax = np.ceil(triggers["sample"].max() / source_sfreq) + RAW_MARGIN_S[1]

    raw = read_excerpt(SRC / row.file, tmin, tmax, with_status=False)
    raw.resample(RAW_SFREQ, verbose="ERROR")

    # Triggers: the audited code of each pulse at its resampled onset.
    status = np.zeros((1, raw.n_times))
    onsets = np.round((triggers["sample"].to_numpy() - tmin * source_sfreq) / step).astype(int)
    width = int(round(PULSE_S * RAW_SFREQ))
    assert np.diff(onsets).min() > width
    for onset, value in zip(onsets, triggers["code"]):
        status[0, onset:onset + width] = value
    stim = mne.io.RawArray(status, mne.create_info(["Status"], RAW_SFREQ, "stim"), verbose="ERROR")
    raw.add_channels([stim], force_update_info=True)

    out = OUT / label / "raw"
    out.mkdir(parents=True, exist_ok=True)
    strip_identity(raw).save(out / f"{label}_visit-{RAW_VISIT}_task_raw.fif", fmt="single",
                             overwrite=True, verbose="ERROR")

    behaviour = pd.read_csv(SRC / "output" / "behaviour_trials.csv")
    behaviour = behaviour[(behaviour.subject == code) & (behaviour.session_kind == "lab")
                          & (behaviour.lab_day == RAW_VISIT) & (behaviour.trial < N_RAW_TRIALS)]
    assert len(behaviour) == N_RAW_TRIALS
    behaviour[BEHAVIOUR_COLUMNS].to_csv(out / f"{label}_visit-{RAW_VISIT}_task_behaviour.csv",
                                        index=False, float_format="%.4f")


def build_raw_rest(label, code):
    files = [f for f in (SRC / "lab_data" / "EEG_data" / "resting_state" / str(RAW_VISIT)).glob("*.bdf")
             if re.match(rf"p{code:03d}_", f.name, re.IGNORECASE)]
    assert len(files) == 1, files
    raw = read_excerpt(files[0], *REST_WINDOW_S, with_status=False)
    raw.resample(RAW_SFREQ, verbose="ERROR")
    strip_identity(raw).save(OUT / label / "raw" / f"{label}_visit-{RAW_VISIT}_rest_raw.fif",
                             fmt="single", overwrite=True, verbose="ERROR")


def read_stim_epochs(code, visit):
    """One visit's cleaned stimulus-locked epochs with allow-listed metadata, or None."""
    path = SRC / "EEG_epo_v2" / "ii_task" / f"P{code:03d}_ii_{visit}-epo.fif"
    if not path.exists():
        return None
    epochs = mne.read_epochs(path, preload=True, verbose="ERROR")["Stim"]
    epochs.pick("eeg", exclude=[])
    epochs.metadata = epochs.metadata[METADATA_COLUMNS].reset_index(drop=True)
    return strip_identity(epochs)


def build_epochs(label, code):
    out = OUT / label / "epochs"
    out.mkdir(parents=True, exist_ok=True)
    for visit in VISITS:
        epochs = read_stim_epochs(code, visit)
        epochs.save(out / f"{label}_visit-{visit}_stim-epo.fif", fmt="single", overwrite=True,
                    verbose="ERROR")


def build_group():
    """Average response to each category on training trials, per participant and visit."""
    out = OUT / "group"
    out.mkdir(parents=True, exist_ok=True)
    for label, code in CODES.items():
        evokeds = []
        for visit in VISITS:
            epochs = read_stim_epochs(code, visit)
            if epochs is None:
                continue
            epochs.interpolate_bads(verbose="ERROR")
            for cat in "AB":
                evoked = epochs[f"phase == 'train' and cat == '{cat}'"].average()
                evoked.comment = f"visit-{visit}/{cat}"
                evokeds.append(evoked)
        mne.write_evokeds(out / f"{label}_stim-ave.fif", evokeds, overwrite=True, verbose="ERROR")


def scan_for_identifiers():
    """Fail if any output file carries a lab code, a date or a source path."""
    codes = sorted(CODES.values())
    # Byte patterns long enough not to occur by chance in a quarter gigabyte of samples.
    words = SOURCES["forbidden_words"]  # study nicknames that appear in source file names
    binary = [Path.home().name.encode(), b"/Users/"] + [f"_{word}_".encode() for word in words]
    binary += [f"20{year}{sep}{digit}".encode() for year in range(20, 30) for sep in "-_" for digit in "01"]
    binary += [f"{prefix}{code:03d}_".encode() for code in codes for prefix in ("P", "p", "sub_")]
    text = re.compile(r"20\d\d[-_/.]\d\d|/Users/|[Pp]\d{3}\b|sub_\d{3}|" + "|".join(words))
    for path in sorted(p for p in OUT.rglob("*") if p.is_file()):
        data = path.read_bytes()
        for pattern in binary:
            assert pattern not in data, f"{path}: contains {pattern!r}"
        if path.suffix in (".csv", ".md", ".txt"):
            found = text.search(data.decode())
            assert found is None, f"{path}: contains {found.group()!r}"
        if path.name.endswith(("_raw.fif", "-epo.fif", "-ave.fif")):
            info = mne.io.read_info(path, verbose="ERROR")
            assert info["meas_date"] is None, f"{path}: carries a recording date"
            assert not info["subject_info"], f"{path}: carries subject information"


def write_manifest():
    rows = []
    for path in sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "manifest.csv"):
        rows.append({"file": path.relative_to(OUT).as_posix(), "bytes": path.stat().st_size,
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = pd.DataFrame(rows)
    manifest.to_csv(OUT / "manifest.csv", index=False)
    print(manifest[["file", "bytes"]].to_string(index=False))
    print(f"total {manifest.bytes.sum() / 1e6:.0f} MB")


if __name__ == "__main__":
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    build_raw_task(DEMO, CODES[DEMO])
    build_raw_rest(DEMO, CODES[DEMO])
    build_epochs(DEMO, CODES[DEMO])
    build_group()
    shutil.copy(REPO_DIR / "tools" / "DATA_README.md", OUT / "README.md")
    scan_for_identifiers()
    write_manifest()
