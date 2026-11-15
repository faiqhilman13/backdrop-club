"""Mountain lake: a pink dawn behind soft ranges by day, an aurora over black mountains by night."""

from __future__ import annotations

import math

import numpy as np

from dither import H, MID, SHORE, W, Picture, grid, noise, range_of, stars, strokes

ID = "mountain-lake"
NAME = "Mountain lake"


def day() -> Picture:
    """Light windows: a sun coming up behind soft ranges, its light on the water."""
    p = Picture("dawn", "#f5f2ea")
    x, y = grid()
    sun_x, sun_y, sun_r = MID + 52.0, 129.0, 18.0

    # The glow: nothing in the upper part of the window, strongest round the sun.
    rise = np.clip((y - 68) / (140 - 68), 0, 1) ** 1.9
    halo = np.exp(-(((x - sun_x) / 96) ** 2) - ((y - sun_y) / 54) ** 2)
    drift = 0.88 + 0.24 * noise(W, 11, 3, 8.0)[None, :]
    p.tone(rise * (0.24 + 1.3 * halo) * drift, ["#f9dbe0", "#f4b3c5"])

    # The sun: a pale disc, dotted thicker toward its foot.
    p.disc(sun_x, sun_y, sun_r, "#f8c9d3")
    p.disc(sun_x, sun_y, sun_r, p.level("#f29db6", 5), rows=(int(sun_y - sun_r), int(sun_y - 6)))
    p.disc(sun_x, sun_y, sun_r, p.level("#f29db6", 9), rows=(int(sun_y - 6), int(sun_y + sun_r) + 1))

    # Three ranges, the nearest the greenest.
    far = range_of(138, [(20, 12, 40), (74, 16, 44), (150, 13, 46), (206, 19, 40), (254, 11, 30), (342, 16, 44), (400, 10, 30), (452, 17, 42), (504, 12, 30)], 21)
    mid = range_of(142, [(40, 13, 30), (96, 9, 26), (136, 9, 26), (180, 14, 30), (232, 17, 30), (278, 9, 24), (360, 15, 34), (420, 11, 28), (478, 14, 30)], 22)
    near = range_of(146, [(24, 6, 24), (88, 8, 28), (158, 7, 30), (214, 5, 22), (260, 9, 30), (318, 6, 26), (372, 8, 24), (436, 6, 28), (492, 8, 24)], 23, rough=1.2)
    p.ridge(far, "#f7cbd5")
    p.ridge(mid, "#efa2b9")
    p.ridge(near, "#62b8a2")

    # The water: the page again, with the ranges and the sun lying on it in fine strokes.
    p.rect(0, SHORE, W, H - SHORE, "#f4ece8")
    rng = np.random.default_rng(5)
    under_sun = lambda col: math.exp(-(((col - sun_x) / 24) ** 2))
    for runs, colour in strokes(rng, under_sun, ["#f3bccb", "#7cc4b1", "#ee86a6"], base=0.22, gain=0.55):
        p.dashes(runs, colour)
    return p


def night() -> Picture:
    """Dark windows: curtains of light over black mountains, a few stars, a still lake."""
    p = Picture("night", "#0b0c14")
    x, y = grid()
    rng = np.random.default_rng(9)

    # A few stars, dim and high.
    stars(p, 50, ("#24474f", "#5fa9a4"), seed=9)

    # The curtains. Each column of the sky is a ray: how bright it is, and how high it reaches.
    curtain = sum(power * np.exp(-(((x[0] - at) / wide) ** 2)) for at, wide, power in [(22, 24, 0.65), (84, 32, 0.9), (158, 26, 0.7), (220, 34, 1.0), (278, 22, 0.75), (334, 36, 1.0), (398, 24, 0.7), (454, 32, 0.9), (502, 20, 0.6)])
    streak = noise(W, 31, 5, 44.0) ** 1.7
    ray = curtain * (0.42 + 0.85 * streak)
    reach = 120 - 50 * np.clip(ray, 0, 1.1) / 1.1 - 6 * noise(W, 32, 4, 24.0)
    fall = np.clip((y - reach[None, :]) / (140 - reach[None, :]), 0, 1) ** 1.5
    field = 4.6 * ray[None, :] * fall + 0.5 * np.clip((y - 84) / 56, 0, 1) ** 1.5
    # Kept quiet where the chat is: only close to the mountains may it burn bright.
    # The limit wanders from ray to ray, so no colour starts along a ruled line.
    yy = y + 12 * (noise(W, 33, 5, 60.0)[None, :] - 0.5)
    cap = 1.25 + 1.75 * np.clip((yy - 92) / (120 - 92), 0, 1) ** 1.4 + 1.0 * np.clip((yy - 120) / (132 - 120), 0, 1)
    field = np.minimum(field, cap)
    p.tone(field, ["#221a4a", "#1b4480", "#13767c", "#4fd2aa"])

    far = range_of(140, [(30, 14, 40), (96, 10, 30), (168, 12, 44), (240, 24, 46), (304, 10, 28), (364, 15, 40), (430, 20, 44), (494, 11, 30)], 41)
    near = range_of(146, [(48, 7, 30), (120, 9, 30), (198, 6, 24), (278, 9, 34), (340, 7, 30), (410, 8, 28), (474, 6, 26)], 42, rough=1.2)
    p.ridge(far, "#10121f")
    p.ridge(near, "#06070c")

    # The lake: black, with the light lying on it in broken strokes.
    p.rect(0, SHORE, W, H - SHORE, "#08090f")
    above = field[SHORE - 16]
    for runs, colour in strokes(rng, lambda col: min(1.0, above[col] / 3.4), ["#1b3a6b", "#14666e", "#3aa98d"], base=0.1, gain=0.6):
        p.dashes(runs, colour)
    return p


