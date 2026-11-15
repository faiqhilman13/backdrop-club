"""New York: Manhattan across the water, an apricot dawn by day, amber haze and lit windows by night."""

from __future__ import annotations

import math

import numpy as np

from dither import H, SHORE, W, Picture, Skyline, grid, lights, noise, stars, strokes

ID = "new-york"
NAME = "New York"

# Where the three towers everyone knows stand, and the gap the sun comes up in.
EMPIRE, CHRYSLER, TRADE = 215, 262, 318
SUN_X, SUN_Y, SUN_R = 290.0, 125.0, 12.0


def city():
    """The buildings, the same by day and by night: a far row, the towers, and the waterfront."""
    far, mid, near = Skyline(), Skyline(), Skyline()

    # The far row: ordinary blocks, low where the bridge and the sun want to be seen.
    for x0, w, top in [
        (112, 14, 139), (126, 14, 142), (140, 12, 140), (152, 16, 143), (168, 10, 141), (178, 12, 143), (190, 6, 138), (196, 4, 129),
        (200, 7, 119), (207, 17, 124),
        (224, 8, 121), (232, 7, 126), (244, 8, 118), (252, 6, 123),
        (258, 10, 126), (268, 7, 124), (275, 9, 131), (284, 10, 136), (294, 8, 134), (302, 7, 128), (309, 17, 125),
        (326, 8, 120), (334, 7, 125), (341, 9, 117), (350, 8, 123), (358, 9, 127), (367, 8, 121), (375, 10, 129), (385, 9, 133),
    ]:
        far.box(x0, w, top)
    far.blocks(0, 118, 138, 128, seed=7, widths=(6, 13), gap=(0, 2))
    far.blocks(394, W, 138, 127, seed=8, widths=(6, 13), gap=(0, 2))

    # The Empire State Building: broad shoulders, then the mast.
    mid.stack(EMPIRE, [(17, 4), (13, 12), (11, 24), (9, 2), (7, 3), (3, 8), (1, 9)])
    # The Chrysler Building: a slim shaft sharpening to a needle.
    mid.stack(CHRYSLER, [(11, 7), (9, 8), (7, 20), (5, 6), (3, 4), (1, 7)])
    # One World Trade Center: a slab that narrows as it climbs, flat on top, and its spire.
    for w, top in [(15, 140), (13, 131), (11, 122), (9, 113), (7, 104)]:
        mid.box(TRADE - w // 2, w, top)
    mid.spire(TRADE, 89)
    # Two newer ones: a pencil between the old pair, and a slant-roofed one downtown.
    mid.box(239, 3, 101)
    for i in range(6):
        mid.box(349 + i, 1, 109 + i)
    # Lower blocks about their feet.
    for x0, w, top in [
        (197, 9, 129), (224, 7, 131), (231, 6, 127), (246, 8, 132), (269, 8, 130),
        (303, 7, 133), (327, 9, 127), (338, 7, 124), (358, 8, 130), (368, 8, 126), (378, 9, 133),
    ]:
        mid.box(x0, w, top)
    mid.blocks(0, 112, 142, 132, seed=17, widths=(5, 10), gap=(5, 16))
    mid.blocks(392, W, 142, 131, seed=18, widths=(5, 10), gap=(5, 16))

    # The waterfront: long and low. Left of the bridge is the shore the bridge leaves from.
    for x0, w, top in [
        (104, 12, 138), (116, 12, 136),
        (205, 9, 137), (214, 12, 139), (226, 10, 135), (236, 12, 140), (248, 9, 137), (257, 12, 141), (269, 10, 138),
        (279, 14, 142), (293, 12, 141), (305, 9, 138), (314, 12, 140), (326, 10, 136), (336, 13, 139), (349, 9, 134), (358, 12, 138), (370, 10, 140), (380, 12, 136),
    ]:
        near.box(x0, w, top)
    near.blocks(0, 104, 143, 137, seed=27, widths=(8, 18), gap=(0, 3))
    near.blocks(392, W, 143, 136, seed=28, widths=(8, 18), gap=(0, 3))
    return far.tops, mid.tops, near.tops


def bridge():
    """The bridge as pixels: two stone towers, each with a pair of pointed arches, the deck,
    and the cable hanging between. Also returns the cable's pixels alone, for its lights."""
    m = np.zeros((H, W), bool)
    top, deck = 124, 136
    towers = (142, 182)  # the left edge of each; they are 9 wide
    m[deck:deck + 2, 124:209] = True
    for tx in towers:
        m[top:SHORE, tx:tx + 9] = True
        for ax in (tx + 1, tx + 5):
            m[top + 4:deck, ax:ax + 3] = False
            m[top + 3, ax + 1] = False

    cable = []

    def hang(x0, x1, row):
        last = None
        for cx in range(x0, x1 + 1):
            cy = int(round(row(cx)))
            if last is not None and abs(cy - last) > 1:
                step = 1 if cy > last else -1
                for yy in range(last + step, cy, step):
                    m[yy, cx] = True
            m[cy, cx] = True
            cable.append((cx, cy))
            last = cy

    a, b = towers[0] + 9, towers[1] - 1  # the span between the towers
    centre, half = (a + b) / 2, (b - a) / 2
    hang(a, b, lambda cx: 134 - 10 * ((cx - centre) / half) ** 2)
    hang(128, towers[0] - 1, lambda cx: 135 - 11 * ((cx - 128) / 13) ** 2)
    hang(towers[1] + 9, 204, lambda cx: 135 - 11 * ((204 - cx) / 13) ** 2)
    return m, cable


def pixels(p: Picture, mask: np.ndarray, fill: str):
    """Draws a set of pixels: runs along each row, joined downward where a run repeats."""
    d = ""
    running = {}
    for row in range(mask.shape[0] + 1):
        here = set()
        if row < mask.shape[0]:
            xs = np.flatnonzero(mask[row])
            if xs.size:
                cuts = np.flatnonzero(np.diff(xs) > 1)
                for s, e in zip(np.r_[xs[0], xs[cuts + 1]], np.r_[xs[cuts], xs[-1]]):
                    here.add((int(s), int(e - s + 1)))
        for run in sorted(set(running) - here):
            x0, n = run
            y0 = running.pop(run)
            d += f"M{x0} {y0}h{n}v{row - y0}h-{n}z"
        for run in here:
            running.setdefault(run, row)
    if d:
        p.body.append(f'<path fill="{fill}" d="{d}"/>')


def inside(tops: np.ndarray) -> np.ndarray:
    """A skyline with its sides shaved by a pixel, so that no lit window sits on an outline."""
    return np.maximum.reduce([np.roll(tops, 1), tops, np.roll(tops, -1)])


def day() -> Picture:
    """Light windows: the sun coming up in the gap between midtown and downtown."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()

    # The glow: nothing in the upper part of the window, warmest round the sun.
    rise = np.clip((y - 70) / (134 - 70), 0, 1) ** 2.1
    halo = np.exp(-(((x - SUN_X) / 100) ** 2) - ((y - SUN_Y) / 54) ** 2)
    drift = 0.9 + 0.2 * noise(W, 11, 3, 8.0)[None, :]
    p.tone(rise * (0.3 + 1.3 * halo) * drift, ["#fbe0c8", "#f7c49c"])

    # The sun: a pale disc, dotted thicker toward its foot.
    p.disc(SUN_X, SUN_Y, SUN_R, "#fdf0d2")
    p.disc(SUN_X, SUN_Y, SUN_R, p.level("#f9cf9b", 4), rows=(int(SUN_Y - 5), int(SUN_Y + 2)))
    p.disc(SUN_X, SUN_Y, SUN_R, p.level("#f9cf9b", 8), rows=(int(SUN_Y + 2), int(SUN_Y + SUN_R) + 1))

    far, mid, near = city()
    p.ridge(far, "#dcd8ec")
    p.ridge(mid, "#bcc0e2")
    p.ridge(near, "#9ba8cf")
    span, _ = bridge()
    pixels(p, span, "#9ba8cf")

    # The water: the page again, the sun lying on it in short strokes.
    p.rect(0, SHORE, W, H - SHORE, "#f2ede6")
    rng = np.random.default_rng(5)
    under_sun = lambda col: math.exp(-(((col - SUN_X) / 24) ** 2))
    for runs, colour in strokes(rng, under_sun, ["#c5cae8", "#f6c9a3", "#ee9f73"], base=0.22, gain=0.55):
        p.dashes(runs, colour)
    return p


def night() -> Picture:
    """Dark windows: the city's own light low in a navy sky, windows lit, beacons on the masts."""
    p = Picture("night", "#0b0c14")
    x, y = grid()
    rng = np.random.default_rng(9)

    stars(p, 36, ("#232a48", "#7682ac"), seed=4)

    # The haze: barely there where the chat is, amber only down among the roofs.
    high = 0.26 * np.clip((y - 64) / (100 - 64), 0, 1) ** 1.6
    glow = (0.6 + 0.4 * np.exp(-(((x - 268) / 130) ** 2))) * (0.86 + 0.28 * noise(W, 12, 3, 8.0)[None, :])
    low = np.clip((y - 100) / (138 - 100), 0, 1) ** 1.15
    field = high + 3.6 * glow * low
    p.tone(field, ["#14132d", "#33203f", "#784630", "#c5852f"])

    far, mid, near = city()
    p.ridge(far, "#1f2649")
    lights(p, inside(far), [("#6b4d2e", 1)], chance=0.1, seed=31)

    # The towers, lighter than the sky they stand in, their masts lit and a red beacon on each tip.
    p.ridge(mid, "#161c3c")
    steel = "#414c85"
    p.rect(EMPIRE - 1, 93, 3, 8, steel)
    p.rect(EMPIRE, 85, 1, 8, steel)
    p.rect(CHRYSLER, 95, 1, 6, steel)
    p.rect(TRADE, 90, 1, 14, steel)
    p.dashes([(CHRYSLER, 102, 1), (CHRYSLER - 1, 105, 1), (CHRYSLER + 1, 105, 1), (CHRYSLER - 1, 108, 3)], "#c4b58e")
    p.dashes([(EMPIRE, 84, 1), (CHRYSLER, 94, 1), (TRADE, 89, 1)], "#e5484d")
    lights(p, np.maximum(inside(mid), 106), [("#8a6334", 1)], chance=0.16, seed=32, foot=118)
    lights(p, np.maximum(inside(mid), 116), [("#8a6334", 2), ("#d9a650", 1)], chance=0.22, seed=34)

    p.ridge(near, "#06070d")
    lights(p, inside(near), [("#b5803a", 2), ("#f0c468", 1)], chance=0.3, seed=33)
    span, cable = bridge()
    pixels(p, span, "#06070d")
    p.dashes([(cx, cy, 1) for cx, cy in cable[::3]], "#d9b36a")

    # The water: black, with the city's light lying on it in broken strokes.
    p.rect(0, SHORE, W, H - SHORE, "#07080f")
    shine = np.clip((glow[0] - 0.62) / 0.45, 0, 1)
    for runs, colour in strokes(rng, lambda col: shine[col], ["#1a2142", "#5c3f2b", "#b9813a"], base=0.1, gain=0.45):
        p.dashes(runs, colour)
    return p
