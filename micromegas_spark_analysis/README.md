# Micromegas pillar & spark analysis

Analyzes the first N seconds (default 5) of a micromegas detector video to
locate the static support **pillars** and detect transient **sparks**.

## Run

```bash
source ../venv/bin/activate          # needs: opencv-python-headless, numpy, matplotlib
python analyze_micromegas.py                      # uses the default video path
python analyze_micromegas.py /path/to/video.mp4 --seconds 5
```

## What the footage looks like

The mesh is a warm **gold** surface covered by a regular grid of small **dark
dots** — those dots are the support pillars. A spark is a brief, small,
**blue-white pinpoint** flash between the pillars. The clip is handheld, so the
camera drifts continuously.

## Methods (chosen for this footage)

- **Pillars** — static, so in principle a temporal median isolates them, but
  handheld motion smears the median. Instead we pick the **sharpest single
  frame** (max variance-of-Laplacian) and run a **black top-hat** to pop the
  small dark dots, then take blob centroids. Reports count and lattice pitch.

- **Sparks** — the decisive cue is **colour, not brightness**: the gold mesh and
  all its bright reflections are low-blue, while a spark is blue-white. We
  compute `blueness = B - (R+G)/2`; the background sits near **−15**, sparks
  jump to **+120…+150**. Thresholding blueness isolates sparks and — unlike
  background subtraction — is **immune to the camera motion**. Consecutive
  flagged frames are grouped into one event.

  > An earlier attempt used median-background subtraction + bright-blob area.
  > It failed: handheld motion makes the residual huge everywhere, drowning the
  > sparks. The blue-channel method replaced it.

## Outputs (`output/`)

| file | meaning |
|---|---|
| `pillars_detected.png` | sharpest frame with every detected pillar circled |
| `pillar_blackhat.png`, `pillar_mask.png` | pillar-detection intermediates |
| `spark_score.png` | max-blueness vs time, with detected events marked |
| `spark_NN_frameXXXX_t*.png` | full frame for each spark, boxed |
| `spark_NN_crop.png` | zoomed crop of each spark |
| `sparks.csv` | event, frame, time_s, x, y, blob_area_px, max_blueness |
| `median_background.png` | diagnostic (shows motion blur of the static scene) |

## Result on `PXL_20260619_094502018.TS.mp4` (first 5 s)

- ~2200 pillars, lattice pitch ≈ 33 px.
- **4 sparks**: t≈0.07 s, 1.67 s, 3.85 s, 3.95 s.

## Tuning

`--blueness` (spark colour threshold), `--spark-min-pixels`, `--tophat-kernel`
and `--pillar-min-area/--pillar-max-area` (pillar blob size) are all CLI flags.
