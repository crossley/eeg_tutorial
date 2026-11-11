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
