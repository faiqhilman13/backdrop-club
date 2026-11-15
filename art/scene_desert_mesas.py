"""Desert mesas: a pale sun low behind table mountains by day, a crescent moon over black buttes by night."""

from __future__ import annotations

import math

import numpy as np

from dither import H, MID, SHORE, W, Picture, crescent, grid, noise, stars, strokes

ID = "desert-mesas"
NAME = "Desert mesas"

# Where the sun stands by day, and where its afterglow lingers by night.
SUN_X, SUN_Y, SUN_R = MID + 38.0, 129.0, 19.0

# Saguaros, drawn a pixel to a letter.
TALL = [
    "....#....",
    "...###...",
    "...###...",
    "...###...",
    "##.###...",
    "##.###...",
    "##.###.##",
    "######.##",
    ".#####.##",
    "...######",
    "...#####.",
    "...###...",
    "...###...",
    "...###...",
]
SHORT = [
    ".#.....",
    "###....",
    "###....",
    "###.##.",
    "###.##.",
    "######.",
    "#####..",
    "###....",
    "###....",
    "###....",
    "###....",
]
# (left column, row its foot stands on, shape)
CACTI = [(141, 148, TALL), (364, 147, SHORT), (36, 148, SHORT), (394, 148, TALL)]


def block(tops: np.ndarray, x0: int, x1: int, top: int):
    """Rock from row `top` down, over columns x0 to x1."""
    a, b = max(0, x0), min(W, x1)
    if b > a:
        tops[a:b] = np.minimum(tops[a:b], top)


def mesa(tops: np.ndarray, x0: int, x1: int, top: int, wall: int, left=(3, 2), right=(3, 2), foot: int = SHORE):
    """A table mountain: a flat cap over columns x0 to x1 at row `top`, sheer sides
    down to row `wall`, and from there an apron of scree going down to the foot
    in steps. A side's steps are (run, rise) each, the last one repeated."""
    block(tops, x0, x1, top)
    for side, steps in ((-1, left), (1, right)):
        steps = [steps] if isinstance(steps[0], int) else list(steps)
        edge, row, k = (x0 if side < 0 else x1), wall, 0
        while row < foot:
            run, rise = steps[min(k, len(steps) - 1)]
            block(tops, min(edge, edge + side * run), max(edge, edge + side * run), row)
            edge, row, k = edge + side * run, row + rise, k + 1


def land():
    """The same place in both pictures: mesas at three distances, as skylines."""
    far, mid, near = (np.full(W, SHORE, dtype=int) for _ in range(3))

    # Far: low tables on the horizon, with open desert between them.
    mesa(far, 4, 58, 134, 139)
    mesa(far, 92, 130, 134, 139)
    mesa(far, 200, 228, 132, 137)
    mesa(far, 268, 312, 134, 139)
    mesa(far, 378, 424, 132, 137)
    mesa(far, 448, 502, 134, 139)

    # Middle: the mesa the sun goes down behind, and a narrow butte with a needle beside it.
    mesa(mid, 301, 337, 123, 135)
    mesa(mid, 301, 351, 127, 135)
    mesa(mid, 242, 248, 115, 136, left=(2, 2), right=[(2, 2), (3, 2)])
    block(mid, 241, 249, 127)
    block(mid, 251, 254, 126)
    mesa(mid, 62, 102, 123, 135)
    mesa(mid, 426, 434, 117, 136, right=(2, 2))

    # Near: one tall butte, its cap a step higher on the left.
    mesa(near, 178, 192, 110, 130, left=[(2, 2), (3, 2), (3, 2), (3, 2), (3, 2), (3, 2), (4, 2)], right=[(2, 2), (2, 2), (3, 2), (3, 2), (3, 2), (3, 2), (4, 2)])
    block(near, 178, 187, 107)
    block(near, 177, 193, 121)
    mesa(near, -10, 14, 118, 134)
    mesa(near, 488, 522, 120, 134)
    return far, mid, near


