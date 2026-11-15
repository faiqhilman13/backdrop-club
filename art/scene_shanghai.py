"""Shanghai: Lujiazui across the Huangpu, in rose morning haze by day and lit up over a dark river by night."""

from __future__ import annotations

import math

import numpy as np

from dither import H, SHORE, W, Picture, Skyline, grid, lights, noise, stars, strokes

ID = "shanghai"
NAME = "Shanghai"

# Where the four landmarks stand, left to right, and where the sun comes up.
PEARL, JINMAO, SWFC, TOWER = 206, 244, 272, 300
SUN = (340.0, 129.0, 13.0)
# The two boats: (first column, first row, last column, last row).
FERRY, BARGE = (258, 149, 264, 152), (140, 152, 148, 154)


# ---- helpers the kit lacks ----


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


def tops_of(mask: np.ndarray, ceiling: int = 0) -> np.ndarray:
    """The first row of a shape in every column, for `lights`; never above `ceiling`."""
    return np.maximum(np.where(mask.any(axis=0), mask.argmax(axis=0), SHORE), ceiling)


def edge(mask: np.ndarray, rows, side: int = 0, on: int = 2, off: int = 1):
    """A column of dashes down one edge of a shape: `side` 0 is its left, -1 its right."""
    out = []
    for i, row in enumerate(range(*rows)):
        hit = np.flatnonzero(mask[row])
        if hit.size and i % (on + off) < on:
            out.append((int(hit[side]), row, 1))
    return out


class Bulbs:
    """Stands in for a picture while `lights` runs, so many calls end as one path a colour."""

    def __init__(self):
        self.runs: dict[str, list] = {}

    def dashes(self, runs, fill: str):
        self.runs.setdefault(fill, []).extend(runs)

    def onto(self, p: Picture):
        for fill, runs in self.runs.items():
            p.dashes(runs, fill)


def windows(p: Picture, tops: np.ndarray, palettes, seed: int, most: float = 0.45, dark: float = 0.25):
    """Lit windows building by building: each stretch of one roof height takes one palette
    and its own share of lit windows, and some stay dark."""
    rng = np.random.default_rng(seed)
    bulbs = Bulbs()
    start = 0
    for col in range(1, W + 1):
        if col < W and tops[col] == tops[start]:
            continue
        palette = palettes[int(rng.integers(len(palettes)))]
        chance = 0.0 if rng.random() < dark else float(rng.uniform(0.12, most))
        if chance and col - start >= 3 and tops[start] < SHORE - 4:
            lights(bulbs, tops, palette, chance=chance, step=(2, 3), seed=int(rng.integers(1 << 30)), x0=start + 1, x1=col - 1)
        start = col
    bulbs.onto(p)


