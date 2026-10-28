#!/usr/bin/env python3
"""Closet risers from the same stock as the under-sink shelf: cut plan, cost and sag check.

A riser is one 750 x 400 x 18 mm pine top on four 27 x 27 mm batten legs, 200 mm tall
overall. It stands on an existing closet shelf (80 x 40 cm, ~76 cm usable) and splits the ~40 cm gap above
it in two (182 mm clear under the top, about 200 mm above it).

A second, small riser for empty jars in a kitchen top closet (v2, 2026-10-28): a 600 x 400 top
on four 20 mm dowel legs (Dylan's two 1 m dowels, not the batten), 180 mm tall overall. It fits
on the first board only because the two kitchen shelves are cut nested (see NEST_D).

    python3 under_sink_shelf/closet_riser.py        # table for 0..6 closet risers, cut plan for 1
    python3 under_sink_shelf/closet_riser.py 2      # cut plan for 2 closet risers

Stock and prices are the ones in buy.html (Castorama, read 2026-10-16). Writes
renders/closet_cut_plan.png.
"""
import pathlib
import sys

import build_model as bm

OUT = pathlib.Path(__file__).resolve().parent / "renders" / "closet_cut_plan.png"

# --- riser -------------------------------------------------------------------
TOP_L, TOP_W = 750, 400          # closet is ~76 cm wide with obstacles (Dylan, 2026-10-28)
HEIGHT = 200                     # overall, floor of the closet shelf to top of the riser
LEG_L = HEIGHT - bm.T            # 182
LEGS = 4
BRACKETS = 4                     # one per leg-to-top joint, like the kitchen shelf

# --- stock (buy.html) ----------------------------------------------------------
BOARD_L, BOARD_W, BOARD_EUR = 2000, 400, 16.90      # Tablette pin massif 40 x 200 cm, 18 mm
BATTEN_L, BATTEN_EUR = 2400, 8.69                  # baguette pin 27 x 27 mm, 2.4 m
BRACKET_PACK, BRACKET_EUR = 20, 7.79               # Amazon B0D6YTK3KT, 20 stainless 40 x 40 x 16 with screws
KITCHEN_EUR = 99.47                                # recommended basket in buy.html (2026-10-28)
KERF = 3                                           # saw cut, plus a little for squaring
END_TRIM = 10                                      # off each factory end, in case it is not square

# Jar riser for the kitchen top closet: top from the board, legs from 20 mm dowels.
JAR_TOP_L = 600
JAR_HEIGHT = 180
JAR_LEG_L = JAR_HEIGHT - bm.T    # 162, four of them from the 2 m of dowel

# The two kitchen shelves are cut nested: the second one is turned 180 degrees so the two diagonal
# edges run side by side, one saw cut apart. Board frame: u along the board, v across it (0..400).
SHELF_UV = [(y - 15, x - 15) for x, y in bm.OUTLINE_LOW]   # 430 long, 370 across
NEST_D = 191                     # u of the second shelf's narrow end; >= 3 mm between the diagonals
NEST_L = NEST_D + 430            # 621 mm of board for both shelves (860 if cut straight)
KITCHEN_BOARD = [("kitchen shelves", NEST_L)]
KITCHEN_POSTS = [("kitchen post", bm.Z_LOW)] * 3 + [("kitchen post", bm.Z_UP - bm.Z_LOW - bm.T)] * 3

E_PINE = 9000                    # MPa along the grain, on the low side for pine
LOAD_KG = 20                     # folded clothes: 80 x 40 x 18 cm at ~0.3 g/cm3 is about 17 kg


def pack(pieces, stock_len):
    """First-fit in the given order (kitchen pieces first). Returns a list of bins of (label, length)."""
    bins = []
    for label, n in pieces:
        for b in bins:
            used = 2 * END_TRIM + sum(x + KERF for _, x in b)
            if used + n <= stock_len:
                b.append((label, n))
                break
        else:
            bins.append([(label, n)])
    return bins


