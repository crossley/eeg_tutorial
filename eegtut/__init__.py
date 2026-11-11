"""Plumbing for the tutorial pages: where the demo data are, and nothing about EEG.

The pages import this so that the code they show is only the analysis.
On first use the demo dataset is downloaded (about 320 MB) unless it is
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


def feedback_epochs_file(visit=1):
    """The cleaned feedback-locked epochs (visit 1 only)."""
    return data_dir() / "sub-01" / "epochs" / f"sub-01_visit-{visit}_fb-epo.fif"


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


def clean_recording(file):
    """Chapter 3 in one step: name the channels, filter 0.5 to 40 Hz, average reference.

    Blinks are left in; they matter little for what chapter 5 does with the result.
    """
    import mne
    raw = mne.io.read_raw_fif(file, preload=True)
    layout = mne.channels.make_standard_montage("biosemi64")
    raw.rename_channels(dict(zip(raw.ch_names[:64], layout.ch_names)))
    raw.set_montage(layout)
    raw.filter(0.5, 40)
    raw.set_eeg_reference("average")
    return raw


def compare_spectra(recordings, channel, fmax=30):
    """Overlay the power spectrum of several recordings at one channel. recordings: label -> raw."""
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 3.5))
    for label, raw in recordings.items():
        spectrum = raw.compute_psd(fmin=1, fmax=fmax, picks=[channel], n_fft=int(2 * raw.info["sfreq"]))
        ax.plot(spectrum.freqs, spectrum.get_data()[0] * 1e12, label=label)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel(f"Power at {channel} (µV²/Hz)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def plot_scores(times, scores):
    """Decoding score over time. scores: label -> one score per time point. Chance is 0.5."""
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 3.5))
    for label, values in scores.items():
        ax.plot(times, values, label=label)
    ax.axhline(0.5, color="0.5", lw=0.8)
    ax.axvline(0, color="0.5", lw=0.8, ls="--")
    ax.text(times[0], 0.49, "chance", ha="left", va="top", color="0.4", fontsize=9)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Decoding score (AUC)")
    ax.set_ylim(0.4, 1)
    ax.legend(frameon=False, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig
