#!/usr/bin/env python3
"""Build build.html: the step-by-step assembly tab ("Montage") for the under-sink shelf.

The drawings are computed from the same geometry as build_model.py (shelf outline, post
positions, heights), projected orthographically into inline SVG. Run:  python3 build_steps.py
"""
import math
import pathlib

import build_model as M

HERE = pathlib.Path(__file__).resolve().parent

# --- geometry in the drawing frame ------------------------------------------------------
# u: 0 at the short (left) side .. 400 at the long side against the dishwasher wall (right)
# w: 0 at the back edge .. 430 at the front edge;  z up.
W = 400
SH = [(W - (x - 15), y - 15) for x, y in M.OUTLINE_LOW]          # shelf outline (u, w)
LEG, T, ZL, ZU = M.LEG, M.T, M.Z_LOW, M.Z_UP
POSTS = {n: (W - (x - 15) - LEG, y - 15) for n, (x, y) in M.POSTS.items()}   # (u0, w0)
CENTRE = {n: (u + LEG / 2, w + LEG / 2) for n, (u, w) in POSTS.items()}
# which post face the bracket goes on: the face toward the middle of the shelf
FACE = {"R": "front", "F": "back", "B": "right"}
NORMAL = {"front": (0, 1, 0), "back": (0, -1, 0), "left": (-1, 0, 0), "right": (1, 0, 0)}
BR_W, BR_L, BR_T = 15, 40, 3


def prism(poly, z0, z1, kind, new=False):
    return dict(poly=poly, z0=z0, z1=z1, kind=kind, new=new)


def boxp(u0, u1, w0, w1, z0, z1, kind, new=False):
    return prism([(u0, w0), (u1, w0), (u1, w1), (u0, w1)], z0, z1, kind, new)


def post(n, z0, z1, new=False):
    u, w = POSTS[n]
    return dict(boxp(u, u + LEG, w, w + LEG, z0, z1, "post", new), id=f"{n}{z0}")


def bracket(n, zj, shelf_above, new=False):
    """Two thin boxes: one leg on the post face, one flat on the shelf face at height zj."""
    u, w = POSTS[n]
    cu, cw = CENTRE[n]
    if shelf_above:
        zp0, zp1, zs0, zs1 = zj - BR_L, zj, zj - BR_T, zj
    else:
        zp0, zp1, zs0, zs1 = zj, zj + BR_L, zj, zj + BR_T
    if FACE[n] == "front":
        a = boxp(cu - BR_W / 2, cu + BR_W / 2, w + LEG, w + LEG + BR_T, zp0, zp1, "steel", new)
        b = boxp(cu - BR_W / 2, cu + BR_W / 2, w + LEG, w + LEG + BR_L, zs0, zs1, "steel", new)
    elif FACE[n] == "back":
        a = boxp(cu - BR_W / 2, cu + BR_W / 2, w - BR_T, w, zp0, zp1, "steel", new)
        b = boxp(cu - BR_W / 2, cu + BR_W / 2, w - BR_L, w, zs0, zs1, "steel", new)
    elif FACE[n] == "right":
        a = boxp(u + LEG, u + LEG + BR_T, cw - BR_W / 2, cw + BR_W / 2, zp0, zp1, "steel", new)
        b = boxp(u + LEG, u + LEG + BR_L, cw - BR_W / 2, cw + BR_W / 2, zs0, zs1, "steel", new)
    else:  # left face
        a = boxp(u - BR_T, u, cw - BR_W / 2, cw + BR_W / 2, zp0, zp1, "steel", new)
        b = boxp(u - BR_L, u, cw - BR_W / 2, cw + BR_W / 2, zs0, zs1, "steel", new)
    # drawn right after the post it is screwed to (it is always on a face the view can see),
    # but before any shelf above it
    pid = f"{n}0" if zj == ZL else f"{n}{ZL + T}"   # base post under the middle shelf, else the middle post
    for o in (a, b):
        o["follow"] = pid
        o["normal"] = NORMAL[FACE[n]]
    return [a, b]


def flip(objs, H):
    """Turn everything upside down: 180 degrees about the front-back axis."""
    out = []
    for o in objs:
        if "normal" in o:
            nx, ny, nz = o["normal"]
            o = dict(o, normal=(-nx, ny, nz))
        out.append(dict(o, poly=[(W - u, w) for u, w in o["poly"]][::-1], z0=H - o["z1"], z1=H - o["z0"]))
    return out


def table(z=0):
    return boxp(-60, W + 60, -50, 480, z - 22, z, "table")


# --- projection --------------------------------------------------------------------------
class View:
    """Orthographic view in the (u, w, z) frame. az > 0: viewer at the front-left; az < 0: front-right."""
    def __init__(self, az_deg, el_deg):
        a, e = math.radians(az_deg), math.radians(el_deg)
        sa, ca, se, ce = math.sin(a), math.cos(a), math.sin(e), math.cos(e)
        self.D = (-sa * ce, ca * ce, se)    # toward the viewer
        self.R = (ca, sa, 0.0)              # screen right
        self.U = (sa * se, -ca * se, ce)    # screen up

    def p(self, u, w, z):
        P = (u, w, z)
        return (dot(P, self.R), -dot(P, self.U))

    def depth(self, u, w, z):
        return dot((u, w, z), self.D)

    def vis(self, n):
        return dot(n, self.D) > 1e-9


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


LIGHT = (-0.45, 0.75, 0.5)  # light from the front-left, above


def faces(o):
    poly, z0, z1 = o["poly"], o["z0"], o["z1"]
    cu = sum(p[0] for p in poly) / len(poly)
    cw = sum(p[1] for p in poly) / len(poly)
    fs = [([(u, w, z1) for u, w in poly], (0, 0, 1)), ([(u, w, z0) for u, w in poly], (0, 0, -1))]
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        nu, nw = (b[1] - a[1]), -(b[0] - a[0])
        mu, mw = (a[0] + b[0]) / 2 - cu, (a[1] + b[1]) / 2 - cw
        if nu * mu + nw * mw < 0:
            nu, nw = -nu, -nw
        L = math.hypot(nu, nw) or 1
        fs.append(([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], (nu / L, nw / L, 0)))
    return fs


def shade(n):
    v = dot(n, LIGHT)
    return "t" if n[2] > 0.5 else ("a" if v > 0.05 else "b")


class Fig:
    def __init__(self, view):
        self.v = view
        self.objs = []
        self.extra = []      # (kind, data) drawn after the solids
        self.pts = []

    def add(self, objs):
        self.objs += objs if isinstance(objs, list) else [objs]

    def P(self, u, w, z):
        q = self.v.p(u, w, z)
        self.pts.append(q)
        return q

    def screw(self, u, w, ztop, label=None, side=1):
        self.extra.append(("screw", (u, w, ztop, label, side)))

    def label(self, u, w, z, text, dx, dy, cls=""):
        self.extra.append(("label", (u, w, z, text, dx, dy, cls)))

    def height(self, u, w, zs):
        self.extra.append(("height", (u, w, zs)))

    def svg(self, aria, scale=1.0):
        body = []
        v = self.v
        key = {}
        for o in self.objs:
            if "id" in o:
                key[o["id"]] = (round(o["z0"]), v.depth(*centroid(o)))
        def k(o):
            if "follow" in o:
                z, d = key[o["follow"]]
                # on a face the view can see: right after its post; on a hidden face: just before it
                sign = 1 if v.vis(o["normal"]) else -1
                return (z, d + sign * 1e-3 * (1 + o["z1"] - o["z0"]))
            return (round(o["z0"]), v.depth(*centroid(o)))
        objs = sorted(self.objs, key=k)
        for o in objs:
            k = o["kind"]
            for pts, n in faces(o):
                if not v.vis(n):
                    continue
                q = [self.P(*p) for p in pts]
                cls = f"{k}-{shade(n)}" + (" new" if o["new"] else "")
                body.append(f'<polygon class="{cls}" points="{fmt(q)}"/>')
        for kind, d in self.extra:
            if kind == "screw":
                u, w, z, label, side = d
                h = self.P(u, w, z + 75)
                t = self.P(u, w, z + 8)
                body.append(f'<line class="screwline" x1="{h[0]:.1f}" y1="{h[1]:.1f}" x2="{t[0]:.1f}" y2="{t[1]:.1f}" marker-end="url(#arr)"/>')
                body.append(f'<ellipse class="screwhead" cx="{h[0]:.1f}" cy="{h[1]:.1f}" rx="7" ry="3"/>')
                if label:
                    body.append(f'<text class="lbl" x="{h[0] + 10 * side:.1f}" y="{h[1] - 4:.1f}" text-anchor="{"start" if side > 0 else "end"}">{label}</text>')
            elif kind == "label":
                u, w, z, text, dx, dy, cls = d
                a = self.P(u, w, z)
                b = (a[0] + dx, a[1] + dy)
                self.pts.append(b)
                anchor = "start" if dx >= 0 else "end"
                body.append(f'<line class="leader" x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>')
                body.append(f'<circle class="dot" cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="2.5"/>')
                lines = text.split("|")
                for i, line in enumerate(lines):
                    body.append(f'<text class="lbl {cls}" x="{b[0] + (4 if dx >= 0 else -4):.1f}" y="{b[1] + 4 + i * 15:.1f}" text-anchor="{anchor}">{line}</text>')
                    self.pts.append((b[0] + (len(line) * 7.2 if dx >= 0 else -len(line) * 7.2), b[1] + 8 + i * 15))
            elif kind == "height":
                u, w, zs = d
                base = self.P(u, w, 0)
                top = self.P(u, w, max(zs))
                body.append(f'<line class="ext" x1="{base[0]:.1f}" y1="{base[1]:.1f}" x2="{top[0]:.1f}" y2="{top[1]:.1f}"/>')
                for z in zs:
                    q = self.P(u, w, z)
                    body.append(f'<line class="tick" x1="{q[0] - 5:.1f}" y1="{q[1]:.1f}" x2="{q[0] + 5:.1f}" y2="{q[1]:.1f}"/>')
                    body.append(f'<text class="lbl hnum" x="{q[0] + 9:.1f}" y="{q[1] + 4:.1f}" text-anchor="start">{z}</text>')
                    self.pts.append((q[0] + 45, q[1]))
        xs = [p[0] for p in self.pts]
        ys = [p[1] for p in self.pts]
        pad = 14
        x0, y0 = min(xs) - pad, min(ys) - pad - 10
        wv, hv = max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad + 10
        return (f'<svg viewBox="{x0:.0f} {y0:.0f} {wv:.0f} {hv:.0f}" style="max-width:{wv * scale:.0f}px" role="img" aria-label="{aria}">'
                + DEFS + "".join(body) + "</svg>")


DEFS = ('<defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" class="arrowhead"/></marker></defs>')


def centroid(o):
    poly = o["poly"]
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly), (o["z0"] + o["z1"]) / 2)


def fmt(q):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in q)


LEFT = View(32, 26)    # from the front-left, as you stand at the cabinet door
RIGHT = View(-32, 26)  # from the front-right (for the upside-down steps, so every bracket shows)
NAMES = {"R": "back-right", "F": "front-right", "B": "back-left"}


# --- the parts at their final heights ----------------------------------------------------
def base_posts(new=False):
    return [post(n, 0, ZL, new) for n in POSTS]


def mid_shelf(new=False):
    return prism(SH, ZL, ZL + T, "pine", new)


def low_brackets(new=False):
    return sum((bracket(n, ZL, True, new) for n in POSTS), [])


def mid_posts(new=False):
    return [post(n, ZL + T, ZU, new) for n in POSTS]


def mid_brackets(new=False):
    return sum((bracket(n, ZL + T, False, new) for n in POSTS), [])


def top_shelf(new=False):
    return prism(SH, ZU, ZU + T, "pine", new)


def up_brackets(new=False):
    return sum((bracket(n, ZU, True, new) for n in POSTS), [])


# --- figures -----------------------------------------------------------------------------
def fig_plan():
    """Top view of one shelf, right way up, with the three post squares and their centres."""
    s = 1.3
    out = []

    def X(u):
        return 60 + u * s

    def Y(w):
        return 50 + w * s

    out.append(f'<polygon class="pine-t" points="{" ".join(f"{X(u):.1f},{Y(w):.1f}" for u, w in SH)}"/>')
    for n, (u, w) in POSTS.items():
        out.append(f'<rect class="sq" x="{X(u):.1f}" y="{Y(w):.1f}" width="{LEG * s:.1f}" height="{LEG * s:.1f}"/>')
        cu, cw = CENTRE[n]
        out.append(f'<path class="cross" d="M{X(cu) - 7:.1f},{Y(cw):.1f}h14M{X(cu):.1f},{Y(cw) - 7:.1f}v14"/>')
    # edge names
    out.append(f'<text class="lbl edge" x="{X(200):.0f}" y="{Y(0) - 12:.0f}" text-anchor="middle">BACK EDGE · 400 · against the back wall</text>')
    out.append(f'<text class="lbl edge" transform="translate({X(W) + 22:.0f},{Y(215):.0f}) rotate(90)" text-anchor="middle">LONG SIDE · 430 · dishwasher wall</text>')
    out.append(f'<text class="lbl edge" x="{X(350):.0f}" y="{Y(430) + 22:.0f}" text-anchor="middle">FRONT · 100</text>')
    out.append(f'<text class="lbl edge" x="{X(0) - 8:.0f}" y="{Y(36):.0f}" text-anchor="end">63</text>')
    out.append(f'<text class="lbl edge" transform="translate({X(130):.0f},{Y(260):.0f}) rotate({math.degrees(math.atan2(367, 300)):.1f})" text-anchor="middle">diagonal</text>')
    out.append(f'<text class="lbl" x="{X(200):.0f}" y="{Y(150):.0f}" text-anchor="middle">TOP face, seen from above,</text>')
    out.append(f'<text class="lbl" x="{X(200):.0f}" y="{Y(150) + 17:.0f}" text-anchor="middle">standing at the cabinet door</text>')
    # centre callouts
    calls = {
        "R": ("Back-right", "22.5 from the back edge", "22.5 from the long side", (-150, 70)),
        "B": ("Back-left", "22.5 from the back edge", "39.5 from the 63 edge", (60, 70)),
        "F": ("Front-right", "29.5 from the front edge", "22.5 from the long side", (-175, -150)),
    }
    for n, (t1, t2, t3, (dx, dy)) in calls.items():
        cu, cw = CENTRE[n]
        x, y = X(cu), Y(cw)
        bx, by = x + dx, y + dy
        anchor = "start"
        out.append(f'<line class="leader" x1="{x:.1f}" y1="{y:.1f}" x2="{bx:.1f}" y2="{by:.1f}"/>')
        out.append(f'<text class="lbl b" x="{bx + 4:.1f}" y="{by + 16:.1f}" text-anchor="{anchor}">{t1} centre</text>')
        out.append(f'<text class="lbl" x="{bx + 4:.1f}" y="{by + 32:.1f}" text-anchor="{anchor}">{t2}</text>')
        out.append(f'<text class="lbl" x="{bx + 4:.1f}" y="{by + 47:.1f}" text-anchor="{anchor}">{t3}</text>')
    wv, hv = X(W) + 50, Y(430) + 40
    return (f'<svg viewBox="0 0 {wv:.0f} {hv:.0f}" style="max-width:{wv:.0f}px" role="img" '
            'aria-label="Top view of a shelf with the three 25 mm post squares and their centres">' + "".join(out) + "</svg>")