def plan(n):
    boards = pack(KITCHEN_BOARD + [("closet top", TOP_L)] * n + [("jar riser top", JAR_TOP_L)], BOARD_L)
    battens = pack(KITCHEN_POSTS + [("closet leg", LEG_L)] * (LEGS * n), BATTEN_L)
    packs = -(-(9 + BRACKETS * n) // BRACKET_PACK)
    extra = (len(boards) - 1) * BOARD_EUR + (len(battens) - 1) * BATTEN_EUR + (packs - 1) * BRACKET_EUR
    return boards, battens, packs, extra


def sag_mm():
    """Mid-span sag of the top, simply supported between the legs, uniform load."""
    span = TOP_L - bm.LEG
    i = TOP_W * bm.T ** 3 / 12
    w = LOAD_KG * 9.81
    return 5 * w * span ** 3 / (384 * E_PINE * i), span


def draw(n):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Rectangle

    boards, battens, _, _ = plan(n)
    rows = [("Board", i + 1, b, BOARD_L, BOARD_W) for i, b in enumerate(boards)]
    rows += [("Batten", i + 1, b, BATTEN_L, 120) for i, b in enumerate(battens)]
    colour = {"kitchen shelves": "#c9a46a", "kitchen post": "#c9a46a", "closet top": "#7aa5c9",
              "closet leg": "#7aa5c9", "jar riser top": "#8fbf8a"}

    fig, ax = plt.subplots(figsize=(11, 1.1 + 0.95 * len(rows)), dpi=150)
    y = 0
    for kind, k, b, length, h in rows:
        y -= h + 160
        ax.add_patch(Rectangle((0, y), length, h, fc="#efece4", ec="#888"))
        x = END_TRIM
        for label, size in b:
            if label == "kitchen shelves":
                second = [(NEST_D + 430 - u, BOARD_W - v) for u, v in SHELF_UV]
                for shape in (SHELF_UV, second):
                    ax.add_patch(Polygon([(x + u, y + v) for u, v in shape], fc=colour[label], ec="#333", lw=.6))
                ax.text(x + 90, y + 200, "kitchen\nshelf 1", ha="center", va="center", fontsize=8)
                ax.text(x + size - 90, y + 200, "kitchen\nshelf 2", ha="center", va="center", fontsize=8)
                x += size + KERF
                continue
            ax.add_patch(Rectangle((x, y), size, h, fc=colour[label], ec="#333", lw=.6))
            ax.text(x + size / 2, y + h / 2, f"{size}" if kind == "Batten" else f"{label}\n{size} x {BOARD_W}",
                    ha="center", va="center", fontsize=6.5 if kind == "Batten" else 8)
            x += size + KERF
        ax.text(-40, y + h / 2, f"{kind} {k}", ha="right", va="center", fontsize=9)
        ax.text(length + 40, y + h / 2, f"{length - x + KERF - END_TRIM:.0f} mm left", va="center",
                fontsize=8, color="#666")
    ax.set_xlim(-330, max(BATTEN_L, BOARD_L) + 330)
    ax.set_ylim(y - 60, 40)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"Cut plan: kitchen shelves (tan, nested), {n} closet riser{'s' * (n != 1)} (blue), "
                 f"jar riser (green), mm. Jar riser legs: 4 x {JAR_LEG_L} from the dowels", fontsize=10)
    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight")
    print("wrote", OUT)


if __name__ == "__main__":
    n_draw = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print("risers  boards  battens  bracket packs  extra EUR  total EUR")
    for n in range(7):
        boards, battens, packs, extra = plan(n)
        print(f"{n:6d}  {len(boards):6d}  {len(battens):7d}  {packs:13d}  {extra:9.2f}  {KITCHEN_EUR + extra:9.2f}")
    d, span = sag_mm()
    print(f"top sag with {LOAD_KG} kg spread over it: {d:.1f} mm over a {span} mm span "
          f"(long-term creep can about double it)")
    draw(n_draw)
