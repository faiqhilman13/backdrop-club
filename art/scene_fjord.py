"""Fjord: misty blue-green walls dropping into still water toward snowy peaks by day, the same fjord under a low moon by night."""

from __future__ import annotations

import numpy as np

from dither import H, PLACE, SHORE, TILE, W, Picture, grid, noise, stars, strokes

ID = "fjord"
NAME = "Fjord"
DESCRIPTION = "A Norwegian fjord: steep walls dropping into still water toward snowy peaks, a red cabin on stilts at the shore, misty by day and moonlit by night."
TAGS = ["landscape", "norway", "fjord", "mountains"]

# The walls, the same by day and by night, nearest first on each side:
# (root, toe, height at the root, height at the shoulder, seed). A wall stands high at its root,
# falls a little toward the far end of the fjord and then drops sheer into the water at its toe.
LEFT = [(-40, 116, 80, 64, 61), (30, 172, 48, 38, 62), (130, 210, 31, 25, 63)]
RIGHT = [(552, 398, 80, 64, 71), (470, 336, 48, 38, 72), (382, 302, 31, 25, 73)]
# The snowy massif at the far end, as its skyline's corners: (x, height) each, summits and saddles in turn.
MASSIF = [(194, 0), (205, 14), (214, 10), (226, 28), (236, 19), (244, 24), (253, 17), (266, 33), (277, 22), (290, 39), (301, 24), (311, 28), (320, 16), (327, 18), (338, 0)]
# Waterfalls over the lip of the second wall on the right, side by side: (x, rows below the lip it starts).
FALLS = [(361, 2), (366, 3)]

# The moon rises behind the shoulder of the right wall, clear of the chat, so its path lies beside the message box.
MOON_X, MOON_Y, MOON_R = 346.0, 112.0, 5.5
CABIN_X = 148  # the cabin's left column, on the shelf at the foot of the left wall
BOAT_X = 252  # a small boat out on the water

# The cabin, a pixel to a letter: R red wall, T white trim, O window, D door, P platform, S stilts.
# A rorbu: its gable to the water, white barge boards, a window up in the gable.
CABIN = [
    ".....TTT.....",
    "....TRRRT....",
    "...TRRRRRT...",
    "..TRRROORRT..",
    ".TRRRROORRRT.",
    "TTRRRRRRRRRTT",
    ".RRRRRRRRRRR.",
    ".ROORRRRRDDR.",
    ".ROORRRRRDDR.",
    ".RRRRRRRRDDR.",
    "PPPPPPPPPPPPP",
    ".S..S...S..S.",
    ".S..S...S..S.",
]
BOAT = [
    "...C.....",
    "...CC....",
    "HHHHHHHHH",
    ".HHHHHHH.",
]


def smooth(tops: np.ndarray) -> np.ndarray:
    """Nothing one pixel wide: a lone spike sinks to its taller neighbour, a lone notch fills."""
    tops = tops.copy()
    for i in range(1, W - 1):
        a, b, c = tops[i - 1], tops[i], tops[i + 1]
        if b < a and b < c:
            tops[i] = min(a, c)
        elif b > a and b > c:
            tops[i] = max(a, c)
    return tops


def wall(root: float, toe: float, high: float, edge: float, seed: int, foot: int = SHORE) -> np.ndarray:
    """One wall as a skyline: the first row of rock in every column, `foot` where there is none."""
    x = np.arange(W) + 0.5
    u = (x - root) / (toe - root)
    lean = high + (edge - high) * u
    shoulder = np.clip(1 - np.clip(u, 0, 1) ** 16, 0, 1) ** 0.42
    rise = np.where(u <= 1, lean * shoulder, 0.0)
    # A rugged lip: broad swells and small crags, fading out down the sheer face.
    crag = 3.4 * (noise(W, seed, 3, 9.0) - 0.5) + 1.4 * (noise(W, seed + 100, 5, 40.0) - 0.5)
    rise = np.minimum(rise + 2 * crag * np.clip(rise / 12, 0, 1) * shoulder**4, 80)
    return smooth(np.where(rise > 0.5, np.round(foot - rise), foot).astype(int))


def walls():
    """Both sides, nearest first: each layer is one skyline holding the left and the right wall."""
    return [np.minimum(wall(*a), wall(*b)) for a, b in zip(LEFT, RIGHT)]