def fig_section():
    """Cross-section of one joint: the 4 x 40 screw, and a bracket screw with its depth stop."""
    s = 3.6
    out = []
    ox, oy = 90, 40

    def R(x, y, w, h, cls):
        out.append(f'<rect class="{cls}" x="{ox + x * s:.1f}" y="{oy + y * s:.1f}" width="{w * s:.1f}" height="{h * s:.1f}"/>')

    def lbl(x, y, text, anchor="start", cls=""):
        out.append(f'<text class="lbl {cls}" x="{ox + x * s:.1f}" y="{oy + y * s:.1f}" text-anchor="{anchor}">{text}</text>')

    def lead(x1, y1, x2, y2):
        out.append(f'<line class="leader" x1="{ox + x1 * s:.1f}" y1="{oy + y1 * s:.1f}" x2="{ox + x2 * s:.1f}" y2="{oy + y2 * s:.1f}"/>')

    # left: the long screw. shelf 0..18 (y), post 18..65 below, centred at x=30
    R(0, 0, 60, 18, "pine-a")
    R(17.5, 18, 25, 50, "post-a")
    cx = 30
    # clearance hole + countersink
    R(cx - 2.5, 0, 5, 18, "hole")
    out.append(f'<polygon class="hole" points="{ox + (cx - 4) * s:.1f},{oy:.1f} {ox + (cx + 4) * s:.1f},{oy:.1f} {ox + (cx + 2.5) * s:.1f},{oy + 1.5 * s:.1f} {ox + (cx - 2.5) * s:.1f},{oy + 1.5 * s:.1f}"/>')
    # pilot
    out.append(f'<rect class="pilot" x="{ox + (cx - 1.25) * s:.1f}" y="{oy + 18 * s:.1f}" width="{2.5 * s:.1f}" height="{25 * s:.1f}"/>')
    # screw
    out.append(f'<polygon class="screw" points="{ox + (cx - 4) * s:.1f},{oy:.1f} {ox + (cx + 4) * s:.1f},{oy:.1f} {ox + (cx + 2) * s:.1f},{oy + 2 * s:.1f} '
               f'{ox + (cx + 1.6) * s:.1f},{oy + 38 * s:.1f} {ox + cx * s:.1f},{oy + 40 * s:.1f} {ox + (cx - 1.6) * s:.1f},{oy + 38 * s:.1f} {ox + (cx - 2) * s:.1f},{oy + 2 * s:.1f}"/>')
    lbl(30, -3, "4 × 40 screw", "middle", "b")
    lead(cx + 4, 1, 64, 3); lbl(65, 4, "countersink")
    lead(cx + 2, 10, 64, 11); lbl(65, 12, "5 mm (3/16\") hole right")
    lbl(65, 15.5, "through the shelf")
    lead(cx + 1.3, 32, 64, 32); lbl(65, 33, "2.5 mm (3/32\") pilot,")
    lbl(65, 36.5, "~25 mm into the post")
    lbl(-2, 9, "shelf 18", "end")
    lbl(17, 55, "post", "end")
    lbl(17, 58.5, "25 × 25", "end")
    # dimension: 18 / 22
    lbl(16, 41, "tip 22 mm into the post", "end")

    # right: a bracket in the corner, as you fit it (shelf upside down on the table, post standing on it).
    # The post sits straight on the wood; the L wraps the outside of the corner: one leg flat on the shelf,
    # one leg up the post face.
    bx = 110
    th = 2.0                                       # bracket metal, drawn a little thick to show
    R(bx, 30, 95, 18, "pine-a")                    # shelf 30..48
    R(bx + 2, -14, 25, 44, "post-a")               # post standing directly on the shelf
    R(bx + 27, 30 - th, 40, th, "steel-a")         # leg flat on the shelf
    R(bx + 27, 30 - 40, th, 40 - th, "steel-a")    # leg up the post face

    def screw_v(x, y0, L):                         # pointing down
        out.append(f'<polygon class="screw" points="{ox + (x - 3) * s:.1f},{oy + y0 * s:.1f} {ox + (x + 3) * s:.1f},{oy + y0 * s:.1f} '
                   f'{ox + (x + 1.2) * s:.1f},{oy + (y0 + L - 1.5) * s:.1f} {ox + x * s:.1f},{oy + (y0 + L) * s:.1f} {ox + (x - 1.2) * s:.1f},{oy + (y0 + L - 1.5) * s:.1f}"/>')

    def screw_h(y, x0, L):                         # pointing left, into the post
        out.append(f'<polygon class="screw" points="{ox + x0 * s:.1f},{oy + (y - 3) * s:.1f} {ox + x0 * s:.1f},{oy + (y + 3) * s:.1f} '
                   f'{ox + (x0 - L + 1.5) * s:.1f},{oy + (y + 1.2) * s:.1f} {ox + (x0 - L) * s:.1f},{oy + y * s:.1f} {ox + (x0 - L + 1.5) * s:.1f},{oy + (y - 1.2) * s:.1f}"/>')

    screw_v(bx + 40, 30 - th, 14)
    screw_v(bx + 56, 30 - th, 14)
    screw_h(5, bx + 27 + th, 14)
    screw_h(19, bx + 27 + th, 14)
    # drill with its tape flag, shown at full depth: the tape touches the wood when the hole is 12 deep
    dx0 = bx + 82
    out.append(f'<rect class="bit" x="{ox + (dx0 - 1) * s:.1f}" y="{oy - 3 * s:.1f}" width="{2 * s:.1f}" height="{45 * s:.1f}"/>')
    out.append(f'<rect class="tape" x="{ox + (dx0 - 4) * s:.1f}" y="{oy + 25 * s:.1f}" width="{8 * s:.1f}" height="{5 * s:.1f}"/>')
    out.append(f'<path class="dim" d="M{ox + (dx0 + 6) * s:.1f},{oy + 30 * s:.1f}v{12 * s:.1f}"/>')
    lbl(bx + 45, -20, "Bracket: an L around the outside of the corner", "middle", "b")
    lbl(bx + 31, -3, "leg up the post", "start")
    lbl(bx + 31, 0.5, "2 screws into the post", "start")
    lbl(bx + 31, 22, "leg flat on the shelf, 2 screws", "start")
    lbl(dx0 + 4, -9, "tape flag on the", "middle")
    lbl(dx0 + 4, -5.5, "2 mm (5/64\") bit", "middle")
    lbl(dx0 + 8, 37.5, "12", "start")
    lbl(bx - 2, -5, "post sits", "end")
    lbl(bx - 2, -1.5, "straight on", "end")
    lbl(bx - 2, 2, "the wood", "end")
    lbl(bx + 47, 53, "shelf-side screws ≤ 16 mm: the shelf is only 18", "middle")
    wv, hv = ox + (bx + 110) * s, oy + 66 * s
    return (f'<svg viewBox="0 -30 {wv:.0f} {hv + 30:.0f}" style="max-width:{wv:.0f}px" role="img" '
            'aria-label="Cross-sections: the 4 by 40 screw through a 5 mm hole into a 2.5 mm pilot, and a short bracket screw with a tape depth stop on the drill bit">'
            + "".join(out) + "</svg>")