def river(p: Picture, seed: int, lit, tint, base: float, gain: float):
    """Strokes on the water, each taking the colour of what stands above it, and none across the boats."""
    rng = np.random.default_rng(seed)
    by: dict[str, list] = {}
    for runs, _ in strokes(rng, lit, [None], base=base, gain=gain):
        for col, row, n in runs:
            if any(a - 3 < col + n and col < c + 3 and b - 1 <= row <= d + 1 for a, b, c, d in (FERRY, BARGE)):
                continue
            by.setdefault(tint(col + n // 2, row), []).append((col, row, n))
    for colour, runs in by.items():
        p.dashes(runs, colour)


def boats(p: Picture, hull: str, lamp=None):
    """Two small boats on the river: a ferry and a barge."""
    fx, fy = FERRY[:2]
    bx, by = BARGE[:2]
    p.dashes([(fx + 3, fy, 1), (fx + 2, fy + 1, 3), (fx, fy + 2, 7), (fx + 1, fy + 3, 5)], hull)
    p.dashes([(bx + 6, by, 2), (bx, by + 1, 9), (bx + 1, by + 2, 7)], hull)
    if lamp:
        p.dashes([(fx + 3, fy + 1, 1), (bx + 6, by, 1)], lamp)


# ---- the place: the same in both lights ----


def pearl_tower():
    """The Oriental Pearl Tower as two masks: its mast, antenna and legs, and its spheres."""
    x, y = grid()
    frame = np.zeros((H, W), bool)
    frame[86:101, PEARL] = True
    frame[101:SHORE, PEARL - 1 : PEARL + 2] = True
    for row in range(131, SHORE):  # the legs lean out a pixel every two rows
        out = 3 + (row - 131) // 2
        frame[row, PEARL - out - 1 : PEARL - out + 1] = True
        frame[row, PEARL + out : PEARL + out + 2] = True
    ball = lambda cy, r: (x - PEARL - 0.5) ** 2 + (y - cy - 0.5) ** 2 <= r * r
    return frame, ball(127, 5.5) | ball(113, 3.6) | ball(102, 2.0)


def shanghai_tower() -> np.ndarray:
    """The tallest: a smooth taper with a lopsided, notched crown."""
    m = np.zeros((H, W), bool)
    top = 88
    for row in range(top, SHORE):
        w = 5 + int(round(6 * ((row - top) / (SHORE - 1 - top)) ** 0.9))
        m[row, TOWER - w // 2 : TOWER - w // 2 + w] = True
    m[88:89, TOWER - 2] = False
    m[88:93, TOWER] = False
    m[88:90, TOWER + 1] = False
    m[88:91, TOWER + 2] = False
    return m


def world_financial_center():
    """A tall slab with a trapezoid opening under its top edge: the slab, and the rim of the opening."""
    m = np.zeros((H, W), bool)
    m[100:SHORE, SWFC - 4 : SWFC + 5] = True
    hole = np.zeros((H, W), bool)
    hole[102:104, SWFC - 2 : SWFC + 3] = True
    hole[104:106, SWFC - 1 : SWFC + 2] = True
    rim = np.zeros((H, W), bool)
    rim[1:] |= hole[:-1]
    rim[:-1] |= hole[1:]
    rim[:, 1:] |= hole[:, :-1]
    rim[:, :-1] |= hole[:, 1:]
    return m & ~hole, rim & ~hole


def jin_mao() -> np.ndarray:
    """Tiers that shorten as they climb, each under a jutting eave, and a small spire."""
    m = np.zeros((H, W), bool)
    row = SHORE
    for w, h in [(9, 18), (7, 9), (5, 6), (3, 4)]:
        m[row - h : row, JINMAO - w // 2 : JINMAO + w // 2 + 1] = True
        row -= h
        if w < 9:  # the eave: a row a pixel wider each side
            m[row, JINMAO - w // 2 - 1 : JINMAO + w // 2 + 2] = True
    m[row - 4 : row, JINMAO] = True
    return m


def far_blocks() -> Skyline:
    """The towers behind: tallest round the landmarks, low in front of the sun, falling away to both sides."""
    s = Skyline()
    s.blocks(0, 64, 138, 133, seed=11, widths=(7, 15), gap=(0, 1))
    s.blocks(64, 158, 137, 129, seed=12, widths=(6, 13), gap=(0, 1))
    s.blocks(384, 452, 137, 129, seed=14, widths=(6, 13), gap=(0, 1))
    s.blocks(452, W, 138, 133, seed=15, widths=(7, 15), gap=(0, 1))
    x0 = 158
    for w, top in [
        (9, 133), (7, 128), (8, 134), (7, 124), (6, 130), (6, 135), (11, 133),  # left of the Pearl and behind it
        (5, 120), (2, 131), (5, 120), (8, 129), (6, 123), (12, 130),  # the twins, then on behind Jin Mao
        (7, 127), (7, 119), (4, 131), (9, 131), (7, 125), (6, 117), (5, 129), (11, 129),  # to the tallest
        (7, 123), (7, 118), (8, 128), (9, 134), (9, 135), (7, 132),  # low where the sun comes up
        (8, 126), (9, 133), (7, 128), (7, 134),
    ]:
        s.box(x0, w, top)
        x0 += w
    # A few roofs that are not flat.
    s.box(213, 3, 118).box(220, 3, 118).box(259, 3, 116).box(315, 3, 115).spire(185, 120)
    s.tops = np.minimum(s.tops, 139)
    return s


def near_blocks() -> Skyline:
    """The waterfront: low blocks, lowest at the Pearl's feet, and older buildings out at the sides."""
    s = Skyline()
    s.blocks(0, W, 144, 141, seed=21, widths=(8, 20), gap=(0, 1))
    for x0, w, top in [
        (152, 10, 138), (164, 8, 141), (173, 10, 136), (185, 8, 139),
        (221, 9, 138), (232, 8, 135), (242, 11, 140), (255, 10, 137), (267, 9, 141), (278, 11, 136),
        (291, 9, 139), (302, 12, 134), (316, 10, 138), (328, 12, 141), (342, 9, 139), (353, 9, 136),
    ]:
        s.box(x0, w, top)
    s.tops[194:220] = np.maximum(s.tops[194:220], 143)
    # The old waterfront. In a normal window: a clock tower at the left edge, a pointed roof at the right.
    s.box(136, 16, 140).stack(145, [(5, 15), (3, 3), (1, 3)])
    s.box(362, 14, 139).taper(368, 7, 1, 131, 139)
    # Further out, for wide windows: domes, a pediment, another tower.
    s.box(100, 20, 140).dome(110, 4, 140)
    s.box(70, 18, 141).stack(84, [(5, 12), (3, 2), (1, 2)])
    s.box(34, 22, 141).taper(45, 11, 1, 136, 141)
    s.box(4, 18, 140).dome(13, 3, 140)
    s.box(380, 18, 141).dome(390, 3, 141)
    s.box(404, 22, 140).stack(418, [(5, 13), (3, 2), (1, 3)])
    s.box(440, 20, 141).taper(450, 11, 1, 136, 141)
    s.box(474, 22, 140).dome(486, 4, 140)
    return s


# ---- the two lights ----


def day() -> Picture:
    """Light windows: a low sun in lilac and rose haze, the towers in pastels."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()
    sun_x, sun_y, sun_r = SUN

    # Morning haze: nothing high up, lilac low down, rose round the sun.
    rise = np.clip((y - 68) / (140 - 68), 0, 1) ** 1.9
    halo = np.exp(-(((x - sun_x) / 90) ** 2) - ((y - sun_y) / 50) ** 2)
    drift = 0.88 + 0.24 * noise(W, 7, 3, 8.0)[None, :]
    p.tone(rise * (0.3 + 1.25 * halo) * drift, ["#e7dff2", "#f5c4d3"])

    # The sun: a pale disc, dotted thicker toward its foot.
    p.disc(sun_x, sun_y, sun_r, "#f9d0d6")
    p.disc(sun_x, sun_y, sun_r, p.level("#f2a2b8", 5), rows=(int(sun_y - sun_r), int(sun_y - 4)))
    p.disc(sun_x, sun_y, sun_r, p.level("#f2a2b8", 9), rows=(int(sun_y - 4), int(sun_y + sun_r) + 1))

    frame, spheres = pearl_tower()
    slab, _ = world_financial_center()
    p.ridge(far_blocks().tops, "#d9cdeb")
    blot(p, shanghai_tower() | slab | jin_mao() | frame, "#aab5e8")
    blot(p, spheres, "#ec9db7")
    p.ridge(near_blocks().tops, "#86c9ba")

    # The river: the page again, the skyline and the sun lying on it in short strokes.
    p.rect(0, SHORE, W, H - SHORE, "#f1ebef")
    under = lambda col, at, wide: math.exp(-(((col - at) / wide) ** 2))
    lit = lambda col: max(under(col, sun_x, 18), 0.8 * under(col, PEARL, 8), 0.5 * under(col, 272, 40))

    def tint(col, row):
        if abs(col - sun_x) < 16 or abs(col - PEARL) < 8:
            return "#ee93af"
        if min(abs(col - JINMAO), abs(col - SWFC), abs(col - TOWER)) < 7:
            return "#a9b5e6"
        return "#d3c8e8" if (col + row) % 3 else "#9ed3c7"

    river(p, 4, lit, tint, base=0.22, gain=0.5)
    boats(p, "#8894d6")
    return p


def night() -> Picture:
    """Dark windows: the towers dark on a violet glow, the Pearl lit pink, lights on the river."""
    p = Picture("night", "#0b0c14")
    x, y = grid()
    stars(p, 36, ("#26264a", "#6c63a8"), seed=3)

    # The city's glow: low, violet turning magenta at the horizon, strongest behind the towers.
    rise = np.clip((y - 80) / (144 - 80), 0, 1) ** 1.6
    city = np.exp(-(((x - 250) / 140) ** 2))
    drift = 0.85 + 0.3 * noise(W, 8, 4, 10.0)[None, :]
    cap = 0.3 + 2.7 * np.clip((y - 100) / (138 - 100), 0, 1) ** 1.25
    p.tone(np.minimum(rise * (0.7 + 2.3 * city) * drift, cap), ["#1f1a48", "#3a1b63", "#7a2682"])

    far, near = far_blocks(), near_blocks()
    frame, spheres = pearl_tower()
    tower, (slab, rim), pagoda = shanghai_tower(), world_financial_center(), jin_mao()
    warm, cool, pink, violet = "#f0c877", "#8fd3e6", "#ef7fb9", "#b79cf2"

    p.ridge(far.tops, "#13142c")
    windows(p, far.tops, [[("#5d5470", 3), ("#b8975f", 2)], [("#5d5470", 2), ("#5f8fa8", 2)], [("#b8975f", 1)]], seed=31, most=0.4)

    blot(p, tower | slab | pagoda, "#181b3d")
    bulbs = Bulbs()
    lights(bulbs, tops_of(tower, 110), [(cool, 3), (warm, 1)], chance=0.24, seed=32, x0=TOWER - 3, x1=TOWER + 5)
    lights(bulbs, tops_of(slab, 110), [(violet, 3), (warm, 1)], chance=0.26, seed=33, x0=SWFC - 3, x1=SWFC + 4)
    lights(bulbs, tops_of(pagoda, 109), [(warm, 4), ("#f6e3b0", 1)], chance=0.45, seed=34, x0=JINMAO - 3, x1=JINMAO + 4)
    bulbs.onto(p)
    # Edge lights: dim where the chat is, bright below it.
    for runs, (dim, bright) in [(edge(tower, (89, 141), 0), ("#2c7f96", "#62d5e6")), (edge(slab, (107, 141), -1), ("#5a4cae", "#a98cf0"))]:
        p.dashes([r for r in runs if r[1] < 108], dim)
        p.dashes([r for r in runs if r[1] >= 108], bright)
    blot(p, rim, "#6a5cc6")
    p.dashes([(JINMAO, 105, 1)], "#f6e3b0")

    # The Pearl: a violet frame, its spheres lit pink and dotted brighter, lights up the antenna.
    blot(p, frame, "#44327e")
    blot(p, spheres, "#b23a8a")
    blot(p, spheres, p.level("#f77fc0", 7))
    p.dashes([(PEARL, row, 1) for row in range(87, 100, 2)], "#a04a98")

    p.ridge(near.tops, "#07080e")
    windows(p, near.tops, [[(warm, 4), (cool, 1)], [(warm, 3), (pink, 1)], [(warm, 1)]], seed=35, most=0.5, dark=0.2)

    # The river: black, the lights lying on it in broken strokes.
    p.rect(0, SHORE, W, H - SHORE, "#08090f")
    under = lambda col, at, wide: math.exp(-(((col - at) / wide) ** 2))
    lit = lambda col: max(under(col, PEARL, 10), 0.7 * under(col, 272, 34), 0.2)

    def tint(col, row):
        if abs(col - PEARL) < 9:
            return "#d9539f"
        if abs(col - TOWER) < 8:
            return "#2f8ea8"
        if abs(col - SWFC) < 7:
            return "#6a5cc6"
        if abs(col - JINMAO) < 7:
            return "#b8975f"
        return "#2b2466" if (col + row) % 3 else "#1f5a70"

    river(p, 6, lit, tint, base=0.1, gain=0.6)
    boats(p, "#2a2f66", warm)
    return p
