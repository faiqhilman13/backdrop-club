"""Snowy pines: soft sage pines round a snowy clearing by day, black-green pines on deep blue snow by night, a cabin's window lit in both."""

from __future__ import annotations

import numpy as np

from dither import BAYER, H, SHORE, TILE, W, Picture, grid, noise, stars, strokes

ID = "snowy-pines"
NAME = "Snowy pines"
DESCRIPTION = "A winter forest: layers of snowy pines round a clearing, a small cabin with a lit window and a thread of smoke, a frozen lake at its foot."
TAGS = ["landscape", "winter", "forest", "snow"]

# The pines, the same by day and by night: (x, foot, height, half width) each, drawn in this order.
# The middle row stands behind the clearing; the near row frames it, tallest at the window's edges.
MIDDLE = [
    (8, 143, 30, 9), (30, 143, 34, 10), (47, 143, 24, 7), (70, 143, 32, 9), (100, 143, 28, 8), (118, 143, 22, 7),
    (138, 143, 26, 8), (149, 143, 20, 6), (190, 143, 30, 9), (213, 143, 24, 7), (201, 143, 36, 10), (240, 143, 22, 7),
    (252, 143, 29, 8), (264, 143, 18, 6), (283, 143, 21, 6), (307, 143, 25, 8), (296, 143, 33, 9), (318, 143, 19, 6),
    (362, 143, 34, 10), (374, 143, 24, 7), (391, 143, 30, 9), (409, 143, 26, 8), (428, 143, 34, 10), (447, 143, 22, 7),
    (466, 143, 32, 9), (486, 143, 26, 8), (504, 143, 36, 10),
]
NEAR = [
    (122, 147, 44, 12), (90, 148, 58, 16), (54, 150, 72, 19), (16, 151, 82, 21), (156, 147, 30, 8), (171, 146, 18, 6),
    (404, 147, 44, 12), (434, 148, 60, 16), (466, 150, 74, 19), (500, 151, 82, 21), (380, 147, 26, 7),
]
# The cabin stands in the clearing to the right of the chat, where the message box leaves it in view.
CABIN_X, CABIN_FOOT = 328, 145

# The cabin, a pixel to a letter: S snow on the roof, E eaves, L and l logs, W window, F its frame, D door, K chimney.
CABIN = [
    "................KK......",
    ".......SSSSSSSSSKKSS....",
    "......SSSSSSSSSSSSSSS...",
    ".....SSSSSSSSSSSSSSSSS..",
    "....SSSSSSSSSSSSSSSSSSS.",
    "...SSSSSSSSSSSSSSSSSSSSS",
    "...EEEEEEEEEEEEEEEEEEEEE",
    "....LLLLLLLLLLLLLLLLLLL.",
    "....lllWFWlllllllllllll.",
    "....LLLFFFLLLLLLLLLDDLL.",
    "....lllWFWlllllllllDDll.",
    "....LLLLLLLLLLLLLLLDDLL.",
    "....lllllllllllllllDDll.",
    "....LLLLLLLLLLLLLLLDDLL.",
]

BODY, SNOW, DUST, TRUNK = 1, 2, 3, 4