def fig_step3a():
    f = Fig(RIGHT)
    H = ZL + T
    f.add(table())
    parts = [mid_shelf()] + base_posts(True) + low_brackets(True)
    f.add(flip(parts, H))
    f.label(W - 200, 330, T, "middle shelf, upside down|(underside up)", -60, 70)
    u, w = POSTS["R"]
    f.label(W - u - LEG / 2 - 12, w + LEG / 2, T, "glue the foot,|stand it on its square", -120, -60, "b")
    cu, cw = CENTRE["R"]
    f.label(W - cu, cw + LEG / 2 + 25, T + 3, "bracket on the inner face,|2 short screws per leg", 90, 60)
    return f.svg("Step 3: the middle shelf lies upside down on the table; the three 300 mm base posts stand on it, each with a bracket")


def fig_step3b():
    f = Fig(LEFT)
    f.add(base_posts() + low_brackets() + [mid_shelf(True)])
    for i, n in enumerate(POSTS):
        cu, cw = CENTRE[n]
        f.screw(cu, cw, ZL + T, "4 × 40" if n == "B" else None, -1)
    f.label(150, 330, ZL + T, "turned right way up,|standing on its posts", -80, 40)
    f.label(*CENTRE["R"], ZL + T, "2.5 mm pilot through|the 5 mm hole, then screw", 70, -60, "b")
    f.height(W + 45, 430, [0, ZL, ZL + T])
    return f.svg("Step 3, continued: the shelf turned upright on its posts, with a 4 by 40 screw driven down into each post")


def fig_step4():
    f = Fig(LEFT)
    f.add(base_posts() + low_brackets() + [mid_shelf()] + mid_posts(True) + mid_brackets(True))
    f.label(*CENTRE["R"], ZU, "182 mm posts straight above the|base posts, over the screw heads", 60, -40, "b")
    cu, cw = CENTRE["F"]
    f.label(cu - LEG / 2, cw, ZL + T + 60, "glue + bracket only|(no long screw here)", -60, 120)
    f.height(W + 45, 430, [0, ZL, ZL + T, ZU])
    return f.svg("Step 4: the three 182 mm middle posts glued on the middle shelf above the base posts, each with a bracket")


def fig_step5a():
    f = Fig(RIGHT)
    H = ZU + T
    f.add(table())
    parts = base_posts() + low_brackets() + [mid_shelf()] + mid_posts() + mid_brackets() + [top_shelf()] + up_brackets(True)
    f.add(flip(parts, H))
    f.label(W - 200, 330, T, "top shelf, upside down", -80, 60)
    u, w = POSTS["B"]
    f.label(W - u - LEG / 2, w + LEG / 2, H, "the lower part, upside down,|middle posts glued onto their squares", -40, -40)
    cu, cw = CENTRE["R"]
    f.label(W - cu, cw + LEG / 2 + 25, T + 3, "3 brackets: easy to|reach this way up", 90, 60, "b")
    return f.svg("Step 5: the top shelf lies upside down; the lower part is turned over onto it and the three brackets are fitted")


def fig_step5b():
    f = Fig(LEFT)
    f.add(base_posts() + low_brackets() + [mid_shelf()] + mid_posts() + mid_brackets() + [top_shelf(True)])
    for n in POSTS:
        cu, cw = CENTRE[n]
        f.screw(cu, cw, ZU + T, "4 × 40" if n == "B" else None, -1)
    f.label(*CENTRE["R"], ZU + T, "last 3 screws, same|as in step 3", 70, -60, "b")
    f.height(W + 45, 430, [0, ZL, ZL + T, ZU, ZU + T])
    return f.svg("Step 5, continued: the finished shelf upright, with the last three screws going down into the middle posts; heights 300, 318, 500 and 518 mm")


