"""Singapore: Marina Bay Sands across the bay, in mint and peach haze by day and lit up over dark water by night."""

from __future__ import annotations

import math

import numpy as np

from dither import H, SHORE, W, Picture, Skyline, grid, lights, noise, stars, strokes

ID = "singapore"
NAME = "Singapore"
DESCRIPTION = "Marina Bay Sands and its SkyPark over Marina Bay, with the ArtScience Museum, the Supertrees, the Singapore Flyer and the city behind."
TAGS = ["city", "skyline", "singapore", "marina-bay"]

# Where things stand, the same by day and by night.
FLYER = (152, 121, 10)  # the wheel: centre column, centre row, radius
ASM_X = 205  # the ArtScience Museum
PROW, STERN, DECK = 223, 293, 100  # the SkyPark: its overhanging end, its other end, its top row
TOWERS = (238, 260, 282)  # each hotel tower's left edge under the SkyPark
TOWER_W = 8
# The Supertrees: (left column of the trunk, canopy row, canopy width), trunks two wide.
TREES = [(310, 127, 10), (322, 119, 12), (334, 125, 10), (346, 116, 12), (358, 128, 10)]
SKYWAY = 135
SUN = (339.0, 124.0, 11.0)


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


def dots(mask: np.ndarray) -> list:
    """A mask's pixels as one-pixel dashes."""
    ys, xs = np.nonzero(mask)
    return [(int(x), int(y), 1) for x, y in zip(xs, ys)]


def tops_of(mask: np.ndarray, ceiling: int = 0) -> np.ndarray:
    """The first row of a shape in every column, for `lights`; never above `ceiling`."""
    return np.maximum(np.where(mask.any(axis=0), mask.argmax(axis=0), SHORE), ceiling)


def line(mask: np.ndarray, x0: float, y0: float, x1: float, y1: float):
    """A one-pixel line between two points."""
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for t in np.linspace(0.0, 1.0, n + 1):
        mask[int(round(y0 + (y1 - y0) * t)), int(round(x0 + (x1 - x0) * t))] = True


def circle(cx: int, cy: int, r: int) -> np.ndarray:
    """A one-pixel ring round pixel (cx, cy), drawn the midpoint way so it has no gaps or lumps."""
    m = blank()
    x, y, err = r, 0, 1 - r
    while x >= y:
        for dx, dy in ((x, y), (y, x), (-y, x), (-x, y), (-x, -y), (-y, -x), (y, -x), (x, -y)):
            m[cy + dy, cx + dx] = True
        y += 1
        if err < 0:
            err += 2 * y + 1
        else:
            x -= 1
            err += 2 * (y - x) + 1
    return m


# ---- the place: the same in both lights ----


def skypark():
    """The SkyPark: a long ship across the three tower tops, overhanging far at its north end.
    Returns (ship, trees): its hull and deck, and the trees standing on the deck."""
    m, trees = blank(), blank()
    for x in range(PROW, STERN + 1):
        d = x - PROW
        rows = 1 if d < 3 else 2 if d < 9 else 3
        m[DECK : DECK + rows, x] = True
    m[DECK + 2, STERN] = False
    for x in (241, 242, 251, 263, 264, 270, 279, 287):
        trees[DECK - 1, x] = True
    return m, trees


def hotel() -> np.ndarray:
    """The three hotel towers under the SkyPark: slim slabs, each curving out a little on one side toward the ground."""
    m = blank()
    for left in TOWERS:
        for y in range(DECK + 3, SHORE):
            s = int(round(3.0 * max(0.0, (y - 118) / (SHORE - 1 - 118)) ** 1.8))
            m[y, left - s : left + TOWER_W] = True
    return m


def curve() -> np.ndarray:
    """The side of each hotel tower that curves out toward the ground: its two left columns and the flare."""
    m = blank()
    for left in TOWERS:
        m[DECK + 3 : SHORE, left - 4 : left + 2] = True
    return m


