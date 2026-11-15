"""Tokyo: a pale sun beside Fuji over a pastel city by day, the towers lit over a pink haze by night."""

from __future__ import annotations

import math

import numpy as np

from dither import H, SHORE, W, Picture, Skyline, grid, lights, noise, stars, strokes

ID = "tokyo"
NAME = "Tokyo"

# Where things stand, the same by day and by night.
FUJI_X, FUJI_TOP = 300, 98
TOWER_X, TOWER_TIP = 196, 88
TREE_X, TREE_TIP = 352, 84
PAGODA_X = 160
SUN_X, SUN_Y, SUN_R = 238.0, 122.0, 10.0


# ---- shapes of whole pixels that a skyline cannot hold (overhangs, openings) ----


def blank() -> np.ndarray:
    return np.zeros((H, W), dtype=bool)


def bar(mask: np.ndarray, cx: int, y: int, width: int, rows: int = 1, on: bool = True):
    """`rows` rows of `width` pixels (odd), centred on column cx, from row y down."""
    mask[y : y + rows, cx - width // 2 : cx - width // 2 + width] = on


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


def fuji() -> np.ndarray:
    """The cone: the first row of mountain in every column. A flat summit, then slopes that ease out."""
    d = np.abs(np.arange(W) + 0.5 - FUJI_X)
    u = np.clip((d - 4.5) / 104.0, 0, 1)
    return np.round(SHORE - (SHORE - FUJI_TOP) * (1 - u) ** 1.7).astype(int)


def snow_cap(cone: np.ndarray) -> np.ndarray:
    """The snow: the summit down to a zigzag line, each tooth a gully the snow lies longer in."""
    mask = blank()
    teeth = [(-16, 3), (-11, 5), (-6, 3), (-1, 6), (4, 3), (9, 5), (14, 4), (18, 2)]
    for dx in range(-20, 20):
        line = FUJI_TOP + 6 + max(max(0, deep - abs(dx - at)) for at, deep in teeth)
        mask[cone[FUJI_X + dx] : line, FUJI_X + dx] = True
    return mask


def tokyo_tower():
    """A flared A narrowing to a mast, with two decks. Returns (frame, solid): the lattice and the solid parts."""
    cx = TOWER_X
    frame, solid = blank(), blank()
    bar(solid, cx, TOWER_TIP, 1, 14)  # mast, rows 88..101
    bar(solid, cx, 102, 5, 2)  # top deck
    bar(frame, cx, 104, 3, 7)
    bar(frame, cx, 111, 5, 7)
    bar(solid, cx, 118, 9, 3)  # main deck
    arch = 131
    for y in range(121, SHORE):
        t = (y - 121) / (SHORE - 1 - 121)
        bar(frame if y < arch else solid, cx, y, 2 * int(round(3 + 5 * t**1.8)) + 1)
    # The arch between the legs.
    for y, inner in zip(range(arch, SHORE), [0, 1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4]):
        bar(solid, cx, y, 2 * inner + 1, on=False)
    return frame, solid


def skytree() -> np.ndarray:
    """Very thin and tall: a needle, two small decks, a shaft that widens a little to its foot."""
    cx = TREE_X
    m = blank()
    bar(m, cx, TREE_TIP, 1, 13)  # rows 84..96
    bar(m, cx, 97, 3, 3)
    bar(m, cx, 100, 5, 2)  # upper deck
    bar(m, cx, 102, 3, 6)
    bar(m, cx, 108, 5, 3)  # lower deck
    bar(m, cx, 111, 3, 19)
    bar(m, cx, 130, 5, SHORE - 130)
    return m


def pagoda() -> np.ndarray:
    """Five roofs, each wider than the one above, their corners turned up."""
    cx = PAGODA_X
    m = blank()
    bar(m, cx, 112, 1, 8)  # the finial and its rings
    bar(m, cx, 114, 3)
    bar(m, cx, 116, 3)
    y = 120
    for eave, body in [(9, 3), (11, 3), (13, 5), (15, 5), (17, 7)]:
        bar(m, cx, y, eave - 6)  # the roof's rise
        m[y, cx - eave // 2 - 1] = m[y, cx + eave // 2 + 1] = True  # the turned-up corners
        bar(m, cx, y + 1, eave)  # the eave
        bar(m, cx, y + 2, body, 2)
        y += 4
    bar(m, cx, y, 7, SHORE - 2 - y)
    bar(m, cx, SHORE - 2, 11, 2)  # the platform
    return m


def city() -> tuple[Skyline, Skyline]:
    """The blocks in two depths: the far row taller and paler, the near row low along the water.
    Both keep low behind the pagoda, the tower, the sun and Fuji."""
    far, near = Skyline(), Skyline()
    far.box(0, W, 138)
    for x0, w, top in [
        (128, 8, 129), (136, 6, 125), (142, 6, 131), (172, 6, 130), (178, 7, 126), (185, 4, 133),
        (206, 5, 131), (211, 7, 124), (213, 3, 121), (218, 6, 129), (224, 5, 134),
        (229, 8, 136), (246, 8, 135), (261, 9, 134), (276, 10, 135), (294, 9, 136), (310, 10, 134), (328, 9, 135),
        (337, 7, 132), (344, 6, 129), (356, 7, 127), (363, 6, 131), (369, 8, 123), (371, 4, 121), (377, 7, 128), (384, 6, 132),
    ]:
        far.box(x0, w, top)
    far.blocks(0, 128, 135, 123, 3, widths=(5, 11), gap=(0, 3))
    far.blocks(391, W, 135, 123, 4, widths=(5, 11), gap=(0, 3))
    near.box(0, W, 143)
    for x0, w, top in [
        (126, 9, 137), (135, 9, 133), (144, 6, 139), (171, 8, 138), (179, 8, 141),
        (206, 7, 139), (213, 9, 134), (222, 8, 138), (230, 10, 141), (240, 9, 139), (257, 9, 140), (266, 8, 137),
        (274, 10, 141), (284, 9, 139), (304, 8, 140), (312, 9, 138), (329, 10, 139), (339, 8, 136), (347, 9, 140),
        (364, 9, 135), (373, 8, 138), (381, 9, 141),
    ]:
        near.box(x0, w, top)
    near.blocks(0, 126, 142, 133, 5, widths=(6, 13), gap=(0, 3))
    near.blocks(390, W, 142, 133, 6, widths=(6, 13), gap=(0, 3))
    return far, near


def day() -> Picture:
    """Light windows: a pale sun coming up beside Fuji, the city in cherry pink and grey blue."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()

    # The morning sky: nothing where the chat is, peach and then pink toward the roofs, warmest round the sun.
    rise = np.clip((y - 70) / (142 - 70), 0, 1) ** 1.9
    halo = np.exp(-(((x - SUN_X) / 100) ** 2) - ((y - SUN_Y) / 52) ** 2)
    drift = 0.9 + 0.2 * noise(W, 7, 3, 8.0)[None, :]
    p.tone(rise * (0.26 + 1.25 * halo) * drift, ["#fbe0d1", "#f8c8ba"])

    # The sun: a pale disc, dotted thicker toward its foot.
    p.disc(SUN_X, SUN_Y, SUN_R, "#fbd2c0")
    p.disc(SUN_X, SUN_Y, SUN_R, p.level("#f5a598", 5), rows=(int(SUN_Y - SUN_R), int(SUN_Y - 3)))
    p.disc(SUN_X, SUN_Y, SUN_R, p.level("#f5a598", 9), rows=(int(SUN_Y - 3), int(SUN_Y + SUN_R) + 1))

    # Fuji, far and faint, with its snow.
    cone = fuji()
    p.ridge(cone, "#d9e0ee")
    paint(p, snow_cap(cone), "#ffffff")

    far, near = city()
    p.ridge(far.tops, "#f2bfd0")
    paint(p, skytree(), "#b7c3e2")
    p.ridge(near.tops, "#9db3d6")

    frame, solid = tokyo_tower()
    paint(p, frame | solid, "#f9cfc2")
    paint(p, frame, p.level("#ef8b76", 8))
    paint(p, solid, "#ef8b76")
    paint(p, pagoda(), "#e88ba4")

    # The river: the page again, with the city and the sun lying on it in fine strokes.
    p.rect(0, SHORE, W, H - SHORE, "#f3edea")
    rng = np.random.default_rng(5)
    mix = 0.6 * noise(W, 8, 4, 30.0)
    under_sun = lambda col: max(math.exp(-(((col - SUN_X) / 20) ** 2)), mix[col])
    for runs, colour in strokes(rng, under_sun, ["#f3bccb", "#a9bcd9", "#ee8f9c"], base=0.22, gain=0.5):
        p.dashes(runs, colour)
    return p


def night() -> Picture:
    """Dark windows: the same city lit, a pink haze low over the roofs, Fuji dark with a pale cap."""
    p = Picture("night", "#0b0c14")
    x, y = grid()
    rng = np.random.default_rng(9)

    stars(p, 40, ("#2b2a55", "#7d78b8"), seed=4)

    # The sky: indigo, thin where the chat is, and the city's own light low over the roofs.
    low = np.clip((y - 78) / (102 - 78), 0, 1) ** 1.5
    high = np.clip((y - 102) / (140 - 102), 0, 1) ** 1.3
    glow = (0.62 + 0.5 * np.exp(-(((x[0] - 256) / 150) ** 2))) * (0.86 + 0.28 * noise(W, 12, 3, 9.0))
    field = 0.3 * low + 3.2 * high * glow[None, :]
    p.tone(field, ["#1d1a45", "#45205e", "#84296b", "#d0508a"])

    cone = fuji()
    p.ridge(cone, "#191b3a")
    paint(p, snow_cap(cone), "#5a5f8c")

    far, near = city()
    p.ridge(far.tops, "#121126")
    lights(p, far.tops, [("#8f6f9c", 3), ("#b0577f", 2), ("#4f8f9c", 1)], chance=0.22, seed=21)

    tree = skytree()
    paint(p, tree, "#4d4390")
    p.dashes([(TREE_X, yy, 1) for yy in range(114, 140, 4)], "#9a8cf0")
    p.dashes([(TREE_X + dx, yy, 1) for yy in (100, 108) for dx in (-2, 0, 2)] + [(TREE_X, TREE_TIP, 1)], "#cfc9ff")

    p.ridge(near.tops, "#07070d")
    lights(p, near.tops, [("#ffe9b8", 4), ("#ff7eb6", 2), ("#6fe3ee", 2)], chance=0.3, seed=22)

    frame, solid = tokyo_tower()
    paint(p, frame | solid, "#8a3a1a")
    paint(p, frame, p.level("#e06a2a", 8))
    paint(p, solid, "#c8582a")
    p.dashes([(TOWER_X - 4, 118, 9), (TOWER_X, 102, 1), (TOWER_X, TOWER_TIP, 1)], "#ffc56b")
    paint(p, pagoda(), "#07070d")

    # The river: black, with the city's colours lying on it in broken strokes.
    p.rect(0, SHORE, W, H - SHORE, "#07080e")
    shine = 0.25 + 0.75 * noise(W, 13, 5, 40.0)
    for runs, colour in strokes(rng, lambda col: shine[col], ["#2c2a63", "#8c3270", "#2f8fa3"], base=0.1, gain=0.5):
        p.dashes(runs, colour)
    warm = lambda col: math.exp(-(((col - TOWER_X) / 10) ** 2))
    for runs, colour in strokes(rng, warm, ["#b5502a", "#f08a3c"], base=0.0, gain=0.7):
        p.dashes(runs, colour)
    return p
