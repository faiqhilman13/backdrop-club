"""Island bay: a lemon sun low between limestone islands by day, a small full moon over the same bay by night."""

from __future__ import annotations

import numpy as np

from dither import H, MID, SHORE, W, Picture, grid, noise, stars, strokes

ID = "island-bay"
NAME = "Island bay"

# The islands, the same by day and by night: (x, height, reach left, reach right) for each dome.
# An island is one dome or a few run together; the three lists are three distances.
FAR = [(40, 12, 9, 8), (96, 10, 7, 8), (281, 13, 6, 6), (289, 9, 5, 6), (371, 11, 7, 8), (424, 12, 8, 8), (480, 10, 8, 7)]
MIDDLE = [(58, 24, 11, 10), (67, 15, 6, 7), (231, 27, 12, 12), (242, 17, 6, 6), (349, 22, 9, 9), (357, 14, 5, 6), (452, 25, 11, 12), (506, 19, 10, 10)]
NEAR = [(14, 30, 13, 12), (24, 20, 7, 8), (194, 31, 8, 8), (205, 42, 12, 14), (299, 13, 3, 3), (313, 25, 9, 8), (328, 33, 10, 11), (398, 30, 13, 12), (389, 19, 7, 7)]
# Where the sun and the moon stand: the gap between two islands.
GAP = MID + 4.0

# Two palms, drawn pixel by pixel: each leans out from its foot (the last row) and straightens toward its fronds.
PALM_TALL = [
    "......##...##....",
    "....##..#.#..##..",
    "...#...#####...#.",
    "..#..##.###.##..#",
    "..#.#....#....#.#",
    "....#....#....#..",
    ".........#.......",
    ".........#.......",
    "........#........",
    "........#........",
    ".......#.........",
    ".......#.........",
    "......#..........",
    ".....#...........",
    "....#............",
    "..##.............",
    "##...............",
]
PALM_SHORT = [
    ".....##...##...",
    "...##..#.#..##.",
    "..#...#####...#",
    "..#.##.##.##..#",
    "...#...#....#..",
    ".......#.......",
    ".......#.......",
    "......#........",
    ".....#.........",
    "....#..........",
    "..##...........",
    "##.............",
]


def karst(domes, seed: int, tufts: float = 1.0, foot: int = SHORE) -> np.ndarray:
    """Limestone islands as one skyline: the first row of rock in every column, `foot` where there is none.
    Each dome stands almost straight up out of the water and rounds over; clumps of trees roughen its crown."""
    rng = np.random.default_rng(seed)
    x = np.arange(W) + 0.5
    rise = np.zeros(W)
    crown = np.zeros(W)
    for at, height, left, right in domes:
        u = np.where(x < at, (at - x) / left, (x - at) / right)
        dome = np.clip(1 - u**3.0, 0, 1) ** 0.38
        crown = np.where(height * dome > rise, np.clip((dome - 0.5) / 0.3, 0, 1), crown)
        rise = np.maximum(rise, height * dome)
    clumps = np.zeros(W)
    at = float(rng.uniform(0, 4))
    while at < W:
        size, tall = float(rng.uniform(1.6, 3.0)), float(rng.uniform(0.7, 1.5))
        clumps = np.maximum(clumps, tall * np.clip(1 - ((x - at) / size) ** 2, 0, 1))
        at += float(rng.uniform(3.0, 7.0))
    rise = rise + tufts * crown * (clumps - 0.5)
    tops = np.where(rise > 0.5, np.round(foot - rise), foot).astype(int)
    # Nothing one pixel wide: a lone spike sinks to its taller neighbour, a lone notch fills.
    for i in range(1, W - 1):
        a, b, c = tops[i - 1], tops[i], tops[i + 1]
        if b < a and b < c:
            tops[i] = min(a, c)
        elif b > a and b > c:
            tops[i] = max(a, c)
    return tops


def stamp(picture: Picture, rows: list[str], x: int, foot: int, fill: str):
    """Draws a small pixel drawing with its last row on `foot` and its left edge at x."""
    runs = []
    for j, row in enumerate(rows):
        y = foot - (len(rows) - 1) + j
        i = 0
        while i < len(row):
            if row[i] == "#":
                n = 1
                while i + n < len(row) and row[i + n] == "#":
                    n += 1
                runs.append((x + i, y, n))
                i += n
            else:
                i += 1
    picture.dashes(runs, fill)


def spit() -> np.ndarray:
    """A low spit of sand running in from the left, where the palms stand."""
    tops = np.full(W, SHORE, dtype=int)
    for x in range(118, 182):
        tops[x] = SHORE - (3 if 126 <= x < 168 else 2 if 121 <= x < 176 else 1)
    return tops


