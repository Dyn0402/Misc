#!/usr/bin/env python3
"""Geometry for the under-sink shelf, v5 (measured cabinet, flat back, middle and top shelves).

    python3 under_sink_shelf/build_model.py     # checks the design, writes model.json

Units: mm, Z up. OUTPUT frame (model.json, renders, page), standing at the open front
and looking in:
  +x is toward your RIGHT (the solid dishwasher wall is at x = 400), so LEFT is -x;
  +y is away from you (y = 0 is the door line, y = 500 the back wall, the outer kitchen wall);
  z is up from the cabinet floor. This is right-handed.
Cabinet: x in [0, 400] (the 40 cm door opening), y in [0, 500], z in [0, 700].
Extra space (v8): to the LEFT of the cabinet, x in [-700, 0], the same 500 deep and level with
the cabinet, on the same straight back wall (110 cm from the dishwasher wall to the far left).
The oven stands against it and blocks its front. The corner counter covers all of it and the
basin sits over the cabinet and part of the space.

The geometry below is AUTHORED with the origin at the back-right corner, x growing to the
viewer's left and y toward the front; build() rotates it 180 degrees about z on output
(x -> 400 - x, y -> 500 - y), a proper rotation. Authoring-frame numbers below therefore read:
x = distance to the left of the dishwasher wall, y = distance in front of the back wall.

Measured by Dylan: opening 400 wide, 500 deep, floor to sink basin bottom 600.
The trap and dishwasher hose are not modelled (v5): they are not in the design.

Both render_blender.py and the HTML animation read model.json.
"""

import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

# --- cabinet ---------------------------------------------------------------
CAB = dict(x0=0, x1=400, y0=0, y1=500, z0=0, z1=700)
BASIN_Z = 600        # basin bottom above cabinet floor (measured)
COUNTER_Z = 700      # counter underside (estimate)

# --- margins ---------------------------------------------------------------
WALL_M = 15          # shelf edge to side/back wall
FRONT_M = 55         # shelf edge to open front
TOP_M = 80           # top shelf top to basin bottom (v5: 82 mm; the 50 cm height was asked for)
LEFT_SPACE = 700    # extra space to the left of the 400 mm door opening: authoring x in [400, 1100] (v8)
BACK_LEFT = 0       # same straight back wall as the cabinet: no deeper (v8)
BASIN_X = (60, 460)  # basin outer x range: 60 mm clear of the dishwasher wall, 60 mm over the space (v8)

# --- structure -------------------------------------------------------------
LEG = 27             # 27 x 27 batten posts
T = 18               # shelf board thickness
Z_LOW = 300          # underside of middle shelf: 30 cm off the floor
Z_UP = 500           # underside of top shelf: 50 cm off the floor
TOP = Z_UP + T       # 518

# Flat back, steeper front-left slope toward the extra space (plan view, x, y in mm).
# Lower shelf (v11): the full 400 mm board width, so the back edge and the short left edge are the
# board's factory edges (two fewer cuts). 400 back edge, 100 front edge, 430 deep. The v10 diagonal
# is extended to the new left edge: 63 mm straight at the back (y 15..78), then the diagonal to the
# 100 mm front edge. The back-left corner reaches 15 mm past the door opening, into the open extra space.
OUTLINE_LOW = [(15, 15), (415, 15), (415, 78), (115, 445), (15, 445)]
# Upper shelf: same outline (the standpipe and its notch were removed in v4).
OUTLINE_UP = OUTLINE_LOW

# Post lower-left corners (x, y); each post is LEG x LEG.
POSTS = {"R": (25, 25), "F": (25, 403), "B": (363, 25)}

