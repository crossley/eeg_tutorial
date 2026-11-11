"""Plumbing for the tutorial pages: where the demo data are, and nothing about EEG.

The pages import this so that the code they show is only the analysis.
On first use the demo dataset is downloaded (about 270 MB) unless it is
already in data/ or the folder named by the EEGTUT_DATA variable.
"""

from pathlib import Path
import os

VERSION = "v1"
NAME = f"eeg_tutorial_data_{VERSION}"
# Set when the dataset archive is published (a zip of the NAME folder).
DATA_URL = None
DATA_SHA256 = None

_REPO_DATA = Path(__file__).resolve().parent.parent / "data" / NAME


def data_dir():
    """The folder holding the demo dataset, downloading it if it is not there."""
    if "EEGTUT_DATA" in os.environ:
        return Path(os.environ["EEGTUT_DATA"])
    if _REPO_DATA.exists():
        return _REPO_DATA
    if DATA_URL is None:
        raise FileNotFoundError(
            f"The demo data are not in {_REPO_DATA} and no download address is set yet. "
            "Ask for the dataset folder and put it there.")
    import pooch
    cache = Path(pooch.os_cache("eegtut"))
    if not (cache / NAME).exists():
        pooch.retrieve(DATA_URL, known_hash=DATA_SHA256, path=cache, fname=f"{NAME}.zip",
                       processor=pooch.Unzip(extract_dir="."), progressbar=True)
    return cache / NAME


def raw_task_file(visit=1):
    """The continuous, uncleaned task recording."""
    return data_dir() / "sub-01" / "raw" / f"sub-01_visit-{visit}_task_raw.fif"


def raw_rest_file(visit=1):
    """One minute of eyes-closed rest."""
    return data_dir() / "sub-01" / "raw" / f"sub-01_visit-{visit}_rest_raw.fif"


def behaviour_file(visit=1):
    """The trial table that goes with the task recording."""
    return data_dir() / "sub-01" / "raw" / f"sub-01_visit-{visit}_task_behaviour.csv"


def epochs_file(visit):
    """The cleaned stimulus-locked epochs of one visit (1 to 5)."""
    return data_dir() / "sub-01" / "epochs" / f"sub-01_visit-{visit}_stim-epo.fif"


def group_files():
    """Each participant's average responses, one file per participant."""
    return sorted((data_dir() / "group").glob("sub-*_stim-ave.fif"))


def compare_traces(before, after, channels, start, duration=5, labels=("before", "after")):
    """Draw the same stretch of the same channels from two recordings, one above the other."""
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(channels), 1, figsize=(8, 1.6 * len(channels) + 0.6), sharex=True,
                             squeeze=False)
    for ax, channel in zip(axes[:, 0], channels):
        for raw, label, colour in zip((before, after), labels, ("0.6", "C0")):
            first, last = raw.time_as_index([start, start + duration])
            trace = raw.get_data(picks=[channel], start=first, stop=last)[0] * 1e6
            ax.plot(raw.times[first:last], trace - trace.mean(), color=colour, lw=0.8, label=label)
        ax.set_ylabel(f"{channel}\n(µV)")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0, 0].legend(loc="lower right", bbox_to_anchor=(1, 1), ncols=2, frameon=False)
    axes[-1, 0].set_xlabel("Time (s)")
    fig.tight_layout()
    return fig


def channel_sizes(raw):
    """Bar chart of how large the signal is at each scalp channel (standard deviation, µV)."""
    import matplotlib.pyplot as plt
    data = raw.get_data(picks="eeg") * 1e6
    names = raw.copy().pick("eeg").ch_names
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.bar(range(len(names)), data.std(axis=1), color="C0")
    ax.set_xticks(range(len(names)), names, rotation=90, fontsize=6)
    ax.set_ylabel("Signal size (µV)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def average_of_n(epochs, channel, counts):
    """One panel per count: the average of that many epochs at one channel."""
    import matplotlib.pyplot as plt
    data = epochs.get_data(picks=[channel])[:, 0] * 1e6
    fig, axes = plt.subplots(1, len(counts), figsize=(2.6 * len(counts), 2.8), sharex=True, sharey=True)
    for ax, count in zip(axes, counts):
        ax.plot(epochs.times, data[:count].mean(axis=0), color="C0", lw=1)
        ax.axvline(0, color="0.5", lw=0.8, ls="--")
        ax.axhline(0, color="0.5", lw=0.8)
        ax.set_title(f"{count} trial" + ("s" if count > 1 else ""), fontsize=10)
        ax.set_xlabel("Time (s)")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel(f"{channel} (µV)")
    fig.tight_layout()
    return fig