# --- page --------------------------------------------------------------------------------
CSS = """
  :root { --bg:#fafaf7; --fg:#1c1c1a; --mut:#66645e; --card:#ffffff; --line:#e2dfd6; --acc:#9a6a2f; --warn:#8a3b12; --ink:#1c1c1a;
          --pine-t:#ecd3a2; --pine-a:#d9b77c; --pine-b:#c29c5f; --post-t:#e6c387; --post-a:#cfa865; --post-b:#b38b4c;
          --steel-t:#c9ccd1; --steel-a:#a9adb4; --steel-b:#8a8f97; --table-t:#e6e3dc; --table-a:#d4d0c7; --table-b:#c3beb3;
          --new:#c0392b; --hole:#4a3a22; --tape:#3a7bd5; }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) { --bg:#161513; --fg:#ece9e1; --mut:#a6a095; --card:#1f1e1b; --line:#3a3832; --acc:#d3a262; --warn:#f0a074; --ink:#ece9e1;
          --pine-t:#9c7c48; --pine-a:#81653a; --pine-b:#6a522e; --post-t:#a3814a; --post-a:#86683b; --post-b:#6d542f;
          --steel-t:#9aa0a8; --steel-a:#7d838c; --steel-b:#646971; --table-t:#34322d; --table-a:#2c2a26; --table-b:#25231f;
          --new:#ff7a6b; --hole:#1a140c; --tape:#6ea4f0; }
  }
  :root[data-theme="dark"] { --bg:#161513; --fg:#ece9e1; --mut:#a6a095; --card:#1f1e1b; --line:#3a3832; --acc:#d3a262; --warn:#f0a074; --ink:#ece9e1;
          --pine-t:#9c7c48; --pine-a:#81653a; --pine-b:#6a522e; --post-t:#a3814a; --post-a:#86683b; --post-b:#6d542f;
          --steel-t:#9aa0a8; --steel-a:#7d838c; --steel-b:#646971; --table-t:#34322d; --table-a:#2c2a26; --table-b:#25231f;
          --new:#ff7a6b; --hole:#1a140c; --tape:#6ea4f0; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
  .wrap { max-width: 1040px; margin: 0 auto; padding: 24px 16px 64px; }
  h1 { font-size: 1.7rem; margin: .2em 0 .3em; }
  h2 { font-size: 1.2rem; margin: 2em 0 .6em; border-bottom: 1px solid var(--line); padding-bottom: .3em; }
  p.crumb { font-size: .85rem; color: var(--mut); margin: 0; }
  .lede, .note { color: var(--mut); }
  .note { font-size: .9rem; }
  nav.tabs { display: flex; gap: 4px; margin: 14px 0 6px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
  nav.tabs a { padding: 8px 16px; border: 1px solid transparent; border-bottom: none; border-radius: 8px 8px 0 0; text-decoration: none; color: var(--mut); }
  nav.tabs a[aria-current="page"] { background: var(--card); border-color: var(--line); color: var(--fg); font-weight: 600; margin-bottom: -1px; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 14px; margin: 12px 0; }
  .step { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); gap: 18px; align-items: start; }
  .step.single { grid-template-columns: 1fr; }
  @media (max-width: 760px) { .step { grid-template-columns: 1fr; } }
  .figs { display: grid; gap: 10px; }
  svg { width: 100%; height: auto; display: block; margin: 0 auto; }
  svg text { fill: var(--ink); font-family: system-ui, sans-serif; font-size: 13px; }
  svg .lbl.b { font-weight: 650; }
  svg .lbl.edge { fill: var(--mut); font-size: 12px; letter-spacing: .02em; }
  svg .hnum { fill: var(--mut); font-size: 12px; font-variant-numeric: tabular-nums; }
  svg polygon, svg rect { stroke: var(--ink); stroke-width: .8; stroke-linejoin: round; }
  .pine-t { fill: var(--pine-t); } .pine-a { fill: var(--pine-a); } .pine-b { fill: var(--pine-b); }
  .post-t { fill: var(--post-t); } .post-a { fill: var(--post-a); } .post-b { fill: var(--post-b); }
  .steel-t { fill: var(--steel-t); } .steel-a { fill: var(--steel-a); } .steel-b { fill: var(--steel-b); }
  .table-t { fill: var(--table-t); stroke: var(--mut) !important; } .table-a { fill: var(--table-a); stroke: var(--mut) !important; } .table-b { fill: var(--table-b); stroke: var(--mut) !important; }
  svg .new { stroke: var(--new); stroke-width: 1.6; }
  .sq { fill: none; stroke: var(--new) !important; stroke-width: 1.6 !important; stroke-dasharray: 4 3; }
  .cross { stroke: var(--new); stroke-width: 1.6; fill: none; }
  .leader { stroke: var(--mut); stroke-width: 1; }
  .dot { fill: var(--ink); }
  .ext { stroke: var(--mut); stroke-width: 1; stroke-dasharray: 3 3; }
  .tick, .dim { stroke: var(--mut); stroke-width: 1.2; fill: none; }
  .screwline { stroke: var(--new); stroke-width: 2.5; }
  .screwhead { fill: var(--steel-t); stroke: var(--new); stroke-width: 1.5; }
  .arrowhead { fill: var(--new); stroke: none; }
  .hole { fill: var(--hole) !important; stroke: none !important; }
  .pilot { fill: none; stroke: var(--hole) !important; stroke-dasharray: 3 2; }
  .screw { fill: var(--steel-a); }
  .bit { fill: var(--steel-b); }
  .tape { fill: var(--tape); }
  .legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: .88rem; color: var(--mut); margin: 6px 0 0; }
  .legend span::before { content: ""; display: inline-block; width: 14px; height: 10px; margin-right: 6px; vertical-align: -1px; border: 1.6px solid var(--new); border-radius: 2px; }
  ol, ul { padding-left: 1.3em; } li { margin: .35em 0; }
  table { width: 100%; border-collapse: collapse; font-size: .95rem; }
  th, td { text-align: left; padding: 7px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
  th { color: var(--mut); font-weight: 600; }
  td.v { white-space: nowrap; font-weight: 650; font-variant-numeric: tabular-nums; }
  .warn { color: var(--warn); }
  a { color: var(--acc); }
"""