def summits(seed: int, foot: int = SHORE):
    """The massif at the far end: its skyline, the foot of the shade in each column, and the foot of the snow.

    The light comes from the left, so each summit's right flank is in shade: a facet under the skyline, between
    a ridge line running down from the summit and the next summit's sunlit flank carried on down past the saddle."""
    x = np.arange(W) + 0.5
    rise = np.interp(x, [c[0] for c in MASSIF], [c[1] for c in MASSIF])
    rise += 1.3 * (noise(W, seed, 5, 60.0) - 0.5) * 2 * np.clip(rise / 12, 0, 1)
    tops = smooth(np.where(rise > 0.5, np.round(foot - rise), foot).astype(int))
    shade = tops.copy()
    for i, ((xa, ha), (xs, hs)) in enumerate(zip(MASSIF, MASSIF[1:])):
        if ha <= hs:
            continue
        cols = np.arange(xa, xs)
        ridge = foot - ha + (cols + 0.5 - xa) / 0.45
        if i + 2 < len(MASSIF) and MASSIF[i + 2][1] > hs:
            xb, hb = MASSIF[i + 2]
            ridge = np.minimum(ridge, foot - hs + (xs - cols - 0.5) * (hb - hs) / (xb - xs))
        shade[cols] = np.clip(np.round(ridge), tops[cols], foot)
    # Snow down to a ragged line: a tooth of it reaching down every gully.
    rng = np.random.default_rng(seed)
    line = 121 + 2 * noise(W, seed + 1, 4, 30.0)
    at = float(rng.uniform(0, 4))
    while at < W:
        deep, half = float(rng.uniform(2, 8)), float(rng.uniform(1.5, 3.2))
        line = np.maximum(line, 121 + deep * np.clip(1 - np.abs(x - at) / half, 0, 1))
        at += float(rng.uniform(4, 8))
    snow = smooth(np.minimum(np.maximum(tops, np.round(line).astype(int)), tops + 16))
    return tops, shade, snow


def lip(tops: np.ndarray) -> np.ndarray:
    """The top pixel of every column where a wall runs level enough to catch light along its lip."""
    left = np.concatenate(([tops[0]], tops[:-1]))
    right = np.concatenate((tops[1:], [tops[-1]]))
    level = (np.abs(right - left) <= 2) & (tops < SHORE - 3)
    return np.where(level, tops + 1, tops)


def span(p: Picture, top, bottom, fill: str, x0: int = 0, x1: int = W):
    """Fills every column x0..x1 from row top[x] down to row bottom[x], as one path."""
    top = np.asarray(top, int)
    bottom = np.maximum(np.asarray(bottom, int), top)
    d = f"M{x0} {top[x0]}"
    for x in range(x0, x1):
        if x + 1 == x1 or top[x + 1] != top[x]:
            d += f"H{x + 1}"
            if x + 1 < x1:
                d += f"V{top[x + 1]}"
    d += f"V{bottom[x1 - 1]}"
    for x in range(x1 - 1, x0 - 1, -1):
        if x == x0 or bottom[x - 1] != bottom[x]:
            d += f"H{x}"
            if x > x0:
                d += f"V{bottom[x - 1]}"
    p.body.append(f'<path fill="{fill}" d="{d}z"/>')


