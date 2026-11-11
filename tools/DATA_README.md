# EEG tutorial demo data

A small, de-identified subset of a category-learning EEG experiment,
for teaching only. Not for research use: it is one participant and a
few minutes of raw recording.

## The experiment

On each trial a striped disc (a sine-wave grating) appeared. Its bar
width (`x`) and tilt (`y`) varied from trial to trial. The participant
pressed one of two keys to say whether it belonged to category A or B
and was then told whether that was correct. Nobody was told the rule
(respond B when `x` exceeds `y`); it was learned from the feedback over
five visits to the lab. Visits 1, 4 and 5 end with 50 probe trials
(`phase == "test"`) on which the rule was changed.

EEG was recorded from 64 scalp electrodes (BioSemi ActiveTwo) and two
electrodes by the left eye.

## Files

| file | contents |
|---|---|
| `sub-01/raw/sub-01_visit-1_task_raw.fif` | The first 100 trials of visit 1, continuous and uncleaned: 64 scalp channels (`A1` to `B32`), eye channels `EXG1` (beside the left eye) and `EXG2` (below it), and the trigger channel `Status`. Downsampled from 4096 to 512 Hz; nothing else done. No reference has been applied. |
| `sub-01/raw/sub-01_visit-1_task_behaviour.csv` | One row per trial of that excerpt. |
| `sub-01/raw/sub-01_visit-1_rest_raw.fif` | One minute of eyes-closed rest from the same visit, same channels, no triggers. |
| `sub-01/epochs/sub-01_visit-<n>_stim-epo.fif` | Cleaned epochs around every stimulus of visit `n`: -0.2 to 0.8 s, 256 Hz, 0.5 to 40 Hz, average reference, eye movements removed by ICA, bad epochs repaired or dropped. Channels named in the 10-20 system. A channel listed as bad was left out of the cleaning and should be interpolated or ignored. The trial table is in `.metadata`. |
| `sub-01/epochs/sub-01_visit-1_fb-epo.fif` | The same for visit 1, cut around the feedback instead of the stimulus. Feedback was a ring around the stimulus, green for correct and red for incorrect; the stimulus stayed on screen. |
| `group/sub-<nn>_stim-ave.fif` | For each of 11 participants, the average response to category A and to category B on the training trials of each visit (comments `visit-<n>/A`, `visit-<n>/B`). Two participants have four visits. |
| `manifest.csv` | Size and SHA-256 of every file. |

## Trigger codes in `Status`

| code | event |
|---|---|
| 11 | trial start (fixation) |
| 20, 28 | stimulus from category A, B |
| 30, 31 | response A, B |
| 40, 41 | feedback correct, incorrect |
| 44 | feedback "too slow" |

Probe trials use 22, 23 (stimulus A, B), 33, 38 (response B, A) and
42, 43, 45 (feedback); none fall inside the raw excerpt.

## Trial columns

| column | meaning |
|---|---|
| `trial` | trial number within the visit, from 0 |
| `phase` | `train` or `test` (probe) |
| `cat` | the stimulus's category, A or B |
| `x`, `y` | bar width and tilt on a 0 to 100 scale |
| `resp` | the key pressed, A or B (or `Timeout`) |
| `fb` | `Correct`, `Incorrect` or `Too slow` |
| `rt` | reaction time in ms |

## De-identification

Participants carry tutorial labels unrelated to the lab's codes.
Recording dates, timestamps and source file names have been removed.
