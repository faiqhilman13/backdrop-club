"""Savannah: a low apricot sun behind umbrella acacias and a pair of giraffes by day, a big pale moon rising over the same plain by night."""

from __future__ import annotations

import math

import numpy as np

from dither import H, MID, SHORE, W, Picture, grid, noise, stars, strokes

ID = "savannah"
NAME = "Savannah"
DESCRIPTION = "Two giraffes and flat-topped acacias on the African plain, Kilimanjaro faint behind, under a low apricot sun by day and a big pale moon by night."
TAGS = ["landscape", "africa", "sunset", "wildlife"]

# The far edge of the plain, where the sun sits by day and the moon comes up by night.
HORIZON = 140
SUN_X, SUN_Y, SUN_R = MID + 62.0, 138.0, 20.0
MOON_X, MOON_Y, MOON_R = MID + 64.0, 141.0, 14.0

# The giraffes, a pixel to a letter, facing right; the last row is where the hooves stand.
GIRAFFE = [
    "..................#.#.......",
    "..................#.#.......",
    "................######......",
    ".................#######....",
    ".................########...",
    ".................####.......",
    "................###.........",
    "................###.........",
    "...............###..........",
    "...............###..........",
    "..............####..........",
    "..............###...........",
    ".............####...........",
    "............#####...........",
    "...........######...........",
    ".........########...........",
    ".......###########..........",
    "......############..........",
    "....##############..........",
    "...###############..........",
    "..################..........",
    ".#.###############..........",
    ".#.##############...........",
    ".#.#############............",
    ".#..###########.............",
    ".#..###.....###.............",
    ".#..#.#.....#.#.............",
    ".#..#.#.....#.#.............",
    "##..#.#.....#.#.............",
    "##..#.#.....#.#.............",
    "...#..#.....#.#.............",
    "...#..#....#..#.............",
    "...#..#....#..#.............",
    "...#...#...#..#.............",
    "...#...#...#...#............",
    "...#...#...#...#............",
    "...#...#...#...#............",
    "..##...##.##...##...........",
]
# The second, a little smaller, leaning its neck toward the first.
MATE = [
    "....................#.#.....",
    "....................#.#.....",
    "..................######....",
    "...................#######..",
    "...................########.",
    "..................####......",
    ".................###........",
    "................###.........",
    "...............####.........",
    "..............####..........",
    ".............####...........",
    "............#####...........",
    "..........########..........",
    "........##########..........",
    "......############..........",
    "....##############..........",
    "...###############..........",
    "..################..........",
    ".#.##############...........",
    ".#.#############............",
    ".#..###########.............",
    ".#..###.....###.............",
    ".#..#.#.....#.#.............",
    "##..#.#.....#.#.............",
    "##..#.#.....#.#.............",
    "....#.#.....#.#.............",
    "....#.#.....#.#.............",
    "....#.#.....#.#.............",
    "....#.#.....#.#.............",
    "....#.#.....#.#.............",
    "....#.#.....#.#.............",
    "....#.#.....#.#.............",
    "....#.#.....#.#.............",
    "...##.##...##.##............",
]