def mist(p: Picture, field: np.ndarray, colour: str):
    """Dithers a band of tone (0 to 1) in one colour. Unlike Picture.tone the band may thin out again
    below: each threshold fills, in every tile column, the rows from the first tile it inks to the last."""
    name = f"{p.name[0]}{p.inks}"
    p.inks += 1
    rows = H // TILE
    for t in range(TILE * TILE):
        ox, oy = PLACE[t]
        on = field > (t + 0.5) / (TILE * TILE)
        top, bottom = np.zeros(W, int), np.zeros(W, int)
        for i in range(W // TILE):
            hit = np.flatnonzero(on[oy::TILE, i * TILE + ox][:rows])
            if hit.size:
                top[i * TILE : (i + 1) * TILE] = hit[0] * TILE
                bottom[i * TILE : (i + 1) * TILE] = (hit[-1] + 1) * TILE
        live = np.flatnonzero(bottom > top)
        if not live.size:
            continue
        p.defs.append(
            f'<pattern id="{name}{t:x}" x="{ox - 1.5}" y="{oy - 1.5}" width="{TILE}" height="{TILE}" patternUnits="userSpaceOnUse">'
            f'<rect x="1.48" y="1.48" width="1.04" height="1.04" fill="{colour}"/></pattern>'
        )
        span(p, top, bottom, f"url(#{name}{t:x})", int(live[0]), int(live[-1]) + 1)


def mist_band(seed: int, strength: float, x0: float = 150, x1: float = 362) -> np.ndarray:
    """Mist lying on the water: thickest a row or two above it, thinning upward over the feet of the walls
    and down over the water, drifting thicker and thinner along the fjord."""
    x, y = grid()
    above = np.clip(1 - (SHORE - 1.5 - y) / 7.0, 0, 1) ** 1.6
    below = np.clip(1 - (y - SHORE + 1.5) / 4.0, 0, 1)
    across = np.where(y < SHORE - 1.5, above, below)
    along = 0.45 + 0.75 * noise(W, seed, 3, 12.0)[None, :]
    fade = np.clip((x - x0) / 24, 0, 1) * np.clip((x1 - x) / 24, 0, 1)
    return strength * across * along * fade


def cracks(rng, tops: np.ndarray, every=(5, 10), foot: int = SHORE):
    """Dark seams down a rock face, starting at its lip: (x, top, bottom) each, broken once or twice."""
    out = []
    x = int(rng.integers(0, every[1]))
    while x < W:
        top = int(tops[x])
        if top < foot - 8:
            y = top + int(rng.integers(2, 4))
            end = top + int((foot - top) * rng.uniform(0.35, 0.8))
            while y < end:
                n = int(rng.integers(4, 12))
                out.append((x, y, min(y + n, end)))
                y += n + int(rng.integers(2, 5))
        x += int(rng.integers(*every))
    return out


def seams(p: Picture, runs, fill: str):
    """Draws the seams from `cracks`, one pixel wide."""
    d = "".join(f"M{x} {a}h1v{b - a}h-1z" for x, a, b in runs if b > a)
    if d:
        p.body.append(f'<path fill="{fill}" d="{d}"/>')


def waterfall(x: int, top: int, foot: int = SHORE):
    """A thread of water from a wall's lip to the fjord: (x, y, n) runs. It comes over the lip thin and broken,
    steps aside a pixel at a ledge partway down, widens below it and sprays out at its foot."""
    ledge = top + (foot - top) * 2 // 5
    runs = [(x, top, 1), (x, top + 2, 1)]
    runs += [(x, y, 1) for y in range(top + 4, ledge)]
    runs += [(x + 1, y, 1 if y < ledge + 6 else 2) for y in range(ledge, foot - 3)]
    runs += [(x, foot - 3, 3), (x - 1, foot - 2, 2), (x + 2, foot - 2, 2), (x - 2, foot - 1, 1), (x + 1, foot - 1, 1), (x + 4, foot - 1, 1)]
    return runs


def sprite(p: Picture, rows: list[str], x: int, foot: int, palette: dict[str, str]):
    """Draws a small pixel drawing with its last row on `foot` and its left edge at x, one path per colour."""
    runs = {k: [] for k in palette}
    for j, row in enumerate(rows):
        y = foot - (len(rows) - 1) + j
        i = 0
        while i < len(row):
            k = row[i]
            n = 1
            while i + n < len(row) and row[i + n] == k:
                n += 1
            if k in runs:
                runs[k].append((x + i, y, n))
            i += n
    for k, colour in palette.items():
        p.dashes(runs[k], colour)


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


def shelf() -> np.ndarray:
    """The low rock the cabin stands on, at the foot of the left wall."""
    tops = np.full(W, SHORE, dtype=int)
    for x in range(138, 166):
        tops[x] = SHORE - (1 if x < 141 else 2 if x < 146 else 3 if x < 150 else 2 if x < 160 else 1)
    return tops


def day() -> Picture:
    """Light windows: pale misty walls, snow on the far peaks, mist on the still water."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()
    rng = np.random.default_rng(5)

    # The haze: nothing in the upper part of the window, thicker toward the far end of the fjord.
    rise = np.clip((y - 74) / (140 - 74), 0, 1) ** 1.8
    far_end = np.exp(-(((x - 262) / 80) ** 2))
    drift = 0.9 + 0.2 * noise(W, 11, 3, 8.0)[None, :]
    p.tone(rise * (0.3 + 1.05 * far_end) * drift, ["#e8f0ed", "#d7e7e5"])

    # The peaks at the far end: rock, then snow, each a shade deeper right of its ridge line.
    tops, shade, snow = summits(81)
    p.ridge(tops, "#bed2d9")
    span(p, tops, shade, "#adc4ce")
    span(p, tops, snow, "#fdfdfb")
    span(p, tops, np.minimum(shade, snow), "#dde8ee")
    mist(p, 0.9 * np.clip((y - 130) / 16, 0, 1) ** 1.3 * (tops < SHORE)[None, :], "#d8e6e7")

    # The walls, far to near: each paler than the one in front, a light lip, dark seams down its face.
    layers = walls()
    for k, body, top, seam in [(2, "#c3ddd7", "#d3e6e1", "#b4d4cd"), (1, "#a2cbc2", "#b5d6ce", "#93c1b8")]:
        p.ridge(layers[k], body)
        span(p, layers[k], lip(layers[k]), top)
        seams(p, cracks(rng, layers[k]), seam)
    for fx, drop in FALLS:
        p.dashes(waterfall(fx, int(layers[1][fx]) + drop), "#fbfdfc")

    # The water: the page again, with the walls lying on it in fine strokes.
    p.rect(0, SHORE, W, H - SHORE, "#edf3f1")
    p.dashes(mirror(rng, tops, 2.6), "#d3e2e7")
    p.dashes(mirror(rng, layers[2], 2.4), "#c3ddd7")
    p.dashes(mirror(rng, layers[1], 3.4), "#a9cfc6")
    p.dashes(mirror(rng, layers[0], 5.0), "#8ec2b7")
    for runs, colour in strokes(rng, lambda col: 0.0, ["#dce9e7"], base=0.12):
        p.dashes(runs, colour)

    # Mist on the water, over the feet of the far walls.
    mist(p, mist_band(14, 0.8), "#f8fbfa")

    # The near walls, crisp in front of the mist; the shelf, the cabin and the boat.
    p.ridge(layers[0], "#86bcb1")
    span(p, layers[0], lip(layers[0]), "#98c8bd")
    seams(p, cracks(rng, layers[0], (4, 8)), "#7cb5aa")
    p.ridge(shelf(), "#86bcb1")
    sprite(p, CABIN, CABIN_X, SHORE + 1, {"R": "#ef9188", "T": "#fdfbf6", "O": "#fdfbf6", "D": "#f6d7cf", "P": "#c6a690", "S": "#c6a690"})
    sprite(p, BOAT, BOAT_X, SHORE + 5, {"H": "#ef9188", "C": "#fdfbf6"})
    return p


def night() -> Picture:
    """Dark windows: a low moon half risen behind the right wall, its light broken on the water, the snow
    on the far peaks pale where it faces the moon, the cabin's window lit."""
    p = Picture("night", "#0b0c14")
    x, y = grid()
    rng = np.random.default_rng(9)

    stars(p, 30, ("#252a40", "#69739a"), seed=19)

    # The sky: a faint blue coming up from the far end, a little brighter round the moon.
    rise = np.clip((y - 82) / (142 - 82), 0, 1) ** 1.8
    halo = np.exp(-(((x - MOON_X) / 44) ** 2) - ((y - MOON_Y) / 20) ** 2)
    drift = 0.9 + 0.2 * noise(W, 12, 3, 8.0)[None, :]
    p.tone((1.1 * rise + 1.5 * halo * np.clip((y - 86) / 18, 0, 1)) * drift, ["#0f1424", "#141b30", "#19233d"])

    p.disc(MOON_X, MOON_Y, MOON_R, "#e8ead8")

    # The far peaks: dark rock, the snow pale where it faces the moon.
    tops, shade, snow = summits(81)
    p.ridge(tops, "#131929")
    span(p, tops, snow, "#28324a")
    # Left of the moon the snow it lights is right of each ridge line; right of the moon, left of it.
    west = np.arange(W) + 0.5 < MOON_X
    lit = np.where(west, tops, shade)
    span(p, lit, np.maximum(lit, np.where(west, np.minimum(shade, snow), snow)), "#43516e")

    # The walls, far to near, black against the sky, the moon catching their lips.
    layers = walls()
    for k, body, rim in [(2, "#0f1422", "#232d44"), (1, "#0b0f19", "#1b2337")]:
        p.ridge(layers[k], body)
        span(p, layers[k], lip(layers[k]), rim)
    for fx, drop in FALLS:
        p.dashes(waterfall(fx, int(layers[1][fx]) + drop), "#1c2538")

    # The water: black, faint moonlight on it all the way along, and the moon's path across it in pale strokes.
    p.rect(0, SHORE, W, H - SHORE, "#080a11")
    moonlit = lambda col: float(np.exp(-(((col - MOON_X) / 120) ** 2)))
    for runs, colour in strokes(rng, moonlit, ["#10172a", "#182139", "#212c49"], base=0.12, gain=0.4):
        p.dashes(runs, colour)
    p.dashes(glitter(rng, MOON_X, 3.5, 10.0, 0.15), "#33405c")
    p.dashes(glitter(rng, MOON_X, 1.5, 5.0), "#cfd5c6")

    mist(p, mist_band(14, 0.6), "#161e31")

    p.ridge(layers[0], "#06070c")
    span(p, layers[0], lip(layers[0]), "#141a29")
    p.ridge(shelf(), "#06070c")
    sprite(p, CABIN, CABIN_X, SHORE + 1, {"R": "#2a1418", "T": "#3b3437", "O": "#f2b65e", "D": "#1a0c0f", "P": "#120d0f", "S": "#120d0f"})
    # The lit window lying on the water.
    p.dashes([(CABIN_X + 2, SHORE + 3, 2), (CABIN_X + 1, SHORE + 5, 3), (CABIN_X + 2, SHORE + 8, 2)], "#7a5228")
    sprite(p, BOAT, BOAT_X, SHORE + 5, {"H": "#04050a", "C": "#04050a"})
    return p
