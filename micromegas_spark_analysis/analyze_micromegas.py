#!/usr/bin/env python3
"""
Analyze a micromegas detector video to (1) locate the static support pillars
and (2) detect transient sparks, over the first N seconds.

What the footage looks like
---------------------------
The detector mesh reads as a warm GOLD surface covered by a regular grid of
small DARK dots -- those dots are the support pillars. A spark is a brief,
small, BLUE-WHITE pinpoint flash sitting between the pillars. The clip is
handheld (Pixel phone), so the camera drifts the whole time.

Detection methods (chosen for that footage)
-------------------------------------------
Pillars: they are static and the same colour everywhere, but handheld motion
smears them in a temporal median, so we instead pick the SHARPEST single frame
(max variance-of-Laplacian) and run a black top-hat to pop the small dark dots,
then take their blob centroids. We report the count and the lattice pitch.

Sparks: the killer discriminator is COLOUR, not brightness. The gold mesh and
all its bright reflections have LOW blue, whereas a spark is blue-white with
HIGH blue. So we compute "blueness" = B - (R+G)/2 per pixel; the gold surface
sits around -15, sparks jump to +120..+150. Thresholding blueness isolates
sparks cleanly and -- unlike background subtraction -- is immune to the camera
motion. We group consecutive flagged frames into events and save an annotated
frame + zoomed crop for each.

Outputs land in ./output/. Thresholds are CLI-tunable.

Usage:
    python analyze_micromegas.py /path/to/video.mp4
    python analyze_micromegas.py video.mp4 --seconds 5 --blueness 20
"""
import argparse
import csv
import os

import cv2
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_VIDEO = "/home/dylan/Downloads/PXL_20260619_094502018.TS.mp4"
HERE = os.path.dirname(os.path.abspath(__file__))