def mirror(rng, tops: np.ndarray, squash: float = 4.0, foot: int = SHORE):
    """What stands above the water, lying on it: broken strokes under a skyline, the taller the rock the deeper they go."""
    runs = []
    for row in range(foot + 1, H):
        depth = row - foot
        col = int(rng.integers(0, 4))
        while col < W:
            n = int(rng.integers(2, 6))
            at = min(W - 1, col + n // 2)
            if foot - tops[at] > depth * squash and rng.random() < 0.8 - 0.07 * depth:
                runs.append((col, row, min(n, W - col)))
            col += n + int(rng.integers(1, 4))
    return runs


def glitter(rng, at: float, near: float, wide: float, skip: float = 0.3, foot: int = SHORE):
    """The path a low light lays on the water: short strokes under it, wandering wider as they come closer."""
    runs = []
    for row in range(foot + 1, H):
        depth = (row - foot) / (H - foot)
        if rng.random() < skip:
            continue
        n = int(rng.integers(2, 5 + int(3 * depth)))
        cx = at + float(rng.normal(0, near + (wide - near) * depth))
        runs.append((int(round(cx - n / 2)), row, n))
    return runs


def day() -> Picture:
    """Light windows: a pale sun low in the gap between the islands, mint light over the bay."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()
    sun_x, sun_y, sun_r = GAP, 133.0, 13.0

    # The glow: nothing in the upper part of the window, strongest round the sun.
    rise = np.clip((y - 70) / (142 - 70), 0, 1) ** 2.0
    halo = np.exp(-(((x - sun_x) / 90) ** 2) - ((y - sun_y) / 50) ** 2)
    drift = 0.88 + 0.24 * noise(W, 11, 3, 8.0)[None, :]
    p.tone(rise * (0.26 + 1.35 * halo) * drift, ["#d9f0e2", "#b0e0d8"], foot=SHORE + 2)

    # The sun: a lemon-white disc, dotted deeper toward its foot.
    p.disc(sun_x, sun_y, sun_r, "#fdf6c8")
    p.disc(sun_x, sun_y, sun_r, p.level("#f6e596", 4), rows=(int(sun_y - 5), int(sun_y + 4)))
    p.disc(sun_x, sun_y, sun_r, p.level("#f6e596", 8), rows=(int(sun_y + 4), int(sun_y + sun_r) + 1))

    # Islands at three distances, the nearest the deepest green; then the spit and its palms.
    far, middle, near, sand = karst(FAR, 51, 0.6), karst(MIDDLE, 52, 0.8), karst(NEAR, 53, 1.0), spit()
    p.ridge(far, "#c8dcc0")
    p.ridge(middle, "#9fcbb4")
    p.ridge(near, "#6dbaa5")
    p.ridge(sand, "#5fb39f")
    stamp(p, PALM_TALL, 139, SHORE - 3, "#5fb39f")
    stamp(p, PALM_SHORT, 155, SHORE - 3, "#5fb39f")

    # The water: the page again, with the islands and the sun lying on it in fine strokes.
    p.rect(0, SHORE, W, H - SHORE, "#ecf3ee")
    rng = np.random.default_rng(5)
    p.dashes(mirror(rng, far), "#c8dcc0")
    p.dashes(mirror(rng, middle), "#9fcbb4")
    p.dashes(mirror(rng, near), "#6dbaa5")
    p.dashes(mirror(rng, sand, 1.4), "#5fb39f")
    for runs, colour in strokes(rng, lambda col: 0.0, ["#bfe3d8"], base=0.16):
        p.dashes(runs, colour)
    p.dashes(glitter(rng, sun_x, 2.5, 7.0), "#efd87a")
    return p


def night() -> Picture:
    """Dark windows: the same bay under a small full moon, its light in a path across the water."""
    p = Picture("night", "#0b0c14")
    x, y = grid()
    rng = np.random.default_rng(9)
    moon_x, moon_y, moon_r = GAP, 121.0, 6.0

    # A few stars, dim and high.
    stars(p, 40, ("#1e3a48", "#5a9aa2"), seed=9)

    # The sky: teal coming up from the horizon, a faint halo where the moon stands.
    rise = np.clip((y - 76) / (146 - 76), 0, 1) ** 2.0
    halo = np.exp(-(((x - moon_x) / 34) ** 2)) * np.clip((y - 98) / (moon_y - 98), 0, 1) ** 1.4
    drift = 0.9 + 0.2 * noise(W, 12, 3, 8.0)[None, :]
    p.tone((1.7 * rise + 0.9 * halo) * drift, ["#0f1f2f", "#11323f", "#174a52"], foot=SHORE + 2)

    p.disc(moon_x, moon_y, moon_r, "#e6efd4")

    far, middle, near, sand = karst(FAR, 51, 0.6), karst(MIDDLE, 52, 0.8), karst(NEAR, 53, 1.0), spit()
    p.ridge(far, "#0d1822")
    p.ridge(middle, "#090f17")
    p.ridge(near, "#05070b")
    p.ridge(sand, "#030407")
    stamp(p, PALM_TALL, 139, SHORE - 3, "#030407")
    stamp(p, PALM_SHORT, 155, SHORE - 3, "#030407")

    # The water: black, the islands darker still on it, and the moon's path in pale strokes.
    p.rect(0, SHORE, W, H - SHORE, "#070a11")
    p.dashes(mirror(rng, near), "#030407")
    for runs, colour in strokes(rng, lambda col: 0.0, ["#12333e"], base=0.14):
        p.dashes(runs, colour)
    p.dashes(glitter(rng, moon_x, 3.5, 9.0, 0.2), "#3f7a78")
    p.dashes(glitter(rng, moon_x, 1.5, 5.0), "#cfe3cf")
    return p
