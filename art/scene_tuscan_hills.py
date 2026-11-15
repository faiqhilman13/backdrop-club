"""Tuscan hills: a farmhouse on a crest above a winding white road and its cypresses, in gold haze by day and deep blue by night."""

from __future__ import annotations

import numpy as np

from dither import H, SHORE, W, Picture, grid, noise, stars

ID = "tuscan-hills"
NAME = "Tuscan hills"
DESCRIPTION = "Rolling Tuscan hills fading into haze, a stone farmhouse on a crest, a white road winding up between cypresses and vineyard rows on the near slope."
TAGS = ["landscape", "italy", "hills", "countryside"]

# Where the farmhouse stands: the crest of the middle hill.
HOUSE_X, HOUSE_FOOT = 252, 121

# The farmhouse, a pixel to a letter: r roof, w wall, s wall in shade, o window, d door.
HOUSE = [
    "..........rrrrr...........",
    ".........rrrrrrr..........",
    "..........wwwws...........",
    "..........wowos...........",
    "....rrrrrrwwwwsrrrrrr.....",
    "..rrrrrrrrrrrrrrrrrrrrr...",
    "...wwwwwwwwwwwwwwwwwwws...",
    "...wowwowwowwowwowwowws.rr",
    "...wwwwwwwwwwwwwwwwwwwsrrr",
    "...wwwwwwwwwwwwwwwwwwwsssw",
    "...wowwowwowdwwowwowwwssow",
    "...wwwwwwwwwdwwwwwwwwwsssw",
]

# A smaller farmhouse far off on the right.
HAMLET = [
    "....rr......",
    "...rssr.....",
    ".rrrrrrrrr..",
    "..wossossw..",
    "..wsssosssw.",
]


def runs(mask: np.ndarray):
    """A mask's pixels as one-pixel-tall strokes: (x, y, length) each."""
    out = []
    for y in np.flatnonzero(mask.any(axis=1)):
        row = np.concatenate(([False], mask[y], [False]))
        edges = np.flatnonzero(row[1:] != row[:-1])
        out += [(int(a), int(y), int(b - a)) for a, b in zip(edges[::2], edges[1::2])]
    return out


def paint(p: Picture, mask: np.ndarray, fill: str):
    p.dashes(runs(mask), fill)


def hills(base: float, bumps, seed: int, rough=0.8) -> np.ndarray:
    """Rolling hills as one skyline: smooth crests (x, height, width) summed over a base row."""
    x = np.arange(W) + 0.5
    rise = sum(height * np.exp(-(((x - at) / wide) ** 2)) for at, height, wide in bumps)
    rise = rise + rough * (noise(W, seed, 4, 12.0) - 0.5)
    return np.round(base - rise).astype(int)