def load_frames(path, seconds):
    """Read the first `seconds` of video. Returns (color_frames_list, fps)."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise SystemExit(f"Could not open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_want = int(round(fps * seconds))
    frames = []
    while len(frames) < n_want:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()
    if not frames:
        raise SystemExit("No frames read.")
    h, w = frames[0].shape[:2]
    print(f"Read {len(frames)} frames @ {fps:.2f} fps "
          f"({len(frames)/fps:.2f}s), size {w}x{h}")
    return frames, fps


def blueness(frame):
    """Per-pixel 'how blue vs the gold background'. Gold ~ -15, sparks ~ +130."""
    b, g, r = frame[:, :, 0].astype(np.int16), \
        frame[:, :, 1].astype(np.int16), frame[:, :, 2].astype(np.int16)
    return b - (r + g) // 2


# ----------------------------------------------------------------------------
# Pillars
# ----------------------------------------------------------------------------
def detect_pillars(frames, outdir, tophat_kernel, min_area, max_area):
    """Detect pillars (small dark dots) on the sharpest single frame."""
    # Sharpest frame = max focus = clearest dots (median is motion-blurred).
    sharp_i = int(np.argmax([cv2.Laplacian(
        cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() for f in frames]))
    frame = frames[sharp_i]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    print(f"  using sharpest frame #{sharp_i} for pillar detection")

    # Black top-hat highlights dark features smaller than the kernel (the dots),
    # while removing large-scale illumination (shadows, reflections).
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (tophat_kernel, tophat_kernel))
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, k)
    cv2.imwrite(os.path.join(outdir, "pillar_blackhat.png"), blackhat)

    _, mask = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(os.path.join(outdir, "pillar_mask.png"), mask)
    n, _, stats, cent = cv2.connectedComponentsWithStats(mask, connectivity=8)

    pts = [(cent[i][0], cent[i][1]) for i in range(1, n)
           if min_area <= stats[i, cv2.CC_STAT_AREA] <= max_area]

    annot = frame.copy()
    for x, y in pts:
        cv2.circle(annot, (int(round(x)), int(round(y))), 5, (0, 0, 255), 1)
    cv2.putText(annot, f"pillars: {len(pts)}", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
    cv2.imwrite(os.path.join(outdir, "pillars_detected.png"), annot)

    pitch = None
    if len(pts) >= 2:
        xy = np.array(pts)
        nn = []
        for i in range(len(xy)):
            d = np.linalg.norm(xy - xy[i], axis=1)
            d[i] = np.inf
            nn.append(d.min())
        pitch = float(np.median(nn))
    print(f"  detected {len(pts)} pillars; "
          f"lattice pitch (median NN dist) = "
          f"{pitch:.1f}px" if pitch else "  too few pillars for pitch")
    return pts, pitch


# ----------------------------------------------------------------------------
# Sparks
# ----------------------------------------------------------------------------
def detect_sparks(frames, fps, outdir, blue_thresh, min_pixels):
    """Detect blue-white sparks via the blueness channel."""
    n = len(frames)
    max_blue = np.zeros(n)
    n_blue = np.zeros(n, dtype=int)
    blob = [None] * n  # (cx, cy, x, y, w, h, area) of bluest blob per frame

    for i, f in enumerate(frames):
        bl = blueness(f)
        max_blue[i] = bl.max()
        mask = (bl >= blue_thresh).astype(np.uint8)
        cnt = int(mask.sum())
        n_blue[i] = cnt
        if cnt >= min_pixels:
            nc, _, stats, cent = cv2.connectedComponentsWithStats(mask, 8)
            j = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            blob[i] = (cent[j][0], cent[j][1], stats[j, cv2.CC_STAT_LEFT],
                       stats[j, cv2.CC_STAT_TOP], stats[j, cv2.CC_STAT_WIDTH],
                       stats[j, cv2.CC_STAT_HEIGHT], stats[j, cv2.CC_STAT_AREA])

    hot = np.array([b is not None for b in blob])

    # Group consecutive hot frames into events; keep the bluest frame of each.
    events, i = [], 0
    while i < n:
        if hot[i]:
            j = i
            while j + 1 < n and hot[j + 1]:
                j += 1
            peak = i + int(np.argmax(max_blue[i:j + 1]))
            events.append((i, j, peak))
            i = j + 1
        else:
            i += 1

    rows = []
    for (a, b, peak) in events:
        cx, cy, x, y, w, h, area = blob[peak]
        t = peak / fps
        rows.append({
            "event": len(rows) + 1, "frame": peak, "time_s": round(t, 3),
            "x": int(round(cx)), "y": int(round(cy)), "blob_area_px": int(area),
            "max_blueness": int(max_blue[peak]), "frames_in_event": b - a + 1,
        })
        # full annotated frame
        annot = frames[peak].copy()
        pad = 30
        cv2.rectangle(annot, (max(0, x - pad), max(0, y - pad)),
                      (x + w + pad, y + h + pad), (0, 0, 255), 3)
        cv2.putText(annot, f"SPARK #{len(rows)}  t={t:.2f}s  "
                           f"blueness={int(max_blue[peak])}", (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        cv2.imwrite(os.path.join(outdir, f"spark_{len(rows):02d}_frame{peak:04d}_"
                                         f"t{t:.2f}s.png"), annot)
        # zoomed crop (nearest-neighbour upscale so the pinpoint is visible)
        s = 90
        crop = frames[peak][max(0, int(cy) - s):int(cy) + s,
                            max(0, int(cx) - s):int(cx) + s]
        if crop.size:
            crop = cv2.resize(crop, (360, 360), interpolation=cv2.INTER_NEAREST)
            cv2.imwrite(os.path.join(outdir,
                        f"spark_{len(rows):02d}_crop.png"), crop)

    fieldnames = ["event", "frame", "time_s", "x", "y", "blob_area_px",
                  "max_blueness", "frames_in_event"]
    with open(os.path.join(outdir, "sparks.csv"), "w", newline="") as fcsv:
        wcsv = csv.DictWriter(fcsv, fieldnames=fieldnames)
        wcsv.writeheader()
        wcsv.writerows(rows)

    # Time-series plot of the spark signal.
    t_axis = np.arange(n) / fps
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(t_axis, max_blue, color="tab:blue", lw=1.3)
    ax.axhline(blue_thresh, color="gray", ls="--", lw=1,
               label=f"blueness threshold ({blue_thresh})")
    for r in rows:
        ax.plot(r["time_s"], r["max_blueness"], "rv", ms=10)
        ax.annotate(f"#{r['event']}", (r["time_s"], r["max_blueness"]),
                    textcoords="offset points", xytext=(0, 8), color="red",
                    ha="center")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("max blueness  B-(R+G)/2")
    ax.set_title(f"Spark detection (blue-channel) — {len(rows)} event(s)")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "spark_score.png"), dpi=110)
    plt.close(fig)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", nargs="?", default=DEFAULT_VIDEO)
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--outdir", default=os.path.join(HERE, "output"))
    ap.add_argument("--tophat-kernel", type=int, default=15)
    ap.add_argument("--pillar-min-area", type=int, default=2)
    ap.add_argument("--pillar-max-area", type=int, default=80)
    ap.add_argument("--blueness", type=int, default=20,
                    help="blueness over background to count as spark (gold~-15)")
    ap.add_argument("--spark-min-pixels", type=int, default=5,
                    help="min blue pixels in a frame to call it a spark")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    frames, fps = load_frames(args.video, args.seconds)

    # Diagnostic: temporal median (shows static scene; pillars are motion-blurred).
    gray_stack = np.stack([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames])
    cv2.imwrite(os.path.join(args.outdir, "median_background.png"),
                np.median(gray_stack, axis=0).astype(np.uint8))

    print("Detecting pillars...")
    detect_pillars(frames, args.outdir, args.tophat_kernel,
                   args.pillar_min_area, args.pillar_max_area)

    print("Detecting sparks...")
    sparks = detect_sparks(frames, fps, args.outdir, args.blueness,
                           args.spark_min_pixels)

    print(f"\nDone. {len(sparks)} spark event(s) in first {args.seconds:g}s:")
    for r in sparks:
        print(f"  #{r['event']:>2}  t={r['time_s']:.2f}s  frame {r['frame']}  "
              f"at ({r['x']},{r['y']})  area={r['blob_area_px']}px  "
              f"blueness={r['max_blueness']}")
    print(f"\nOutputs in: {args.outdir}")


if __name__ == "__main__":
    main()