def page():
    centre_rows = "".join(
        f"<tr><td>{NAMES[n].capitalize()}</td><td class='v'>{a}</td><td class='v'>{b}</td></tr>"
        for n, a, b in [("R", "22.5 from the back edge", "22.5 from the long side"),
                        ("F", "29.5 from the front edge", "22.5 from the long side"),
                        ("B", "22.5 from the back edge", "39.5 from the 63 mm edge")])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Shelf assembly steps</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <p class="crumb">Misc / under-sink shelf</p>
  <h1>Assembly, step by step</h1>
  <nav class="tabs" aria-label="Shelf pages">
    <a href="index.html">Design</a>
    <a href="buy.html">Cost &amp; buy list</a>
    <a href="cuts.html">Découpe</a>
    <a href="build.html" aria-current="page">Assembly</a>
    <a href="table.html">Folding table</a>
  </nav>
  <p class="lede">From cut parts to a finished shelf: two shelves, three 300 mm base posts, three 182 mm middle posts,
  9 stainless brackets, 6 screws 4 × 40 and 36 short bracket screws, plus the Pattex glue. All sizes in mm.
  Assemble first and oil afterwards: glue does not stick to oiled wood.</p>
  <p class="legend"><span>red outline: the parts added in that step</span></p>

  <h2>0. Before anything is glued</h2>
  <div class="card">
    <ul>
      <li><strong>Dry-fit in the cabinet.</strong> Stand the parts in place without glue. The unit is as wide as the door, so it goes in turned.</li>
      <li><strong>Measure the cabinet floor to the bottom of the basin.</strong> The design assumes 600 mm, which leaves 82 mm above the top shelf. If it is under about 540 mm, stop and shorten the middle posts first.</li>
      <li><strong>Look at the back for the trap and the dishwasher hose.</strong> Neither may sit where the top shelf or a post goes.</li>
      <li>Lay the two shelves one on the other and check they match, then write <strong>TOP</strong> on the face that will be up on each.</li>
    </ul>
  </div>

  <h2>Drill bits</h2>
  <div class="card">
    <table>
      <tr><th>Hole</th><th>Metric</th><th>US bit</th><th>Depth</th><th>Step</th></tr>
      <tr><td>Clearance hole through the shelf (6)</td><td class="v">5 mm</td><td class="v">3/16"</td><td>right through, scrap board under</td><td>2</td></tr>
      <tr><td>Countersink on the TOP face (6)</td><td class="v">6 mm</td><td class="v">1/4"</td><td>only the cone, until the bit is at full width</td><td>2</td></tr>
      <tr><td>Pilot into the post end, through the clearance hole (6)</td><td class="v">2.5 mm</td><td class="v">3/32"</td><td>tape 43 mm from the tip (18 shelf + 25 post)</td><td>3, 5</td></tr>
      <tr><td>Pilots for the short bracket screws (36)</td><td class="v">2 mm</td><td class="v">5/64"</td><td>tape 12 mm from the tip</td><td>3, 4, 5</td></tr>
    </table>
    <p class="note">The clearance hole must be wider than the 4 mm screw, or its thread bites the shelf and holds it off the post instead of pulling it down. 5 mm or 3/16" both work; 4 mm (or 5/32") is too tight. 7/64" also does for the 2.5 mm pilot in pine.</p>
    <p class="note">Countersinking with a twist bit: use a pointed twist (metal) bit, not a brad-point wood bit, which has a centre spur and cuts a flat-bottomed hole. Run it slowly with light pressure, or turn it by hand; it chatters and grabs. A 1/4" cone is narrower than the 8 mm screw head, so drive the last turn of each 4 × 40 slowly and let the head press itself flush in the pine. Do not overtighten. Try one on an offcut first. A countersink bit is cleaner if you buy one; then cut until the cone is just wider than the head.</p>
  </div>

  <h2>1. Mark the post centres (both shelves)</h2>
  <div class="card step">
    <div class="figs">{fig_plan()}</div>
    <div>
      <p>On the <strong>TOP face</strong> of each shelf, mark the three centres. Both shelves get the same marks, because they have the same outline and go in the same way round.</p>
      <table><tr><th>Post</th><th>Measure</th><th>and</th></tr>{centre_rows}</table>
      <p class="note">Each post is a 25 mm square whose edges sit 10 mm in from the back edge and the long side
      (17 mm from the front edge and 27 mm from the 63 mm edge). The centre is 12.5 mm further in.
      Mark it with a square, not by eye.</p>
    </div>
  </div>

  <h2>2. Drill the shelves</h2>
  <div class="card step single">
    <div class="figs">{fig_section()}</div>
    <div>
      <ol>
        <li>At each centre, drill <strong>5 mm (3/16") right through</strong> the shelf, with a scrap board underneath so the wood does not splinter where the bit comes out. Six holes in all.</li>
        <li><strong>Countersink</strong> each hole on the TOP face with the 1/4" bit: only the cone, stop when the bit reaches its full width.</li>
        <li>Turn each shelf over and draw a <strong>25 mm square centred on each hole</strong> (12.5 mm each way). The posts are glued onto these squares.</li>
      </ol>
      <p class="note">The 5 mm hole is wider than the 4 mm screw, so the screw grips only the post and pulls the shelf down tight on it.
      The 2.5 mm (3/32") pilot into the post is drilled later, through this hole, once the post is in place.</p>
      <p class="note warn">Bracket screws: 16 mm long at most on the shelf side. Wrap tape round the 2 mm (5/64") bit about 12 mm from the tip as a depth stop.</p>
    </div>
  </div>

  <h2>3. Middle shelf onto the three 300 mm base posts</h2>
  <div class="card step">
    <div class="figs">{fig_step3a()}{fig_step3b()}</div>
    <div>
      <ol>
        <li>Put the middle shelf <strong>upside down</strong> on the table (TOP face down).</li>
        <li>Glue the end of a base post. End grain soaks up glue: spread a thin coat, wait about 5 minutes, add a second coat.</li>
        <li>Stand the post on its square and press it down.</li>
        <li>Fit a <strong>bracket</strong> in the corner between the post and the shelf, on the post face that points into the shelf
          so its flat leg points into the shelf, never toward an edge: <strong>back-right</strong> on the post's front face, <strong>back-left</strong> on its right-hand face (the leg runs along the back wall, not toward the diagonal), <strong>front-right</strong> on its back face. Use the same face at every level. (Some are hidden behind their post in the drawings.)</li>
        <li>Pilot 2 mm / 5/64" (tape stop at about 12 mm) and drive the short screws: 2 into the shelf, 2 into the post.</li>
        <li>Do the other two posts the same way.</li>
        <li>Turn it <strong>the right way up</strong>, standing on its posts on the floor.</li>
        <li>Through each 5 mm hole, drill a <strong>2.5 mm (3/32") pilot about 25 mm into the post</strong> (tape 43 mm from the tip: it touches the shelf at the right depth), then drive a <strong>4 × 40</strong> screw, slowly at the end so the head seats flush.</li>
        <li>Wipe any glue that squeezes out with a damp cloth: oil will not take where glue has dried.</li>
      </ol>
    </div>
  </div>

  <h2>4. The three 182 mm middle posts</h2>
  <div class="card step">
    <div class="figs">{fig_step4()}</div>
    <div>
      <ol>
        <li>On the top of the middle shelf, glue each middle post <strong>straight above a base post</strong>, covering its screw head (the square drawn in step 2 is now under it: use the screw head as the centre).</li>
        <li>Fix each with a bracket on the same face as the bracket below, with short screws as before (2 mm / 5/64" pilots, tape at 12 mm).</li>
      </ol>
      <p class="note">These posts get only glue and a bracket at their bottom ends: a screw from below would hit the one coming down from above.</p>
    </div>
  </div>

  <h2>5. The top shelf</h2>
  <div class="card step">
    <div class="figs">{fig_step5a()}{fig_step5b()}</div>
    <div>
      <ol>
        <li>Put the top shelf <strong>upside down</strong> on the table.</li>
        <li>Glue the tops of the middle posts (two thin coats).</li>
        <li>Turn the lower part upside down and set it on the top shelf, each post on its square.</li>
        <li>Fit the last 3 brackets. They are easy to reach this way up.</li>
        <li>Turn the whole shelf the right way up.</li>
        <li>Drill the 2.5 mm (3/32") pilots through the 5 mm holes (tape at 43 mm) into the post tops and drive the last three 4 × 40 screws.</li>
      </ol>
      <p class="note">Heights from the cabinet floor: middle shelf underside 300, top 318; top shelf underside 500, top 518.</p>
    </div>
  </div>

  <h2>6. Check, cure, then oil</h2>
  <div class="card">
    <ol>
      <li>Stand it on the floor and press on each corner. If it rocks, one post is a little long: sand its foot on paper taped to a flat surface, holding the shelf upright.</li>
      <li>Let the glue cure for the time on the Pattex bottle (usually 24 hours).</li>
      <li><strong>Oil</strong> with the linseed oil: thin coats on every face, wipe off all the excess after 15–20 minutes, extra coats on the end grain (the diagonal and the post feet), about 24 hours between coats. Wipe oil off the brackets.</li>
      <li class="warn"><strong>Oily rags can catch fire on their own.</strong> Hang them flat outside to dry hard, or keep them in a sealed jar of water.</li>
      <li>Let it cure <strong>at least two weeks</strong> somewhere dry before it goes under the sink.</li>
    </ol>
    <p class="note">The drawings are computed from the design model (<code>build_model.py</code>), so the outline, post positions and heights match the Design tab.</p>
  </div>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    out = HERE / "build.html"
    out.write_text(page())
    print("wrote", out)