def artscience() -> np.ndarray:
    """The ArtScience Museum: a round bowl on a short stem, its broad petals rising to points of different heights."""
    m = blank()
    cx = ASM_X
    for y, half in zip(range(131, 145), [12, 12, 11, 11, 10, 9, 8, 7, 6, 5, 4, 3, 3, 2]):
        m[y, cx - half : cx + half + 1] = True
    for bx, tx, ty in [(-10, -15, 127), (-6, -9, 123), (-3, -4, 121), (0, 1, 120), (3, 6, 121), (6, 10, 124), (10, 14, 128)]:
        n = 132 - ty
        for i in range(n + 1):
            f = i / n  # 0 at the tip, 1 at the base
            c = cx + tx + (bx - tx) * f
            w = 2.0 if i == 0 else 3.0 if i < 3 else 3.0 + 1.4 * f
            m[ty + i, int(round(c - w / 2)) : int(round(c - w / 2)) + int(round(w))] = True
    m[SHORE - 1, cx - 5 : cx + 6] = True
    return m


def supertrees():
    """The Supertrees: tall trunks opening into funnels under wide canopies, and the skyway between them.
    Returns (trunks, funnels, canopies, skyway)."""
    trunks, funnels, canopies, way = blank(), blank(), blank(), blank()
    for left, top, cw in TREES:
        cx = left + 1  # the trunk is columns left and left + 1
        a = cx - cw // 2 + 1
        canopies[top, a : a + cw] = True
        canopies[top - 1, a : a + cw : 2] = True
        y = top + 1
        for w in [cw - 2, cw - 4, cw - 6, cw - 6, cw - 8, cw - 8] if cw > 10 else [cw - 2, cw - 4, cw - 6, cw - 6, cw - 8]:
            w = max(w, 2)
            funnels[y, cx - w // 2 + 1 : cx + w // 2 + 1] = True
            y += 1
        trunks[y:SHORE, left : left + 2] = True
        trunks[SHORE - 2 : SHORE, left - 1 : left + 3] = True
    a, b = TREES[1][0] + 1, TREES[3][0]
    for x in range(a, b + 1):
        way[SKYWAY - (1 if abs(x - (a + b) / 2) < 7 else 0), x] = True
    return trunks, funnels, canopies, way & ~trunks


def flyer():
    """The Singapore Flyer: a thin wheel with its cabins, spokes, hub and the A-frame it stands on.
    Returns (rim, spokes, frame)."""
    cx, cy, r = FLYER
    rim, spokes, frame = circle(cx, cy, r), blank(), blank()
    for k in range(20):
        a = 2 * math.pi * k / 20
        rim[int(round(cy + (r + 1) * math.sin(a))), int(round(cx + (r + 1) * math.cos(a)))] = True
    for k in range(6):
        a = 2 * math.pi * k / 6 + math.pi / 6
        line(spokes, cx, cy, cx + (r - 1) * math.cos(a), cy + (r - 1) * math.sin(a))
    frame[cy - 1 : cy + 2, cx - 1 : cx + 2] = True
    line(frame, cx, cy, cx - 6, 139)
    line(frame, cx, cy, cx + 6, 139)
    return rim, spokes & ~frame, frame


def far_city() -> Skyline:
    """The farthest towers: the business district behind the museum, more out to the right, low behind the Flyer and the hotel."""
    s = Skyline()
    s.blocks(0, 96, 133, 118, seed=3, widths=(6, 12), gap=(0, 2))
    s.blocks(96, 138, 128, 106, seed=4, widths=(5, 9), gap=(0, 2))
    s.box(138, 26, 137)
    for x0, w, top in [
        (164, 5, 113), (169, 6, 106), (175, 6, 100), (181, 5, 108), (186, 7, 103), (193, 6, 110), (199, 6, 106), (205, 7, 116),
        (212, 9, 124), (221, 82, 134),
        (303, 6, 132), (360, 8, 121), (368, 6, 110), (374, 7, 104), (381, 6, 112), (387, 8, 117), (395, 9, 123),
    ]:
        s.box(x0, w, top)
    s.blocks(404, W, 132, 112, seed=5, widths=(5, 10), gap=(0, 2))
    # Crowns: a stepped top, a slanted one and a split one.
    s.box(176, 4, 98).box(177, 2, 96)
    for i in range(6):
        s.box(186 + i, 1, 101 + i)
    s.tops[201] = 109
    s.box(375, 5, 102)
    return s


def mid_city() -> Skyline:
    """Nearer towers, a shade deeper: the bayfront's offices in front of the business district."""
    s = Skyline()
    for x0, w, top in [
        (100, 7, 122), (107, 9, 128), (116, 6, 118), (122, 8, 126), (130, 6, 131),
        (166, 7, 124), (173, 5, 118), (178, 8, 121), (186, 6, 126), (192, 6, 129),
        (366, 7, 127), (373, 9, 121), (382, 6, 125), (388, 8, 129), (420, 8, 124), (428, 6, 119), (434, 9, 127),
    ]:
        s.box(x0, w, top)
    return s


def waterfront() -> Skyline:
    """The near shore: promenades, the Flyer's terminal, the bridge, the mall under the hotel, the gardens."""
    s = Skyline()
    s.blocks(0, 136, 144, 138, seed=21, widths=(8, 18), gap=(0, 2))
    s.box(136, 30, 140)  # the Flyer's terminal
    s.box(166, 26, 142)  # the Helix Bridge's deck
    s.box(218, 82, 141)  # the mall along the promenade
    for x in range(220, 298, 8):
        s.box(x, 4, 140)
    s.box(300, 66, 142)  # the gardens' edge
    s.blocks(366, W, 144, 138, seed=22, widths=(8, 18), gap=(0, 2))
    return s


def domes() -> np.ndarray:
    """The two glass conservatories by the gardens, for wider windows."""
    x, y = grid()
    yy = np.minimum(y, 142.0)
    flower = ((x - 376) / 13) ** 2 + ((yy - 142) / 7) ** 2 <= 1
    cloud = ((x - 392) / 7) ** 2 + ((yy - 142) / 10) ** 2 <= 1
    return (flower | cloud) & (y < SHORE)


def esplanade() -> np.ndarray:
    """The Esplanade's two spiky domes by the water, for the widest windows."""
    x, y = grid()
    yy = np.minimum(y, 144.0)
    big = ((x - 104) / 12) ** 2 + ((yy - 144) / 10) ** 2 <= 1
    small = ((x - 124) / 8) ** 2 + ((yy - 144) / 7) ** 2 <= 1
    return (big | small) & (y < SHORE)


# ---- the two lights ----


def day() -> Picture:
    """Light windows: a pale sun over the gardens, the hotel in teal, mint and peach about it."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()
    sx, sy, sr = SUN

    rise = np.clip((y - 72) / (142 - 72), 0, 1) ** 1.9
    halo = np.exp(-(((x - sx) / 100) ** 2) - ((y - sy) / 50) ** 2)
    drift = 0.9 + 0.2 * noise(W, 6, 3, 8.0)[None, :]
    p.tone(rise * (0.35 + 1.15 * halo) * drift, ["#e2efe8", "#fbe0cf"])

    p.disc(sx, sy, sr, "#fcdcca")
    p.disc(sx, sy, sr, p.level("#f6b9a0", 5), rows=(int(sy - sr), int(sy - 3)))
    p.disc(sx, sy, sr, p.level("#f6b9a0", 9), rows=(int(sy - 3), int(sy + sr) + 1))

    p.ridge(far_city().tops, "#dce9e7")
    p.ridge(mid_city().tops, "#c7dfdc")

    rim, spokes, frame = flyer()
    blot(p, spokes, "#c2dfe0")
    blot(p, rim | frame, "#86bcc2")

    trunks, funnels, canopies, way = supertrees()
    blot(p, trunks | funnels | way, "#7dbdb5")
    blot(p, canopies, "#93cfb6")

    ship, deck_trees = skypark()
    tower = hotel()
    blot(p, tower | ship, "#86c3bd")
    blot(p, tower & curve(), "#a6d6cf")
    blot(p, deck_trees, "#9fd6bf")
    asm = artscience()
    blot(p, asm, "#f8d5d6")
    blot(p, asm & (x > ASM_X + 0.5) & (y > 129), p.level("#efacb8", 6))
    blot(p, domes(), "#c8dfe6")
    p.ridge(waterfront().tops, "#a6d8c3")
    blot(p, esplanade(), "#f3c7b4")
    blot(p, esplanade(), p.level("#e9a993", 6))

    p.rect(0, SHORE, W, H - SHORE, "#eef2ec")
    rng = np.random.default_rng(5)
    mix = 0.55 * noise(W, 8, 4, 30.0)
    lit = lambda col: max(math.exp(-(((col - sx) / 18) ** 2)), mix[col])
    for runs, colour in strokes(rng, lit, ["#bfe0da", "#f7cdb6", "#f2a98c"], base=0.22, gain=0.5):
        p.dashes(runs, colour)
    return p


def night() -> Picture:
    """Dark windows: the bay at night, the hotel's windows warm, the Supertrees glowing low."""
    p = Picture("night", "#0b0c14")
    x, y = grid()
    rng = np.random.default_rng(9)
    stars(p, 34, ("#232a4c", "#6f7bb0"), seed=6)

    high = 0.25 * np.clip((y - 70) / (104 - 70), 0, 1) ** 1.6
    low = np.clip((y - 104) / (142 - 104), 0, 1) ** 1.3
    glow = (0.6 + 0.5 * np.exp(-(((x - 330) / 70) ** 2))) * (0.86 + 0.28 * noise(W, 12, 3, 9.0)[None, :])
    p.tone(high + 2.6 * low * glow, ["#111634", "#1d1d4a", "#3b1f63"])

    far = far_city()
    p.ridge(far.tops, "#141a33")
    lights(p, np.maximum(far.tops + 1, 104), [("#4d4a6a", 2), ("#5a4630", 1)], chance=0.14, seed=31)
    mid = mid_city()
    p.ridge(mid.tops, "#181d38")
    lights(p, np.maximum(mid.tops + 1, 104), [("#5a4630", 2), ("#6b4d2e", 1)], chance=0.2, seed=35)

    rim, spokes, frame = flyer()
    blot(p, spokes, p.level("#1d3550", 8))
    blot(p, frame, "#16203c")
    blot(p, rim, "#2b6f8a")

    trunks, funnels, canopies, way = supertrees()
    blot(p, trunks | way, "#140f2a")
    blot(p, funnels, "#2a1748")
    blot(p, funnels, p.level("#7a3fb0", 6))
    blot(p, canopies, "#8a3a8a")
    blot(p, canopies, p.level("#e05aa8", 8))
    p.dashes(dots(way)[::3], "#4fb3c0")

    tower, (deck, deck_trees) = hotel(), skypark()
    blot(p, tower | deck | deck_trees, "#1a2244")
    blot(p, tower & curve(), "#222b52")
    lights(p, np.maximum(tops_of(tower) + 1, 104), [("#5a4630", 1)], chance=0.35, step=(2, 3), seed=32, foot=131)
    lights(p, np.maximum(tops_of(tower), 131), [("#b5803a", 2), ("#f0c468", 1)], chance=0.4, step=(2, 3), seed=33)
    p.dashes([(xx, DECK + 2, 1) for xx in range(PROW + 9, STERN, 3)], "#3d4f8f")

    asm = artscience()
    blot(p, asm, "#2c2250")
    blot(p, asm & (y > 135), p.level("#7a4a86", 6))
    tips = tops_of(asm)
    p.dashes([(c, int(tips[c]), 1) for c in range(ASM_X - 16, ASM_X + 17) if tips[c] < 131 and tips[c] < tips[c - 1] and tips[c] <= tips[c + 1]], "#c873a8")
    blot(p, domes(), "#132a3a")

    near = waterfront()
    p.ridge(near.tops, "#06070d")
    lights(p, near.tops, [("#b5803a", 2), ("#f0c468", 1), ("#54c8c8", 1)], chance=0.3, seed=34)
    blot(p, esplanade(), "#141129")
    blot(p, esplanade(), p.level("#3b2a52", 5))

    p.rect(0, SHORE, W, H - SHORE, "#07080f")
    pink = lambda col: math.exp(-(((col - 334) / 26) ** 2))
    warm = lambda col: math.exp(-(((col - 266) / 30) ** 2))
    shine = lambda col: max(0.2, pink(col), 0.9 * warm(col))

    def tint(col):
        if pink(col) > warm(col) and pink(col) > 0.3:
            return 2 if col % 3 else 1
        if warm(col) > 0.3:
            return 3
        return 0

    palette = ["#1a2142", "#2fb3b8", "#c04aa0", "#b5803a"]
    by = {c: [] for c in palette}
    for runs, _ in strokes(rng, shine, [None], base=0.1, gain=0.5):
        for col, row, n in runs:
            by[palette[tint(col + n // 2)]].append((col, row, n))
    for colour, runs in by.items():
        p.dashes(runs, colour)
    return p