# An elephant and her calf, facing left, trunks down.
ELEPHANT = [
    "...####........",
    "..######.####..",
    ".#############.",
    "##############.",
    "##############.",
    "#.############.",
    "#..##.....###..",
    "#..##......##..",
    "#..##......##..",
    ".#.##......##..",
]
CALF = [
    "..##.....",
    ".######..",
    "########.",
    "#.######.",
    "#.##..##.",
    "..##..##.",
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


def sprite(mask: np.ndarray, rows, x: int, foot: int, flip=False):
    """Sets a pixel drawing into `mask` with its last row on `foot` and its left edge at x."""
    wide = max(len(r) for r in rows)
    art = np.array([[c == "#" for c in r.ljust(wide, ".")] for r in rows])
    if flip:
        art = art[:, ::-1]
    h, w = art.shape
    y0 = foot - h + 1
    mask[y0:y0 + h, x:x + w] |= art
    return mask


def line(mask: np.ndarray, x0: float, y0: float, x1: float, y1: float, width=1):
    """A straight stroke of whole pixels."""
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for t in np.linspace(0, 1, n * 2):
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        mask[int(round(y)), int(round(x)):int(round(x)) + width] = True


def acacia(mask: np.ndarray, cx: int, foot: int, half: int, top: int, thick=5, seed=0):
    """An umbrella thorn: a flat crown on a short trunk that forks into a vase of branches."""
    rng = np.random.default_rng(seed)
    if half < 8:
        # Far off: a flat crown two rows deep on a stick, forked just under it.
        mask[top, cx - half + 2:cx + half - 1] = True
        mask[top + 1, cx - half:cx + half + 1] = True
        mask[top + 2:foot + 1, cx] = True
        if foot - top > 4:
            mask[top + 2, cx - 1:cx + 2] = True
            mask[top + 2, cx] = False
        return mask
    shape = [0.55, 0.86, 1.0, 0.92, 0.66, 0.4][:thick] if thick < 6 else [0.55, 0.86, 1.0, 1.0, 0.9, 0.62]
    for j, f in enumerate(shape):
        reach = f * half
        left = int(round(cx - reach + rng.integers(-1, 2)))
        right = int(round(cx + reach + rng.integers(-1, 2)))
        mask[top + j, left:right] = True
    # Tufts on the crown and gaps in its underside.
    for _ in range(max(2, half // 3)):
        at = int(cx + rng.uniform(-0.5, 0.5) * half)
        mask[top - 1, at:at + int(rng.integers(1, 4))] = True
    under = top + thick - 1
    for _ in range(max(2, half // 4)):
        at = int(cx + rng.uniform(-0.6, 0.6) * half)
        mask[under, at:at + int(rng.integers(1, 3))] = False
    # The trunk and its branches.
    fork = int(round(under + (foot - under) * 0.55))
    line(mask, cx, foot, cx, fork, width=2)
    for k in (-0.62, -0.25, 0.2, 0.58):
        line(mask, cx + (0.5 if k > 0 else 0), fork, cx + k * half, under)
    return mask


def kilimanjaro():
    """Kibo's broad flat-topped dome with Mawenzi's jagged shoulder to its left: (tops, snow)."""
    x = np.arange(W) + 0.5
    cx, half, height = 170.0, 80.0, 26.0
    u = np.clip(np.abs(x - cx) / half - 0.12, 0, None) / 0.88
    rise = height / (1 + (u / 0.42) ** 2.6)
    peak = np.clip(1 - np.abs(x - (cx - 40)) / 8.0, 0, 1)
    mawenzi = 18.5 * peak ** 0.7 + 2.4 * (noise(W, 61, 4, 140.0) - 0.5) * (peak > 0.15)
    rise = np.maximum(rise, mawenzi)
    tops = np.where(rise > 0.6, np.round(HORIZON - rise), HORIZON).astype(int)
    snow = np.zeros((H, W), bool)
    depth = 6.0 * np.clip(1 - np.abs(x - cx) / (0.44 * half), 0, 1) ** 0.6
    depth = depth * (0.65 + 0.7 * noise(W, 62, 5, 120.0))
    for col in range(W):
        if depth[col] >= 1:
            snow[tops[col]:tops[col] + int(round(depth[col])), col] = True
    return tops, snow


def plain():
    """The far edge of the grass, with low scrub along it."""
    rng = np.random.default_rng(71)
    tops = np.full(W, HORIZON, dtype=int)
    at = int(rng.integers(0, 6))
    while at < W:
        n = int(rng.integers(2, 7))
        tall = 1 if n < 4 or rng.random() < 0.5 else 2
        tops[at:at + n] = HORIZON - 1
        if tall == 2:
            tops[at + 1:at + n - 1] = HORIZON - 2
        at += n + int(rng.integers(5, 20))
    return tops


def tufts(seed: int, count: int, rows=(SHORE + 4, H + 1)):
    """Dry grass in the foreground: little fans of blades, taller the nearer they are."""
    small = ["#.#.#", ".###."]
    large = ["..#..", "#.#.#", ".###."]
    rng = np.random.default_rng(seed)
    mask = np.zeros((H + 4, W + 8), bool)
    for _ in range(count):
        x, y = int(rng.integers(0, W)), int(rng.integers(*rows))
        near = (y - rows[0]) / (rows[1] - rows[0])
        sprite(mask, large if rng.random() < near else small, x, y)
    return mask[:H, :W]


def coat(mask: np.ndarray, seed: int, spacing=3.2) -> np.ndarray:
    """A giraffe's patches: its pixels cut into irregular cells, with a pale line one pixel wide between them."""
    rng = np.random.default_rng(seed)
    ys, xs = np.nonzero(mask)
    centres = np.array([
        (gy + rng.uniform(-1.0, 1.0), gx + rng.uniform(-1.0, 1.0))
        for gy in np.arange(ys.min() - 1, ys.max() + spacing, spacing)
        for gx in np.arange(xs.min() - 1, xs.max() + spacing, spacing)
    ])
    near = np.argmin((ys[:, None] - centres[None, :, 0]) ** 2 + (xs[:, None] - centres[None, :, 1]) ** 2, axis=1)
    cell = np.full(mask.shape, -1)
    cell[ys, xs] = near
    seam = np.zeros_like(mask)
    seam[:, :-1] |= (cell[:, :-1] != cell[:, 1:]) & mask[:, 1:]
    seam[:-1, :] |= (cell[:-1, :] != cell[1:, :]) & mask[1:, :]
    return mask & ~seam


def herd():
    """Everything that stands on the plain, as masks: far trees, the elephants, the giraffes and their patches, the near acacias."""
    far = np.zeros((H, W), bool)
    for cx, half, top, seed in ((78, 6, 136, 1), (124, 5, 137, 2), (209, 4, 138, 3), (392, 6, 136, 4), (458, 5, 137, 5)):
        acacia(far, cx, HORIZON, half, top, seed=seed)
    beasts = np.zeros((H, W), bool)
    sprite(beasts, ELEPHANT, 144, HORIZON + 1)
    sprite(beasts, CALF, 161, HORIZON + 1)
    giraffes = np.zeros((H, W), bool)
    patches = np.zeros((H, W), bool)
    yy, xx = np.mgrid[0:H, 0:W]
    for rows, x, foot, flip, (r0, r1), seed in ((GIRAFFE, 212, 149, False, (6, 24), 3), (MATE, 244, 147, True, (6, 20), 4)):
        one = sprite(np.zeros((H, W), bool), rows, x, foot, flip)
        top = foot - len(rows) + 1
        tail = x + (len(rows[0]) - 2 if flip else 1)
        body = one & (yy >= top + r0) & (yy <= top + r1) & (xx != tail)
        patches |= coat(body, seed)
        giraffes |= one
    near = np.zeros((H, W), bool)
    acacia(near, 340, 150, 24, 118, thick=6, seed=7)
    acacia(near, 424, 146, 11, 129, thick=4, seed=10)
    acacia(near, 486, 151, 20, 121, thick=5, seed=8)
    acacia(near, 30, 151, 18, 124, thick=5, seed=9)
    return far, beasts, giraffes, patches, near


def day() -> Picture:
    """Light windows: a big pale apricot sun on the horizon, peach haze, straw grass."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()

    # The glow: nothing in the upper part of the window, peach round the sun.
    rise = np.clip((y - 70) / (140 - 70), 0, 1) ** 1.8
    halo = np.exp(-(((x - SUN_X) / 100) ** 2) - ((y - SUN_Y) / 52) ** 2)
    drift = 0.88 + 0.24 * noise(W, 11, 3, 8.0)[None, :]
    p.tone(rise * (0.3 + 1.3 * halo) * drift, ["#fbe4d0", "#f8d0b2"], foot=HORIZON + 2)

    # The sun: a pale apricot disc sitting on the horizon, dotted thicker toward its foot.
    p.disc(SUN_X, SUN_Y, SUN_R, "#fcdcb6")
    p.disc(SUN_X, SUN_Y, SUN_R, p.level("#f7c08f", 4), rows=(int(SUN_Y - SUN_R), int(SUN_Y - 7)))
    p.disc(SUN_X, SUN_Y, SUN_R, p.level("#f7c08f", 8), rows=(int(SUN_Y - 7), int(SUN_Y + SUN_R) + 1))

    # Kilimanjaro faint in the haze, its snow a cool white.
    tops, snow = kilimanjaro()
    p.ridge(tops, "#e9d3cf", foot=HORIZON + 1)
    paint(p, snow, "#e6eaf2")

    far, beasts, giraffes, patches, near = herd()
    p.ridge(plain(), "#f0d9a9", foot=SHORE)
    paint(p, far, "#d3c39a")
    paint(p, beasts, "#c9b0a2")

    # The near grass: straw, with strokes warmer under the sun and a few tufts.
    p.rect(0, SHORE, W, H - SHORE, "#f5e6c6")
    rng = np.random.default_rng(5)
    under_sun = lambda col: math.exp(-(((col - SUN_X) / 50) ** 2))
    for r, colour in strokes(rng, under_sun, ["#ecd4a2", "#efc89c"], base=0.18, gain=0.2):
        p.dashes(r, colour)
    paint(p, tufts(41, 34), "#e8cd99")

    paint(p, giraffes, "#e8bf8c")
    paint(p, patches, "#d4a272")
    paint(p, near, "#aeb98c")
    return p


def night() -> Picture:
    """Dark windows: a big pale moon coming up on the horizon, violet sky, black giraffes and trees."""
    p = Picture("night", "#0b0c14")
    x, y = grid()

    # A few stars, dim and high; a violet band along the horizon, stronger round the moon.
    stars(p, 36, ("#28264c", "#6c66a6"), seed=23)

    band = np.clip((y - 86) / (140 - 86), 0, 1) ** 2.0
    lift = 1.5 + 1.1 * np.exp(-(((x - MOON_X) / 90) ** 2))
    drift = 0.9 + 0.2 * noise(W, 12, 3, 8.0)[None, :]
    p.tone(band * lift * drift, ["#191838", "#272056", "#3b2b6a"], foot=HORIZON + 2)

    # The moon: a clean pale disc, dimmed in dots as it nears the horizon haze.
    p.disc(MOON_X, MOON_Y, MOON_R, "#efe7d2")
    p.disc(MOON_X, MOON_Y, MOON_R, p.level("#d6cab0", 2), rows=(int(MOON_Y - 9), int(MOON_Y - 5)))
    p.disc(MOON_X, MOON_Y, MOON_R, p.level("#d6cab0", 6), rows=(int(MOON_Y - 5), int(MOON_Y + MOON_R) + 1))

    tops, snow = kilimanjaro()
    p.ridge(tops, "#15142b", foot=HORIZON + 1)
    paint(p, snow, "#2b2b4c")

    far, beasts, giraffes, patches, near = herd()
    p.ridge(plain(), "#0d0d1a", foot=SHORE)
    paint(p, far, "#06060c")
    paint(p, beasts, "#06060c")

    p.rect(0, SHORE, W, H - SHORE, "#09090f")
    rng = np.random.default_rng(7)
    glow = lambda col: math.exp(-(((col - MOON_X) / 60) ** 2))
    for r, colour in strokes(rng, glow, ["#14132a", "#1d1b3c"], base=0.12, gain=0.2):
        p.dashes(r, colour)
    paint(p, tufts(41, 34), "#121126")

    paint(p, giraffes, "#040408")
    paint(p, near, "#040408")
    return p