def saguaros(p: Picture, fill: str):
    runs = []
    for x0, foot, shape in CACTI:
        for j, line in enumerate(shape):
            row = foot - len(shape) + j
            i = 0
            while i < len(line):
                if line[i] == "#":
                    n = len(line[i:]) - len(line[i:].lstrip("#"))
                    runs.append((x0 + i, row, n))
                    i += n
                else:
                    i += 1
    p.dashes(runs, fill)


def day() -> Picture:
    """Light windows: a big pale sun low behind a mesa, peach light, sand and clay."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()

    # The glow: nothing in the upper part of the window, strongest round the sun.
    rise = np.clip((y - 68) / (140 - 68), 0, 1) ** 1.9
    halo = np.exp(-(((x - SUN_X) / 96) ** 2) - ((y - SUN_Y) / 54) ** 2)
    drift = 0.88 + 0.24 * noise(W, 11, 3, 8.0)[None, :]
    p.tone(rise * (0.24 + 1.3 * halo) * drift, ["#fbe0cb", "#f7c29c"])

    # The sun: a pale disc, dotted thicker toward its foot.
    p.disc(SUN_X, SUN_Y, SUN_R, "#fbd7ab")
    p.disc(SUN_X, SUN_Y, SUN_R, p.level("#f6b583", 5), rows=(int(SUN_Y - SUN_R), int(SUN_Y - 6)))
    p.disc(SUN_X, SUN_Y, SUN_R, p.level("#f6b583", 9), rows=(int(SUN_Y - 6), int(SUN_Y + SUN_R) + 1))

    # Mesas at three distances: sand, terracotta, clay.
    far, mid, near = land()
    p.ridge(far, "#f3d8b8")
    p.ridge(mid, "#eeb08e")
    p.ridge(near, "#e1957e")

    # The desert floor: sand, with a few short strokes, warmer under the sun.
    p.rect(0, SHORE, W, H - SHORE, "#f6ead8")
    rng = np.random.default_rng(5)
    under_sun = lambda col: math.exp(-(((col - SUN_X) / 44) ** 2))
    for runs, colour in strokes(rng, under_sun, ["#ecd5b5", "#f0c4a2", "#eeb190"], base=0.15, gain=0.22):
        p.dashes(runs, colour)

    saguaros(p, "#7fb898")
    return p


def night() -> Picture:
    """Dark windows: a crescent moon, a violet afterglow along the horizon, black mesas."""
    p = Picture("night", "#0b0c14")
    x, y = grid()

    # A few stars, dim and high.
    stars(p, 44, ("#2c2b52", "#7d76b5"), seed=17)

    # The afterglow: a low band of violet, a little stronger where the sun went down.
    band = np.clip((y - 84) / (134 - 84), 0, 1) ** 2.2
    lift = 1.6 + 1.0 * np.exp(-(((x - SUN_X) / 110) ** 2))
    drift = 0.9 + 0.2 * noise(W, 12, 3, 8.0)[None, :]
    p.tone(band * lift * drift, ["#1b1a3f", "#2e2360", "#4e327a"])

    # The moon: small, low on the right.
    crescent(p, 367.0, 104.0, 5.0, "#e9dfc8")

    far, mid, near = land()
    p.ridge(far, "#14152b")
    p.ridge(mid, "#0e0f1e")
    p.ridge(near, "#07080d")

    # The desert floor: black, with a few faint strokes.
    p.rect(0, SHORE, W, H - SHORE, "#090a11")
    rng = np.random.default_rng(7)
    glow = lambda col: math.exp(-(((col - SUN_X) / 70) ** 2))
    for runs, colour in strokes(rng, glow, ["#15162c", "#1e1d40", "#2e2759"], base=0.12, gain=0.2):
        p.dashes(runs, colour)

    saguaros(p, "#040508")
    return p
