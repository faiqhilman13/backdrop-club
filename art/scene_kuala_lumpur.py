"""Kuala Lumpur: the Petronas Twin Towers over the Klang, lilac and peach by day, dark and quietly lit by night."""

from __future__ import annotations

import math

import numpy as np

from dither import H, SHORE, W, Picture, Skyline, grid, lights, noise, range_of, stars, strokes

ID = "kuala-lumpur"
NAME = "Kuala Lumpur"
DESCRIPTION = "The Petronas Twin Towers and their skybridge, with Menara KL, Merdeka 118, palms by the river and the green Titiwangsa hills behind."
TAGS = ["city", "skyline", "malaysia", "petronas"]

# Where things stand, the same by day and by night.
TWINS = (245, 266)  # the centre column of each Petronas tower
TIP = 76  # the top of their pinnacles
BRIDGE = 118  # the skybridge's top row
MENARA = (172, 135, 86)  # Menara KL: centre column, the hilltop row it stands on, its antenna's tip
MERDEKA = (341, 70)  # Merdeka 118: centre column, the tip of its spire
SUN = (304.0, 116.0, 9.0)


# ---- helpers the kit lacks ----


def blank() -> np.ndarray:
    return np.zeros((H, W), bool)


def blot(p: Picture, mask: np.ndarray, fill: str):
    """Any shape of whole pixels (an H x W mask) as one path: each run of a row, carried down the rows it repeats on."""
    d = ""
    live: dict[tuple[int, int], int] = {}
    for row in range(H + 1):
        runs = set()
        if row < H:
            edges = np.flatnonzero(np.diff(np.concatenate(([0], mask[row].astype(np.int8), [0]))))
            runs = {(int(a), int(b - a)) for a, b in zip(edges[::2], edges[1::2])}
        for run in sorted(r for r in live if r not in runs):
            start = live.pop(run)
            d += f"M{run[0]} {start}h{run[1]}v{row - start}h-{run[1]}z"
        for run in runs:
            live.setdefault(run, row)
    if d:
        p.body.append(f'<path fill="{fill}" d="{d}"/>')