# Things stored under the sink, measured by Dylan (mm). Placed where they fit:
# the detergents stand upright on the floor under the middle shelf, the bags stand
# upright on the middle shelf, and the rinse bottle stands at the back-left, in the
# 50 cm of open floor left of the cabinet opening (it uses about 6 cm of it).
# Box = (x0, x1, y0, y1, z0, z1) bounding box, used for the clearance checks.
ITEM_BOX = {
    "bottle": (430, 560, 5, 65, 0, 390),     # 39 x 13 x 6 cm, at the back, 3 cm left of the door opening (out of view)
    "salt":   (150, 320, 0, 100, 0, 240),     # big blue detergent box 24 x 17 x 10 cm, upright, pushed back
    "tabs":   (60, 130, 0, 180, 0, 200),      # red detergent box 18 x 20 x 7 cm, upright, pushed back
    "roll":   (165, 235, 25, 95, 318, 468),   # bin bags 15 cm long x 7 cm diameter, upright, middle shelf
}


# --- geometry helpers ----------------------------------------------------------
def signed_area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1]
                     - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


def point_seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return ((ax + t * dx - px) ** 2 + (ay + t * dy - py) ** 2) ** 0.5


def inside(p, poly):
    """Even-odd point-in-polygon."""
    x, y = p
    c = False
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def edge_margin(p, poly):
    return min(point_seg_dist(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def rect_gap(a, b):
    """Gap between two xy rectangles (x0,x1,y0,y1); 0 if they overlap."""
    gx = max(a[0] - b[1], b[0] - a[1], 0)
    gy = max(a[2] - b[3], b[2] - a[3], 0)
    return max(gx, gy)


def triangulate(poly):
    """Ear clipping. Returns CCW triangles as index triples into poly."""
    idx = list(range(len(poly)))
    if signed_area(poly) < 0:
        idx.reverse()
    tris = []

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    while len(idx) > 3:
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if cross(a, b, c) <= 1e-9:
                continue
            if any(j not in (i0, i1, i2) and _in_tri(poly[j], a, b, c) for j in idx):
                continue
            tris.append((i0, i1, i2))
            del idx[k]
            break
        else:
            raise ValueError("triangulation failed")
    tris.append(tuple(idx))
    return tris


def _in_tri(p, a, b, c):
    def s(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
    d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def prism(poly, z0, z1):
    """Polygon extruded between z0 and z1. Returns (verts, faces), outward winding."""
    if signed_area(poly) < 0:
        poly = list(reversed(poly))
    n = len(poly)
    v = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
    f = []
    for a, b, c in triangulate(poly):
        f.append((a + n, b + n, c + n))      # top, normal +z
        f.append((a, c, b))                  # bottom, normal -z
    for i in range(n):
        j = (i + 1) % n
        f.append((i, j, j + n))
        f.append((i, j + n, i + n))
    return v, f


def box(x0, x1, y0, y1, z0, z1):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2), (0, 2, 1), (4, 5, 6), (4, 6, 7),
         (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
         (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return v, f


def cylinder(cx, cy, r, z0, z1, n=32):
    poly = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return prism(poly, z0, z1)


def ellipse(cx, cy, rx, ry, z0, z1, n=32):
    poly = [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return prism(poly, z0, z1)


def merge(*meshes):
    v, f = [], []
    for mv, mf in meshes:
        off = len(v)
        v += mv
        f += [(a + off, b + off, c + off) for a, b, c in mf]
    return v, f


def post_rect(name):
    x0, y0 = POSTS[name]
    return (x0, x0 + LEG, y0, y0 + LEG)


# --- checks -------------------------------------------------------------------
def check():
    problems = []

    def need(ok, msg):
        if not ok:
            problems.append(msg)

    for label, poly in (("lower", OUTLINE_LOW), ("upper", OUTLINE_UP)):
        for x, y in poly:
            need(CAB["x0"] + WALL_M <= x <= CAB["x1"] + WALL_M, f"{label} shelf x={x} too close to side wall")
            # past the door opening only at the back, where the cabinet is open to the extra space
            need(x <= CAB["x1"] - WALL_M or y <= 100, f"{label} shelf x={x}, y={y} hits the door frame")
            need(CAB["y0"] + WALL_M <= y <= CAB["y1"] - FRONT_M, f"{label} shelf y={y} margin to back/front")

    for name in POSTS:
        r = post_rect(name)
        for cx, cy in [(r[0], r[2]), (r[1], r[2]), (r[0], r[3]), (r[1], r[3])]:
            need(inside((cx, cy), OUTLINE_LOW), f"post {name} corner {cx},{cy} outside lower shelf")
            need(inside((cx, cy), OUTLINE_UP), f"post {name} corner {cx},{cy} outside upper shelf")
        need(edge_margin((r[0], r[2]), OUTLINE_UP) >= 8 or edge_margin((r[1], r[3]), OUTLINE_UP) >= 8,
             f"post {name} too close to edge")

    need(BASIN_Z - TOP >= TOP_M, "upper shelf too close to basin")

    # stored items: inside the cabinet, clear of each other, the posts and the shelves
    def overlap(a, b):
        return all(a[i] < b[i + 1] and b[i] < a[i + 1] for i in (0, 2, 4))

    posts = [(*post_rect(n), 0, Z_LOW) for n in POSTS] + [(*post_rect(n), Z_LOW + T, Z_UP) for n in POSTS]
    for name, box_ in ITEM_BOX.items():
        x0, x1, y0, y1, z0, z1 = box_
        need(CAB["x0"] <= x0 and x1 <= CAB["x1"] + LEFT_SPACE and -BACK_LEFT <= y0 and y1 <= CAB["y1"]
             and z1 <= BASIN_Z, f"item {name} outside the cabinet and the extra space")
        for pr in posts:
            need(not overlap(box_, pr), f"item {name} hits a post")
        for other, obox in ITEM_BOX.items():
            if other < name:
                need(not overlap(box_, obox), f"item {name} overlaps {other}")
        samples = [(x, y) for x in range(x0, x1 + 1, 5) for y in range(y0, y1 + 1, 5)]
        if z0 >= Z_LOW + T and z1 <= Z_UP:  # standing on the middle shelf: must stay on it
            need(all(inside(q, OUTLINE_LOW) for q in samples), f"item {name} overhangs the middle shelf")
        elif z1 > Z_LOW:  # reaches the middle or top shelf height: must be outside both outlines
            for q in samples:
                need(not inside(q, OUTLINE_LOW), f"item {name} collides with the middle shelf")
                need(not inside(q, OUTLINE_UP), f"item {name} collides with the top shelf")
    return problems


# --- model -------------------------------------------------------------------
def rot(p):
    """Authoring frame -> output frame: 180 degrees about z (proper rotation, winding kept)."""
    return [CAB["x1"] - p[0], CAB["y1"] - p[1], p[2]]


def part(pid, label, role, mesh, explode, step):
    v, f = mesh
    return dict(id=pid, label=label, role=role,
                verts=[rot(p) for p in v], faces=[list(t) for t in f],
                explode=[-explode[0], -explode[1], explode[2]], step=step)


def build():
    problems = check()
    if problems:
        raise SystemExit("design checks failed:\n  " + "\n  ".join(problems))

    parts = []
    # assembly parts
    for name in ("B", "R", "F"):
        x0, y0 = POSTS[name]
        parts.append(part(f"base{name}", f"Base post {name}", "post",
                          box(x0, x0 + LEG, y0, y0 + LEG, 0, Z_LOW), (0, 0, 380), 1))
    parts.append(part("shelfLow", "Middle shelf", "shelf",
                      prism(OUTLINE_LOW, Z_LOW, Z_LOW + T), (0, 0, 340), 2))
    for name in ("B", "R", "F"):
        x0, y0 = POSTS[name]
        parts.append(part(f"mid{name}", f"Middle post {name}", "post",
                          box(x0, x0 + LEG, y0, y0 + LEG, Z_LOW + T, Z_UP), (0, 0, 380), 3))
    parts.append(part("shelfUp", "Top shelf", "shelf",
                      prism(OUTLINE_UP, Z_UP, TOP), (0, 0, 340), 4))

    # context: the space itself (static, not part of the build)
    bx0, bx1 = BASIN_X
    xl = CAB["x1"] + LEFT_SPACE           # far left wall of the extra space (authoring frame)
    ctx = [
        ("back", "Back wall", "wall", box(0, 400, -18, 0, -18, 700)),
        ("right", "Right side (dishwasher wall)", "wall", box(-18, 0, -18, 500, 0, 700)),
        ("floor", "Cabinet floor", "wall", box(0, 400, 0, 500, -18, 0)),
        ("counter", "Corner counter top", "counter", box(-18, xl + 18, -18, 560, 700, 718)),
        ("basinB", "Basin bottom", "steel", box(bx0, bx1, 30, 440, BASIN_Z, BASIN_Z + 6)),
        ("basinF", "Basin front", "steel", box(bx0, bx1, 440, 446, BASIN_Z, COUNTER_Z)),
        ("basinBk", "Basin back", "steel", box(bx0, bx1, 24, 30, BASIN_Z, COUNTER_Z)),
        ("basinL", "Basin left", "steel", box(bx1 - 6, bx1, 24, 446, BASIN_Z, COUNTER_Z)),
        ("basinR", "Basin right", "steel", box(bx0, bx0 + 6, 24, 446, BASIN_Z, COUNTER_Z)),
        # the extra space left of the door: floor, the same back wall, and the far left wall
        ("leftFloor", "Extra space floor", "wall", box(400, xl, 0, 500, -18, 0)),
        ("leftBack", "Extra space back wall", "wall", box(400, xl + 18, -18, 0, -18, 700)),
        ("leftEnd", "Far left wall", "wall", box(xl, xl + 18, 0, 500, -18, 700)),
        ("oven", "Oven front (blocks the extra space)", "pipe", box(400, xl, 500, 520, 0, 700)),
    ]
    for pid, label, role, mesh in ctx:
        parts.append(part(pid, label, role, mesh, (0, 0, 0), 0))
    # stored items, at the positions in ITEM_BOX (checked above)
    items = [
        # rinse bottle: 39 cm bottom to cap, 13 wide, 6 deep; cap/neck on top; back-left
        ("bottle", "Rinse bottle (39 x 13 x 6 cm)", "bottle",
         merge(ellipse(495, 35, 65, 30, 0, 350), ellipse(495, 35, 30, 20, 350, 390))),
        ("salt", "Big blue detergent box (24 x 17 x 10 cm, upright)", "salt", box(*ITEM_BOX["salt"])),
        ("roll", "Trash bags (15 cm long, 7 cm diameter, upright)", "roll", cylinder(200, 60, 35, 318, 468)),
        ("tabs", "Smaller red detergent box (18 x 20 x 7 cm, upright)", "tabs", box(*ITEM_BOX["tabs"])),
    ]
    for pid, label, role, mesh in items:
        parts.append(part(pid, label, role, mesh, (0, 0, 0), 0))

    return dict(units="mm", cabinet=CAB, height=TOP, basin_z=BASIN_Z,
                outline_low=[rot((x, y, 0))[:2] for x, y in OUTLINE_LOW],
                outline_up=[rot((x, y, 0))[:2] for x, y in OUTLINE_UP], parts=parts,
                dims=dict(lower_area_mm2=round(abs(signed_area(OUTLINE_LOW))),
                          post_cut_mm=3 * Z_LOW + 3 * (Z_UP - Z_LOW - T)))


if __name__ == "__main__":
    model = build()
    out = HERE / "model.json"
    out.write_text(json.dumps(model, indent=1))
    print("checks passed; wrote", out)
    print("lower shelf area cm2:", round(model["dims"]["lower_area_mm2"] / 100),
          " post cut total mm:", model["dims"]["post_cut_mm"])
    print("under-shelf clearance mm:", Z_LOW, " between shelves mm:", Z_UP - Z_LOW - T,
          " top to basin mm:", BASIN_Z - TOP)