def cypress(mask: np.ndarray, cx: int, foot: int, tall: int, wide: int):
    """A cypress: a dark flame, one pixel at its tip, full a little below the middle."""
    for j in range(tall):
        t = (j + 0.5) / tall
        w = wide * min(1.0, (t / 0.55) ** 0.7) * (1 - 0.3 * max(0.0, (t - 0.8) / 0.2))
        w = max(1, int(round(w)))
        mask[foot - tall + j, cx - (w - 1) // 2:cx - (w - 1) // 2 + w] = True


def avenue(mask: np.ndarray, tops: np.ndarray, x0: int, x1: int, step: int, tall: int, wide: int, seed: int):
    """A row of cypresses along a ridge, each standing on the skyline."""
    rng = np.random.default_rng(seed)
    for cx in range(x0, x1, step):
        cypress(mask, cx, int(tops[cx]) + 1, tall + int(rng.integers(-1, 2)), wide)


def road_path():
    """The white road from the farmhouse door down to the foot of the window, as points (x, y, width)."""
    knots = [(251, 121), (246, 125), (251, 129), (271, 134), (274, 139), (257, 146), (263, 153), (292, 162)]
    pts = []
    for i in range(len(knots) - 1):
        p0 = knots[max(0, i - 1)]
        p1, p2 = knots[i], knots[i + 1]
        p3 = knots[min(len(knots) - 1, i + 2)]
        for t in np.linspace(0, 1, 40, endpoint=False):
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            wide = 1 if y < 127 else 2 if y < 138 else 3 if y < 148 else 4
            pts.append((x, y, wide))
    return pts


def road():
    """The road as a mask, and the cypresses along it."""
    lane = np.zeros((H + 2, W), bool)
    trees = np.zeros((H + 2, W), bool)
    pts = road_path()
    for x, y, wide in pts:
        xi, yi = int(round(x)), int(round(y))
        if yi < H:
            lane[yi, xi - wide // 2:xi - wide // 2 + wide] = True
    # Cypresses along its right-hand side, further apart and taller as the road comes nearer.
    dist, last = 0.0, None
    for x, y, wide in pts:
        if last is not None:
            dist += float(np.hypot(x - last[0], y - last[1]))
        last = (x, y)
        gap = 3.4 + (y - HOUSE_FOOT) * 0.2
        if dist >= gap and HOUSE_FOOT + 3 < y < H:
            dist = 0.0
            tall = int(round(3 + (y - HOUSE_FOOT) * 0.3))
            w = 1 if y < 130 else 2
            cx = int(round(x + wide / 2 + 1.5 + w / 2))
            one = np.zeros_like(trees)
            cypress(one, cx, int(round(y)) + 1, tall, w)
            if not (one & lane).any():
                trees |= one
    return lane[:H], trees[:H]


def fields(crest: np.ndarray):
    """The farmhouse hill's patchwork: bands that bend over the hill, split by the road. Three masks."""
    x, y = grid()
    centre = np.full(H + 2, np.nan)
    pts = road_path()
    for row in range(H):
        xs = [px for px, py, _ in pts if abs(py - row) < 0.6]
        if xs:
            centre[row] = float(np.mean(xs))
    centre = np.where(np.isnan(centre), HOUSE_X + 6.0, centre)[:H]
    depth = y - crest[None, :]
    wobble = 5.0 * (noise(W, 87, 3, 7.0)[None, :] - 0.5)
    band = np.floor((depth + 0.16 * (x - HOUSE_X) + wobble + 4) / 11.0)
    side = (x > centre[:, None]).astype(int)
    kind = (band + side) % 3
    land = depth >= 0
    return [land & (kind == k) for k in range(3)]


def house_layers():
    """Both farmhouses as masks by letter: the big one on its crest, the small one far off on the right."""
    out = {c: np.zeros((H, W), bool) for c in "rwsod"}
    back = land()[1]
    for rows, cx, foot in ((HOUSE, HOUSE_X, HOUSE_FOOT), (HAMLET, 440, int(back[440]) + 1)):
        x0 = cx - len(rows[0]) // 2
        for j, line in enumerate(rows):
            for i, c in enumerate(line):
                if c != ".":
                    out[c][foot - len(rows) + 1 + j, x0 + i] = True
    return out


def land():
    """The same hills by day and by night: far to near, each the first row of land in every column."""
    far = hills(129, [(30, 9, 34), (100, 11, 40), (176, 8, 30), (232, 10, 34), (300, 9, 32), (370, 11, 38), (446, 9, 34), (500, 8, 28)], 81, rough=0.6)
    back = hills(135, [(60, 8, 34), (130, 6, 30), (196, 5, 26), (330, 7, 30), (392, 9, 34), (470, 7, 36)], 82, rough=0.6)
    crest = hills(162, [(HOUSE_X, 41, 66), (150, 10, 40), (360, 12, 46)], 83, rough=0.4)
    crest[HOUSE_X - 13:HOUSE_X + 14] = np.minimum(crest[HOUSE_X - 13:HOUSE_X + 14], HOUSE_FOOT + 1)
    sides = hills(166, [(130, 31, 46), (64, 26, 40), (392, 34, 52), (470, 27, 40), (530, 30, 40)], 84, rough=0.5)
    near = hills(172, [(110, 34, 70), (20, 30, 50), (440, 26, 60), (520, 24, 40)], 85, rough=0.3)
    return far, back, crest, sides, near


def vineyard(near: np.ndarray, x0: int, x1: int):
    """Vine rows on the near slope: dashes following its contour, further apart lower down."""
    out = []
    gap, depth = 3.0, 3.0
    while depth < 30:
        for x in range(x0, x1, 5):
            y = int(near[x] + depth)
            if near[x] < SHORE + 6 and y < H:
                out.append((x, y, 3))
        depth += gap
        gap += 0.7
    return out


def mist(p: Picture, top: float, bottom: float, ink: str, strength=1.0, seed=0):
    """Haze lying in a valley: no dots above `top`, thickening to solid by `bottom`."""
    _, y = grid()
    drift = 0.85 + 0.3 * noise(W, seed, 3, 6.0)[None, :]
    p.tone(strength * np.clip((y - top) / (bottom - top), 0, 1) * drift, [ink], foot=int(bottom) + 6)


def trees_by_house() -> np.ndarray:
    """Cypresses round the two farmhouses, and a row of small ones along the far ridge on the right."""
    far, back, crest, sides, near = land()
    m = np.zeros((H, W), bool)
    for cx, tall, wide in ((235, 14, 3), (240, 17, 3), (244, 12, 2), (270, 13, 3)):
        cypress(m, cx, HOUSE_FOOT + 1, tall, wide)
    for cx, tall in ((433, 6), (447, 7), (450, 5)):
        cypress(m, cx, int(back[cx]) + 1, tall, 2)
    avenue(m, back, 318, 392, 5, 6, 2, seed=1)
    return m


def ridge_rows() -> np.ndarray:
    """Rows of tall cypresses along the crests of the side hills."""
    far, back, crest, sides, near = land()
    m = np.zeros((H, W), bool)
    avenue(m, sides, 106, 158, 6, 10, 3, seed=2)
    avenue(m, sides, 366, 420, 6, 11, 3, seed=3)
    return m


def far_row() -> np.ndarray:
    """A thin line of cypresses on the farthest ridge, out to the left."""
    m = np.zeros((H, W), bool)
    avenue(m, land()[0], 44, 92, 5, 4, 1, seed=4)
    return m


def day() -> Picture:
    """Light windows: gold haze, sage and wheat hills, a pale stone farmhouse under a terracotta roof."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()

    rise = np.clip((y - 76) / (132 - 76), 0, 1) ** 1.7
    glow = np.exp(-(((x - HOUSE_X) / 150) ** 2))
    drift = 0.88 + 0.24 * noise(W, 21, 3, 8.0)[None, :]
    p.tone(rise * (0.45 + 0.9 * glow) * drift, ["#f8eecf", "#f3e1b3"], foot=136)

    far, back, crest, sides, near = land()
    p.ridge(far, "#dfe4d3", foot=136)
    paint(p, far_row(), "#b4c6a6")
    mist(p, 121, 133, "#f7f1de", 1.25, seed=31)
    p.ridge(back, "#d1dab6", foot=146)
    mist(p, 130, 143, "#f6efda", 1.2, seed=32)

    for mask, colour in zip(fields(crest), ("#ecd9a1", "#dcdcab", "#efd4b2")):
        paint(p, mask, colour)
    lane, lined = road()
    paint(p, lane, "#fbf7ec")
    paint(p, lined | trees_by_house(), "#97b487")
    parts = house_layers()
    for key, colour in (("w", "#f1e4c9"), ("s", "#e4d0b0"), ("r", "#e8b295"), ("o", "#c9ab8b"), ("d", "#c9ab8b")):
        paint(p, parts[key], colour)

    p.ridge(sides, "#cbd29c", foot=H)
    paint(p, ridge_rows(), "#97b487")
    p.ridge(near, "#dcd5a3", foot=H)
    p.dashes(vineyard(near, 0, 214), "#adb67f")
    p.dashes(vineyard(near, 384, W), "#adb67f")
    return p


def night() -> Picture:
    """Dark windows: deep blue hills, black cypresses, warm farmhouse windows, fireflies low down."""
    p = Picture("night", "#0b0c14")
    _, y = grid()

    stars(p, 34, ("#262c4c", "#6a76a8"), seed=29)
    rise = np.clip((y - 84) / (132 - 84), 0, 1) ** 1.8
    drift = 0.9 + 0.2 * noise(W, 22, 3, 8.0)[None, :]
    p.tone(1.6 * rise * drift, ["#121733", "#18204a"], foot=136)

    far, back, crest, sides, near = land()
    p.ridge(far, "#1b2449", foot=136)
    paint(p, far_row(), "#0c1027")
    mist(p, 121, 133, "#1f2851", 1.25, seed=31)
    p.ridge(back, "#141b3d", foot=146)
    mist(p, 130, 143, "#1a2249", 1.2, seed=32)

    for mask, colour in zip(fields(crest), ("#0f1533", "#111838", "#0e1430")):
        paint(p, mask, colour)
    lane, lined = road()
    paint(p, lane, "#272e50")
    paint(p, lined | trees_by_house(), "#04050b")
    parts = house_layers()
    lit = parts["o"].copy()
    rng = np.random.default_rng(4)
    for yy, xx in zip(*np.nonzero(parts["o"])):
        if rng.random() < 0.45:
            lit[yy, xx] = False
    for key, colour in (("w", "#1d2238"), ("s", "#151a2d"), ("r", "#2a1f31"), ("d", "#e9a650")):
        paint(p, parts[key], colour)
    paint(p, parts["o"] & ~lit, "#10131f")
    paint(p, lit, "#f4c46c")

    p.ridge(sides, "#0b1029", foot=H)
    paint(p, ridge_rows(), "#04050b")
    p.ridge(near, "#080b1d", foot=H)
    p.dashes(vineyard(near, 0, 214), "#121a35")
    p.dashes(vineyard(near, 384, W), "#121a35")

    # Fireflies: a few warm dots low over the near slopes, most of them out to the sides.
    rng = np.random.default_rng(13)
    dim, bright = [], []
    for i in range(24):
        fx = int(rng.choice([rng.integers(96, 196), rng.integers(316, 420), rng.integers(4, W - 4)]))
        fy = int(rng.integers(134, 157))
        (bright if i % 3 == 0 else dim).append((fx, fy, 1))
    p.dashes(dim, "#8f9a4c")
    p.dashes(bright, "#e3ea8e")
    return p