def bar(mask: np.ndarray, cx: int, y: int, width: int, rows: int = 1, on: bool = True):
    """`rows` rows of `width` pixels (odd), centred on column cx, from row y down."""
    mask[y : y + rows, cx - width // 2 : cx - width // 2 + width] = on


def line(mask: np.ndarray, x0: float, y0: float, x1: float, y1: float):
    """A one-pixel line between two points."""
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for t in np.linspace(0.0, 1.0, n + 1):
        mask[int(round(y0 + (y1 - y0) * t)), int(round(x0 + (x1 - x0) * t))] = True


# ---- the place: the same in both lights ----

# One Petronas tower from the top down: (first row, rows, width). The pinnacle with its bead,
# the crown, then setbacks that widen to the shaft.
PROFILE = [
    (TIP, 6, 1), (TIP + 6, 2, 3), (TIP + 8, 4, 1),
    (88, 1, 3), (89, 2, 3), (91, 1, 5), (92, 3, 5), (95, 1, 7), (96, 4, 5), (100, 1, 7), (101, 7, 7),
    (108, SHORE - 108, 9),
]


def petronas():
    """The twin towers and the skybridge between them, with its two legs. Returns (towers, bridge)."""
    towers, bridge = blank(), blank()
    for cx in TWINS:
        for top, rows, width in PROFILE:
            bar(towers, cx, top, width, rows)
    a, b = TWINS[0] + 5, TWINS[1] - 5
    bridge[BRIDGE : BRIDGE + 2, a : b + 1] = True
    mid = (a + b) / 2
    line(bridge, mid - 0.5, BRIDGE + 2, a, BRIDGE + 9)
    line(bridge, mid + 0.5, BRIDGE + 2, b, BRIDGE + 9)
    return towers, bridge


def menara():
    """Menara KL on its hill: a slim shaft, the round head near the top, and a long antenna.
    Returns (tower, head)."""
    cx, foot, tip = MENARA
    tower, head = blank(), blank()
    bar(tower, cx, tip, 1, 101 - tip)
    bar(tower, cx, 99, 3, 2)
    bar(tower, cx, 108, 3, foot - 108)
    bar(tower, cx, foot - 4, 5, 4)
    y = 101
    for width in [5, 7, 9, 9, 7, 7, 5]:
        bar(head, cx, y, width)
        y += 1
    return tower, head


def merdeka() -> np.ndarray:
    """Merdeka 118: a faceted shaft tapering gently, folding in to a point, and a long spire."""
    cx, tip = MERDEKA
    m = blank()
    bar(m, cx, tip, 1, 18)
    for y in range(tip + 18, SHORE):
        f = (y - (tip + 18)) / (SHORE - 1 - (tip + 18))
        w = 1 + 2 * int(round(1.5 * min(1.0, f / 0.17) + 2.5 * f))
        bar(m, cx, y, w)
    return m


def facets() -> np.ndarray:
    """The folds in Merdeka 118's glass: the half of its face turned from the light, edged in a zigzag."""
    cx, tip = MERDEKA
    m = blank()
    for y in range(tip + 18, SHORE):
        k = (y - tip) % 14
        off = (k if k < 7 else 14 - k) - 3
        m[y, cx + off // 2 :] = True
    return m & merdeka()


def hills():
    """The Titiwangsa range behind the city: a far ridge and a nearer one."""
    far = range_of(127, [(60, 12, 70), (150, 8, 60), (240, 10, 80), (330, 12, 70), (430, 9, 80)], seed=4, rough=1.1, sharp=1.0)
    near = range_of(133, [(20, 7, 60), (110, 9, 70), (200, 6, 60), (290, 8, 70), (390, 9, 70), (480, 6, 60)], seed=6, rough=0.9, sharp=1.0)
    return far, near


def city():
    """The blocks: a far row, low about the twin towers' feet, and the near row with the mall at their foot."""
    far, near = Skyline(), Skyline()
    far.blocks(0, 150, 137, 123, seed=11, widths=(6, 13), gap=(0, 2))
    far.blocks(150, 226, 138, 128, seed=12, widths=(6, 12), gap=(0, 2))
    far.blocks(226, 286, 140, 133, seed=13, widths=(6, 10), gap=(0, 2))
    far.blocks(286, 362, 138, 126, seed=14, widths=(6, 12), gap=(0, 2))
    far.blocks(362, W, 137, 122, seed=15, widths=(6, 13), gap=(0, 2))
    for x0, w, top in [(204, 6, 122), (210, 5, 125), (290, 6, 121), (298, 5, 124), (380, 7, 115), (387, 5, 119), (120, 6, 117), (126, 5, 120)]:
        far.box(x0, w, top)
    near.blocks(0, W, 144, 141, seed=21, widths=(8, 18), gap=(0, 3))
    near.blocks(0, 146, 141, 131, seed=22, widths=(5, 11), gap=(2, 8))
    near.blocks(196, 231, 140, 131, seed=23, widths=(5, 9), gap=(1, 4))
    near.blocks(281, 330, 140, 130, seed=24, widths=(5, 9), gap=(1, 4))
    near.blocks(356, W, 141, 131, seed=25, widths=(5, 11), gap=(2, 8))
    near.box(231, 50, 140)  # the mall at the towers' foot
    near.box(237, 38, 138)
    return far, near


def palms() -> np.ndarray:
    """A few palms along the river bank."""
    m = blank()
    for x, h, lean in [(150, 15, -3), (160, 11, 2), (191, 13, -2), (226, 10, 2), (296, 10, -2), (318, 14, 3), (329, 10, -2), (372, 13, 2)]:
        base = SHORE - 1
        for i in range(h):
            t = i / h
            m[base - i, x + int(round(lean * t * t))] = True
        tx, ty = x + lean, base - h
        for frond in [
            [(1, 0), (2, 0), (3, 1), (4, 2)],
            [(-1, 0), (-2, 0), (-3, 1), (-4, 2)],
            [(1, -1), (2, -1), (3, -1), (4, 0)],
            [(-1, -1), (-2, -1), (-3, -1), (-4, 0)],
            [(0, -1), (1, -2)],
            [(1, 1), (2, 2), (2, 3)],
            [(-1, 1), (-2, 2), (-2, 3)],
        ]:
            for dx, dy in frond:
                m[ty + dy, tx + dx] = True
    return m


# ---- the two lights ----


def day() -> Picture:
    """Light windows: a pale sun beside the towers, lilac haze over sage hills, the city in pastels."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()
    sx, sy, sr = SUN

    rise = np.clip((y - 78) / (142 - 78), 0, 1) ** 1.9
    halo = np.exp(-(((x - sx) / 95) ** 2) - ((y - sy) / 48) ** 2)
    drift = 0.9 + 0.2 * noise(W, 5, 3, 8.0)[None, :]
    p.tone(rise * (0.35 + 1.15 * halo) * drift, ["#ebe3f2", "#fbe1d2"])

    p.disc(sx, sy, sr, "#fcdccb")
    p.disc(sx, sy, sr, p.level("#f5b8a2", 5), rows=(int(sy - sr), int(sy - 3)))
    p.disc(sx, sy, sr, p.level("#f5b8a2", 9), rows=(int(sy - 3), int(sy + sr) + 1))

    far_hill, near_hill = hills()
    p.ridge(far_hill, "#dbe5d2")
    p.ridge(near_hill, "#c9dbbf")

    blot(p, merdeka(), "#d6d8f0")
    blot(p, facets(), "#bcc3e6")

    far, near = city()
    p.ridge(far.tops, "#ddd3ea")

    tower, head = menara()
    hill = range_of(MENARA[1] + 1, [(MENARA[0], 7, 24)], seed=9, rough=0.6, sharp=0.8)
    p.ridge(hill, "#b6d0ac")
    blot(p, tower, "#eeb29b")
    blot(p, head, "#eeb29b")
    blot(p, head & (y >= 103) & (y <= 104), "#fbd9c8")

    twins, bridge = petronas()
    blot(p, twins | bridge, "#bcb0de")
    left_face = np.zeros((H, W), bool)
    for cx in TWINS:
        left_face[:, cx - 4 : cx] = True
    blot(p, twins & left_face, "#d3cbec")

    p.ridge(near.tops, "#aac8a3")
    blot(p, palms(), "#8db889")

    p.rect(0, SHORE, W, H - SHORE, "#f1eee9")
    rng = np.random.default_rng(5)
    mix = 0.55 * noise(W, 8, 4, 30.0)
    lit = lambda col: max(math.exp(-(((col - sx) / 18) ** 2)), mix[col])
    for runs, colour in strokes(rng, lit, ["#d6cdea", "#b9d3b1", "#f3b9a2"], base=0.22, gain=0.5):
        p.dashes(runs, colour)
    return p


def night() -> Picture:
    """Dark windows: the towers dark against a low violet glow, picked out with a few silver lights."""
    p = Picture("night", "#0b0c14")
    x, y = grid()
    rng = np.random.default_rng(9)
    stars(p, 34, ("#232a4c", "#6f7bb0"), seed=7)

    high = 0.25 * np.clip((y - 78) / (110 - 78), 0, 1) ** 1.6
    low = np.clip((y - 110) / (142 - 110), 0, 1) ** 1.3
    glow = (0.6 + 0.4 * np.exp(-(((x - 256) / 120) ** 2))) * (0.86 + 0.28 * noise(W, 12, 3, 9.0)[None, :])
    p.tone(high + 2.6 * low * glow, ["#121633", "#1f1c45", "#3a2252"])

    far_hill, near_hill = hills()
    p.ridge(far_hill, "#121a2c")
    p.ridge(near_hill, "#0f1624")

    blot(p, merdeka(), "#1c2142")
    blot(p, facets(), "#141831")
    fold = facets()
    edge = [(int(np.flatnonzero(fold[row])[0]), row, 1) for row in range(MERDEKA[1] + 20, SHORE - 2, 3) if fold[row].any()]
    p.dashes([e for e in edge if e[1] < 131], "#3c4266")
    p.dashes([e for e in edge if e[1] >= 131], "#8a90b4")
    p.dashes([(MERDEKA[0], row, 1) for row in range(MERDEKA[1] + 4, MERDEKA[1] + 18, 4)], "#3c4266")
    p.dashes([(MERDEKA[0], MERDEKA[1], 1)], "#e5484d")

    far, near = city()
    p.ridge(far.tops, "#141831")
    lights(p, np.maximum(far.tops + 1, 110), [("#5a4630", 2), ("#4d4a6a", 1)], chance=0.16, seed=31)

    tower, head = menara()
    hill = range_of(MENARA[1] + 1, [(MENARA[0], 7, 24)], seed=9, rough=0.6, sharp=0.8)
    p.ridge(hill, "#0c1220")
    blot(p, tower | head, "#1a1d3a")
    p.dashes([(MENARA[0] + dx, 104, 1) for dx in (-4, -2, 0, 2, 4)], "#9fd3e6")
    p.dashes([(MENARA[0], MENARA[2], 1)], "#e5484d")

    twins, bridge = petronas()
    blot(p, twins | bridge, "#161a33")
    # Silver mostly low on the shafts; up top only faint marks on the setbacks and a dim tip.
    silver, dim, faint = "#d9dcef", "#7b81a6", "#3c4266"
    p.dashes([(cx, TIP, 1) for cx in TWINS], dim)
    p.dashes([(cx + dx, yy, 1) for cx in TWINS for dx in (-3, 3) for yy in (95, 100)], faint)
    p.dashes([(cx + dx, yy, 1) for cx in TWINS for dx in (-4, 4) for yy in range(110, 122, 3)], faint)
    p.dashes([(cx + dx, yy, 1) for cx in TWINS for dx in (-4, 4) for yy in range(123, 131, 3)], dim)
    p.dashes([(cx + dx, yy, 1) for cx in TWINS for dx in (-4, 4) for yy in range(132, 145, 2)], silver)
    p.dashes([(xx, BRIDGE, 1) for xx in range(TWINS[0] + 6, TWINS[1] - 5, 2)], dim)

    p.ridge(near.tops, "#07080e")
    lights(p, near.tops, [("#b5803a", 3), ("#f0c468", 1)], chance=0.3, seed=34)
    blot(p, palms(), "#05060b")

    p.rect(0, SHORE, W, H - SHORE, "#07080f")
    under = lambda col, at, wide: math.exp(-(((col - at) / wide) ** 2))
    shine = lambda col: max(0.2, under(col, 255, 22))
    for runs, colour in strokes(rng, shine, ["#1a2142", "#6a7096", "#b5803a"], base=0.1, gain=0.5):
        p.dashes(runs, colour)
    return p
