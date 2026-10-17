#!/usr/bin/env python3
"""Plan view of the under-sink space, from above, written to renders/shelf_plan.png.

Standing at the door: the back of the kitchen is at the top, your LEFT is the left of the
picture, the solid dishwasher wall is at the right. Uses the numbers in build_model.py.

    python3 under_sink_shelf/plan_view.py
"""
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon

import build_model as bm

OUT = pathlib.Path(__file__).resolve().parent / "renders" / "shelf_plan.png"
XL = bm.CAB["x1"] + bm.LEFT_SPACE        # far left wall of the extra space
YB = -bm.BACK_LEFT                        # 0: the extra space shares the cabinet back wall

fig, ax = plt.subplots(figsize=(10, 6.4), dpi=150)


def rect(x0, x1, y0, y1, **kw):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, **kw))


rect(0, 400, 0, 500, fc="#f4f3ee", ec="none")                       # cabinet floor
rect(400, XL, 0, 500, fc="#ebe9e0", ec="none")                     # extra space floor
rect(400, XL, 440, 500, fc="#5b5f66", ec="none", alpha=.85)         # oven, front part
ax.text((400 + XL) / 2, 470, "OVEN (stands against the space, blocks its front)", ha="center", va="center", color="white", fontsize=8)
rect(bm.BASIN_X[0], bm.BASIN_X[1], 24, 446, fc="#b8bcc2", ec="#555", alpha=.45, ls="--", lw=1.2)
ax.text(sum(bm.BASIN_X) / 2, 400, "sink basin above", ha="center", fontsize=8, color="#333")
ax.add_patch(Polygon(bm.OUTLINE_LOW, closed=True, fc="#c9925a", ec="#7a5230", alpha=.55, lw=1.2))
ax.text(200, 300, "shelves\n(top and middle)", ha="center", va="center", fontsize=8, color="#4a2f10")
for n in bm.POSTS:
    x0, y0 = bm.POSTS[n]
    rect(x0, x0 + bm.LEG, y0, y0 + bm.LEG, fc="#8a5a33", ec="none")
for name, (x0, x1, y0, y1, z0, z1) in bm.ITEM_BOX.items():
    col = {"bottle": "#1a38a0", "salt": "#2659c0", "tabs": "#73193f", "roll": "#202224"}[name]
    rect(x0, x1, y0, y1, fc=col, ec="none", alpha=.9)
ax.annotate("rinse bottle,\njust out of view\nfrom the door", xy=(475, 35), xytext=(700, 120), ha="center", fontsize=8, arrowprops=dict(arrowstyle="->", lw=.8))
ax.text(235, 55, "detergents", ha="center", fontsize=7, color="white")
# walls
w = dict(fc="#444", ec="none")
rect(-18, 0, -18, 500, **w)                       # dishwasher wall
rect(0, XL + 18, -18, 0, **w)                    # the one straight back wall
rect(XL, XL + 18, 0, 500, **w)                   # far left wall
ax.text(-40, 250, "SOLID WALL\n(dishwasher\nbehind)", ha="right", va="center", fontsize=8)
ax.text(200, 515, "door opening (40 cm)", ha="center", va="top", fontsize=8)
ax.annotate("", xy=(0, 510), xytext=(400, 510), arrowprops=dict(arrowstyle="<->", lw=1))
ax.annotate("", xy=(400, 510), xytext=(XL, 510), arrowprops=dict(arrowstyle="<->", lw=1, color="#888"))
ax.text((400 + XL) / 2, 515, "extra space: 70 cm wide, 50 deep", ha="center", va="top", fontsize=8, color="#555")
ax.text(450, -30, "BACK WALL = outer kitchen wall, one straight line, 50 cm from the door line", ha="center", va="bottom", fontsize=8)
ax.text(450, 580, "FRONT: you stand here", ha="center", fontsize=9, weight="bold")
ax.set_xlim(XL + 60, -330)
ax.set_ylim(610, -110)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title("Under the sink, from above (back of the kitchen at the top, your left on the left)", fontsize=10)
fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print("wrote", OUT)