def pine(canvas: np.ndarray, cx: int, foot: int, height: int, half: float, seed: int):
    """Paints one pine into `canvas`: tiers of boughs from its tip down, each a little wider than the one above,
    and a stub of trunk. Snow lies along the top of every tier and thickly on its upper edges, thinning toward
    the bough tips, with a dusting just inside it."""
    rng = np.random.default_rng(seed)
    trunk = max(1, height // 10)
    rows = height - trunk
    tiers = int(np.clip(round(rows / 6.5), 2, 7))
    weights = np.array([1.0 + 0.28 * k for k in range(tiers)])
    lengths = np.maximum(2, np.round(rows * weights / weights.sum()).astype(int))
    lengths[-1] += rows - lengths.sum()
    y, done, wide = foot - height, 0, 0.0
    for k, n in enumerate(lengths):
        done += n
        bottom = half * (done / rows) ** 0.92
        top = 0.0 if k == 0 else wide * 0.45
        # The tips of a tier reach a little further on one side or the other.
        reach = rng.integers(0, 2, size=2) if bottom >= 5 else (0, 0)
        for j in range(n):
            f = j / max(1, n - 1)
            hw = top + (bottom - top) * f
            left, right = int(round(hw + reach[0] * f)), int(round(hw + reach[1] * f))
            rim = 2 if f < 0.45 else 1 if f < 0.8 else 0
            for dx in range(-left, right + 1):
                edge = (left if dx < 0 else right) - abs(dx)
                code = SNOW if j == 0 or edge < rim else DUST if edge == rim and f < 0.7 else BODY
                if 0 <= cx + dx < W:
                    canvas[y, cx + dx] = code
            y += 1
        # The bough tips droop a pixel below the tier's last row.
        if bottom >= 4 and y < foot:
            for tip in (cx - int(round(bottom)) - reach[0], cx + int(round(bottom)) + reach[1]):
                if 0 <= tip < W:
                    canvas[y, tip] = BODY
        wide = bottom
    stem = 1 if half >= 12 else 0
    canvas[y:foot, max(0, cx - stem) : cx + stem + 1] = TRUNK


def grove(trees) -> np.ndarray:
    """A row of pines painted in order, later ones in front: which part of a tree, if any, is at every pixel."""
    canvas = np.zeros((H, W), dtype=np.int8)
    for i, (cx, foot, height, half) in enumerate(trees):
        pine(canvas, cx, foot, height, half, seed=cx * 7 + i)
    return canvas


def paint(p: Picture, mask: np.ndarray, fill: str):
    """Any shape of whole pixels, as one path: each run of pixels a box as tall as it stays the same."""
    open_boxes: dict[tuple[int, int], int] = {}
    d = ""
    for row in range(H + 1):
        runs = set()
        if row < H and mask[row].any():
            edge = np.flatnonzero(np.diff(np.concatenate(([0], mask[row].astype(np.int8), [0]))))
            runs = {(int(a), int(b - a)) for a, b in zip(edge[::2], edge[1::2])}
        for run in [r for r in open_boxes if r not in runs]:
            top = open_boxes.pop(run)
            d += f"M{run[0]} {top}h{run[1]}v{row - top}h-{run[1]}z"
        for run in runs:
            open_boxes.setdefault(run, row)
    if d:
        p.body.append(f'<path fill="{fill}" d="{d}"/>')


def lines(p: Picture, mask: np.ndarray, colour: str):
    """Any shape of whole pixels as one path of strokes a pixel tall, a row at a time: the shortest way to
    write a shape whose rows all differ, like the tiers of a pine."""
    d = []
    for y in np.flatnonzero(mask.any(axis=1)):
        edge = np.flatnonzero(np.diff(np.concatenate(([0], mask[y].astype(np.int8), [0]))))
        end = None
        for a, b in zip(edge[::2], edge[1::2]):
            d.append(f"M{a} {y}.5h{b - a}" if end is None else f"m{a - end} 0h{b - a}")
            end = b
    if d:
        p.body.append(f'<path fill="none" stroke="{colour}" d="{"".join(d)}"/>')


def trees(p: Picture, canvas: np.ndarray, body: str, snow: str, trunk: str):
    """Draws a grove: boughs, then the dusting of snow as a dither over them, then the snow lying solid."""
    lines(p, (canvas == BODY) | (canvas == DUST), body)
    lines(p, canvas == DUST, p.level(snow, 8))
    lines(p, canvas == SNOW, snow)
    paint(p, canvas == TRUNK, trunk)


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


def hills(seed: int) -> np.ndarray:
    """Low snowy hills far off: the first row of snow in every column."""
    rise = 9 + 6 * noise(W, seed, 3, 4.0) + 2 * noise(W, seed + 1, 4, 14.0)
    return smooth(np.round(136 - rise).astype(int))


def far_forest(seed: int, ground: np.ndarray) -> np.ndarray:
    """A band of small pines along the far hills, packed close: one skyline of little teeth."""
    rng = np.random.default_rng(seed)
    x = np.arange(W) + 0.5
    rise = np.zeros(W)
    at = float(rng.uniform(0, 3))
    while at < W:
        tall, half = float(rng.uniform(4, 9)), float(rng.uniform(1.8, 3.2))
        rise = np.maximum(rise, tall * np.clip(1 - np.abs(x - at) / half, 0, 1))
        at += float(rng.uniform(2.5, 5.0))
    return np.minimum(ground + 3, np.round(ground + 3 - rise).astype(int))


def bank(seed: int) -> np.ndarray:
    """The snow of the clearing, along the lake's far shore: the first row of snow in every column."""
    x = np.arange(W) + 0.5
    rise = 4.5 + 1.5 * noise(W, seed, 3, 6.0) + 2.0 * np.exp(-(((x - 340) / 40) ** 2))
    return smooth(np.round(SHORE - rise).astype(int))


def drifts(rng, ground: np.ndarray):
    """Soft shadows in the snow of the clearing: a few long low strokes under its edge."""
    runs = []
    for row in range(int(ground.min()) + 1, SHORE):
        col = int(rng.integers(0, 12))
        while col < W:
            n = int(rng.integers(4, 14))
            if row > ground[min(W - 1, col)] and rng.random() < 0.35:
                runs.append((col, row, min(n, W - col)))
            col += n + int(rng.integers(6, 22))
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


def smoke(p: Picture, colour: str):
    """A thin plume of smoke from the chimney, leaning toward the middle and wavering a little as it climbs,
    dithered thinner and thinner until it is gone."""
    x, y = grid()
    x0, y0 = CABIN_X + 17, CABIN_FOOT - len(CABIN)
    field = np.zeros((H, W))
    for k in range(32):
        at = x0 - 0.35 * k + 1.3 * np.sin(k / 4.5)
        wide = 1.0 + 0.08 * k
        puff = (1.3 - k / 28) * np.exp(-(((x - at) / wide) ** 2) - ((y - (y0 - k)) / 1.2) ** 2)
        field = np.maximum(field, puff)
    # Ordered dither: a pixel is inked where the plume beats its place's threshold in the tile.
    threshold = (np.array(BAYER) + 0.5) / (TILE * TILE)
    paint(p, field > np.tile(threshold, (H // TILE, W // TILE)), colour)


def mirror(rng, tops: np.ndarray, squash: float = 4.0, foot: int = SHORE):
    """What stands above the ice, lying faintly on it: broken strokes under a skyline."""
    runs = []
    for row in range(foot + 1, H):
        depth = row - foot
        col = int(rng.integers(0, 4))
        while col < W:
            n = int(rng.integers(2, 6))
            at = min(W - 1, col + n // 2)
            if foot - tops[at] > depth * squash and rng.random() < 0.7 - 0.07 * depth:
                runs.append((col, row, min(n, W - col)))
            col += n + int(rng.integers(1, 4))
    return runs


def skyline(canvas: np.ndarray) -> np.ndarray:
    """The first painted row in every column of a grove, SHORE where there is none."""
    on = canvas > 0
    return np.where(on.any(axis=0), on.argmax(axis=0), SHORE)


def day() -> Picture:
    """Light windows: pale blue snow, soft sage pines, the cabin's window warm, smoke going up."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()
    rng = np.random.default_rng(5)

    # The sky: a cold pale blue coming up from behind the trees.
    rise = np.clip((y - 76) / (138 - 76), 0, 1) ** 1.7
    drift = 0.9 + 0.2 * noise(W, 11, 3, 8.0)[None, :]
    p.tone(rise * 1.4 * drift, ["#e9f0f2", "#dbe8ee"])

    far = hills(31)
    p.ridge(far, "#e4edf2")
    band = far_forest(32, far)
    p.ridge(band, "#c2d8d6")

    middle = grove(MIDDLE)
    trees(p, middle, "#a6cbbf", "#f6fafa", "#c8b4a6")
    ground = bank(33)
    p.ridge(ground, "#eef4f6")
    p.dashes(drifts(rng, ground), "#dfe9ef")

    sprite(p, CABIN, CABIN_X, CABIN_FOOT, {"S": "#fbfcfc", "E": "#c3aa99", "L": "#dcb89e", "l": "#d3ae94", "W": "#f6d48a", "F": "#c3aa99", "D": "#c3aa99", "K": "#c3aa99"})
    smoke(p, "#d3dce3")

    near = grove(NEAR)
    trees(p, near, "#88b9a9", "#fbfcfc", "#c3aa99")

    # The lake: ice the page's cool cousin, the trees lying faintly on it.
    p.rect(0, SHORE, W, H - SHORE, "#e6eff3")
    p.dashes(mirror(rng, skyline(near), 5.0), "#cfe1e2")
    for runs, colour in strokes(rng, lambda col: 0.0, ["#f6fafb", "#d6e5ec"], base=0.2):
        p.dashes(runs, colour)
    return p


def night() -> Picture:
    """Dark windows: black-green pines on deep blue snow, a few dim stars, the cabin's window the one warm light."""
    p = Picture("night", "#0b0c14")
    x, y = grid()
    rng = np.random.default_rng(9)

    stars(p, 34, ("#222840", "#5b6790"), seed=23)

    rise = np.clip((y - 84) / (140 - 84), 0, 1) ** 1.8
    drift = 0.9 + 0.2 * noise(W, 12, 3, 8.0)[None, :]
    p.tone(rise * 1.6 * drift, ["#0e1427", "#111a33"])

    far = hills(31)
    p.ridge(far, "#151e36")
    band = far_forest(32, far)
    p.ridge(band, "#0b111d")

    middle = grove(MIDDLE)
    trees(p, middle, "#08100f", "#1c2944", "#0c0b0c")
    ground = bank(33)
    p.ridge(ground, "#141d34")
    p.dashes(drifts(rng, ground), "#1a2440")

    sprite(p, CABIN, CABIN_X, CABIN_FOOT, {"S": "#24304b", "E": "#0d0a09", "L": "#1d1411", "l": "#160f0d", "W": "#ffc56a", "F": "#3a2412", "D": "#0d0a09", "K": "#0d0a09"})
    smoke(p, "#232b42")

    near = grove(NEAR)
    trees(p, near, "#040807", "#1f2d4a", "#050505")

    p.rect(0, SHORE, W, H - SHORE, "#0a0f1c")
    for runs, colour in strokes(rng, lambda col: 0.0, ["#131c31"], base=0.16):
        p.dashes(runs, colour)
    # The window's light lying on the ice.
    wx = CABIN_X + 8
    p.dashes([(wx, SHORE + 2, 2), (wx - 1, SHORE + 4, 3), (wx, SHORE + 7, 2)], "#6e4f26")
    return p
