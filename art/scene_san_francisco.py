"""San Francisco: the Golden Gate with fog rolling through, the Marin headlands at one end and the city at the other."""

from __future__ import annotations

import math

import numpy as np

from dither import H, SHORE, W, Picture, Skyline, grid, lights, noise, stars, strokes

ID = "san-francisco"
NAME = "San Francisco"
DESCRIPTION = "The Golden Gate Bridge with fog rolling through, the Marin headlands at one end and the city's towers at the other."
TAGS = ["city", "skyline", "usa", "bridge", "fog"]

# Where things stand, the same by day and by night.
NORTH, SOUTH = 188, 292  # the centres of the two towers
TOP = 94  # the tips of the towers
DECK = 131  # the roadway: this row and the next
ANCHOR_N, ANCHOR_S = 158, 324  # where the side-span cables come down
DECK_FROM, DECK_TO = 140, 338  # where the deck meets the land at each end
SALESFORCE, TRANSAMERICA = 346, 364
SUTRO = 462


# ---- shapes of whole pixels ----


def blank() -> np.ndarray:
    return np.zeros((H, W), dtype=bool)


def paint(p: Picture, mask: np.ndarray, fill: str):
    """Any shape of whole pixels, as one path: each run of a row, carried down the rows it repeats on."""
    d = ""
    live: dict[tuple[int, int], int] = {}
    for row in range(H + 1):
        runs = set()
        if row < H and mask[row].any():
            edges = np.flatnonzero(np.diff(np.concatenate(([0], mask[row].astype(np.int8), [0]))))
            runs = {(int(a), int(b - a)) for a, b in zip(edges[::2], edges[1::2])}
        for run in sorted(r for r in live if r not in runs):
            start = live.pop(run)
            d += f"M{run[0]} {start}h{run[1]}v{row - start}h-{run[1]}z"
        for run in runs:
            live.setdefault(run, row)
    if d:
        p.body.append(f'<path fill="{fill}" d="{d}"/>')


def pattern(mask: np.ndarray, cx: int, top: int, rows) -> int:
    """Rows of '#' and '.' centred on column cx, from row `top` down: (text, how many rows) each. Returns the row below."""
    y = top
    for text, n in rows:
        x0 = cx - len(text) // 2
        for i, ch in enumerate(text):
            if ch == "#":
                mask[y : y + n, x0 + i] = True
        y += n
    return y


# ---- the bridge ----


def tower(cx: int) -> np.ndarray:
    """An art-deco tower: two legs that step out as they come down, joined by struts,
    the openings between them taller the lower they are, and the deck passing through the lowest."""
    m = blank()
    y = pattern(
        m,
        cx,
        TOP,
        [
            (".##.....##.", 1),  # the tops of the legs
            (".#########.", 2),  # the top strut
            (".##.....##.", 4),
            (".#########.", 1),
            ("###.....###", 6),
            ("###########", 1),
            ("###.....###", 8),
            ("###########", 1),
        ],
    )
    pattern(m, cx, y, [("###.....###", DECK - y), ("###########", 3)])
    pattern(m, cx, DECK + 3, [("###.....###", SHORE - 3 - DECK - 3), ("#############", 3)])
    return m


def hang(m: np.ndarray, x0: int, x1: int, row, out: list):
    """A cable of whole pixels from column x0 to x1, its row at each column given by row(x), never broken."""
    last = None
    for cx in range(x0, x1 + 1):
        cy = int(round(row(cx)))
        if last is not None and abs(cy - last) > 1:
            step = 1 if cy > last else -1
            for yy in range(last + step, cy, step):
                m[yy, cx] = True
        m[cy, cx] = True
        out.append((cx, cy))
        last = cy


def cables():
    """The main cables: one sweep between the towers, and one from each tower down to its anchorage.
    Returns them as a mask and as a list of (column, row)."""
    m = blank()
    path: list[tuple[int, int]] = []
    saddle = TOP + 1
    a, b = NORTH + 6, SOUTH - 6
    low = DECK - 2
    hang(m, a, b, lambda x: saddle + (low - saddle) * (1 - ((x - (a + b) / 2) / ((b - a) / 2)) ** 2), path)

    def side(x0, x1, y0, y1, sag):
        def row(x):
            t = (x - x0) / (x1 - x0)
            return y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)

        return row

    hang(m, ANCHOR_N, NORTH - 6, side(ANCHOR_N, NORTH - 6, DECK - 1, saddle, 4), path)
    hang(m, SOUTH + 6, ANCHOR_S, side(SOUTH + 6, ANCHOR_S, saddle, DECK - 1, 4), path)
    return m, path


def hangers(path) -> np.ndarray:
    """The thin suspender ropes: every third column, from the cable down to the deck."""
    m = blank()
    for cx, cy in path:
        if cx % 3 == 0 and cy < DECK - 2:
            m[cy + 1 : DECK, cx] = True
    return m


def deck() -> tuple[np.ndarray, np.ndarray]:
    """The roadway with its anchorages, and the truss under it with the piers that carry the ends over the shore."""
    road, truss = blank(), blank()
    road[DECK, DECK_FROM:DECK_TO] = True
    truss[DECK + 1, DECK_FROM:DECK_TO] = True
    for x in list(range(DECK_FROM + 4, ANCHOR_N, 7)) + list(range(ANCHOR_S + 6, DECK_TO - 2, 7)):
        truss[DECK + 2 : SHORE, x] = True
    for x in (ANCHOR_N, ANCHOR_S):
        road[DECK - 2 : SHORE, x - 2 : x + 3] = True
    return road, truss


def bridge():
    """(towers, cables, cable path, hangers, road, truss)."""
    towers = tower(NORTH) | tower(SOUTH)
    cab, path = cables()
    road, truss = deck()
    return towers, cab, path, hangers(path), road, truss


# ---- the land and the city ----


def hills(bumps, seed: int, rough: float) -> np.ndarray:
    """Soft rounded hills: (x, height, half width) each, the first row of land in every column."""
    x = np.arange(W) + 0.5
    rise = np.zeros(W)
    for at, height, half in bumps:
        rise = np.maximum(rise, height * np.clip(1 - ((x - at) / half) ** 2, 0, 1) ** 0.8)
    rise += rough * (noise(W, seed, 4, 14.0) - 0.5)
    return np.where(rise > 0.5, np.round(SHORE - rise), SHORE).astype(int)


def headlands():
    """The Marin headlands: a far ridge, and the near one the bridge lands on."""
    far = hills([(30, 34, 60), (96, 42, 56), (150, 30, 44), (196, 12, 30)], 21, 2.0)
    near = hills([(58, 30, 62), (118, 36, 44), (150, 22, 24)], 22, 1.6)
    return far, near


def city():
    """The city at the far end: a far row of blocks and Twin Peaks, the two towers everyone knows, and the Presidio's shore."""
    far, mid, shore = Skyline(), Skyline(), Skyline()
    far.blocks(318, 400, 138, 126, seed=31, widths=(4, 9), gap=(0, 2))
    far.blocks(400, W, 141, 133, seed=32, widths=(5, 11), gap=(0, 2))
    far.tops = np.minimum(far.tops, peaks())

    # Salesforce Tower: tall and plain, a little narrower near the top, which is rounded off.
    mid.box(SALESFORCE - 3, 7, 122).box(SALESFORCE - 2, 5, 103).box(SALESFORCE - 1, 3, 101)
    # The Transamerica Pyramid: a slim pyramid, its spire a quarter of its height.
    for row in range(111, SHORE):
        left, right = (row - 111 + 4) // 7, (row - 111) // 7
        mid.box(TRANSAMERICA - left, 1 + left + right, row)
    mid.box(TRANSAMERICA, 1, 102)
    # Their neighbours, lower, and kept clear of the pyramid's flanks.
    for x0, w, top in [(326, 6, 130), (331, 5, 124), (336, 6, 128), (352, 6, 117), (357, 2, 129), (371, 2, 131), (373, 6, 125), (379, 5, 131), (384, 7, 128)]:
        mid.box(x0, w, top)
    mid.blocks(391, 440, 140, 132, seed=33, widths=(4, 8), gap=(1, 4))

    # The Presidio's low wooded shore where the bridge comes down.
    shore.blocks(DECK_TO - 18, 400, 143, 139, seed=34, widths=(3, 7), gap=(0, 0))
    return far.tops, mid.tops, shore.tops


def peaks() -> np.ndarray:
    """Twin Peaks and the hill beside them, out where only wide windows reach."""
    return hills([(SUTRO - 2, 17, 20), (486, 15, 18), (506, 11, 20)], 23, 0.0)


def sutro() -> np.ndarray:
    """Sutro Tower on its hill: three masts, two crossbars, its legs spread at the foot."""
    m = blank()
    foot = int(peaks()[SUTRO]) + 1
    pattern(m, SUTRO, foot - 22, [("#.#.#", 3), ("#####", 1), ("#.#.#", 4), ("#####", 1), (".#.#.", 3), (".###.", 1), (".#.#.", 3), ("#...#", 6)])
    return m


# ---- the fog ----


def billows(base: int, puffs, seed: int) -> np.ndarray:
    """The top of a fog bank: round puffs, (x, height, half width) each, run together, a little ragged."""
    x = np.arange(W) + 0.5
    rise = np.zeros(W)
    for at, height, half in puffs:
        rise = np.maximum(rise, height * np.clip(1 - ((x - at) / half) ** 2, 0, 1) ** 0.5)
    return base - rise - 1.5 * noise(W, seed, 4, 24.0)


def bank(x, y) -> np.ndarray:
    """The fog bank behind the bridge: piled up in the gate, lower against the hills and the city."""
    puffs = [(140, 9, 18), (164, 13, 16), (190, 12, 14), (214, 21, 18), (240, 26, 22), (266, 20, 16), (288, 13, 14), (314, 13, 16), (340, 8, 16), (366, 9, 18), (392, 6, 18)]
    top = billows(143, puffs, 41)
    return np.clip((y - top[None, :]) / 7, 0, 1)


def wisps(x, y) -> np.ndarray:
    """Low wisps in front, about the feet of the towers and the headland, lapping at the deck."""
    puffs = [(150, 6, 12), (180, 10, 9), (197, 8, 9), (238, 4, 14), (285, 9, 9), (301, 11, 9), (330, 5, 10)]
    top = billows(146, puffs, 43)
    return 0.88 * np.clip((y - top[None, :]) / 4, 0, 1)


def wafts() -> list[tuple[np.ndarray, int]]:
    """Two thin wisps drifting across the deck in front of the bridge: (shape, how thick its dots) each,
    each wisp thicker toward its middle."""
    x, y = grid()
    out = []
    for cx, cy, half, tall in [(236, 130.5, 30, 3.2), (342, 135.0, 16, 2.6)]:
        d = ((x - cx) / half) ** 2 + ((y - cy) / tall) ** 2
        for reach, level in [(1.0, 3), (0.55, 6), (0.22, 9)]:
            out.append((d <= reach, level))
    return out


# ---- the two lights ----


def day() -> Picture:
    """Light windows: the bridge in a pale international orange, a cool white fog rolling through behind it."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()

    # A clear pale blue over the fog, nothing in the upper part of the window.
    rise = np.clip((y - 72) / (138 - 72), 0, 1) ** 1.7
    drift = 0.88 + 0.24 * noise(W, 7, 3, 8.0)[None, :]
    p.tone(rise * 1.7 * drift, ["#e2eaf0", "#d3e0ec"])

    far_hills, near_hills = headlands()
    far, mid, shore = city()
    p.ridge(far_hills, "#d3dccf")
    p.ridge(far, "#dcdcec")
    paint(p, sutro(), "#c4c7df")
    p.ridge(mid, "#b7bfdd")
    p.dashes([(SALESFORCE - 1, 101, 3), (SALESFORCE - 2, 103, 5), (SALESFORCE - 2, 105, 5)], "#d3d8ec")

    p.tone(bank(x, y) * 1.4, ["#fbfbfa", "#e8edf1"], foot=SHORE + 2)
    p.ridge(near_hills, "#b9c9ad")
    p.ridge(shore, "#a9c2a6")

    towers, cab, path, hang_, road, truss = bridge()
    paint(p, hang_, "#f8d8ca")
    paint(p, truss, "#e89883")
    paint(p, cab | road | towers, "#ee9c82")

    p.tone(wisps(x, y), ["#fbfcfc"], foot=SHORE + 2)
    for shape, level in wafts():
        paint(p, shape, p.level("#fbfbfa", level))

    # The water: the page again, the bridge lying on it in short strokes.
    p.rect(0, SHORE, W, H - SHORE, "#f1f0ea")
    rng = np.random.default_rng(5)
    under = lambda col: max(math.exp(-(((col - NORTH) / 6) ** 2)), math.exp(-(((col - SOUTH) / 6) ** 2)))
    for runs, colour in strokes(rng, under, ["#c9d6e3", "#f2b9a4"], base=0.22, gain=0.6):
        p.dashes(runs, colour)
    return p


def night() -> Picture:
    """Dark windows: the bridge a dark rust against the fog's faint glow, a row of amber lamps along its deck."""
    p = Picture("night", "#0b0c14")
    x, y = grid()
    rng = np.random.default_rng(9)

    stars(p, 34, ("#222842", "#6f7aa6"), seed=6)

    # The sky: navy, a little lighter low down.
    rise = np.clip((y - 84) / (142 - 84), 0, 1) ** 1.6
    drift = 0.88 + 0.24 * noise(W, 8, 3, 8.0)[None, :]
    p.tone(rise * 1.6 * drift, ["#11152a", "#191e36"])

    far_hills, near_hills = headlands()
    far, mid, shore = city()
    p.ridge(far_hills, "#0e121c")
    p.ridge(far, "#141831")
    lights(p, far, [("#6a5a52", 2), ("#3f5a70", 1)], chance=0.12, seed=51)
    paint(p, sutro(), "#1b2040")
    tip = int(np.flatnonzero(sutro().any(axis=1))[0])
    p.dashes([(SUTRO - 2, tip, 1), (SUTRO, tip, 1), (SUTRO + 2, tip, 1)], "#b8434a")
    p.ridge(mid, "#191d3a")
    lights(p, np.maximum(mid, 112), [("#9a7440", 2), ("#d9b062", 1), ("#8fb4d8", 1)], chance=0.22, seed=52, x0=320, x1=400)
    p.dashes([(SALESFORCE - 1, 101, 3), (SALESFORCE - 2, 103, 5)], "#5d6b9a")
    p.dashes([(TRANSAMERICA, 102, 1)], "#e5484d")

    # The fog bank, lit faintly by the city.
    p.tone(bank(x, y) * 1.5, ["#1b2134", "#262c42"], foot=SHORE + 2)
    p.ridge(near_hills, "#080a10")
    p.ridge(shore, "#06080d")

    towers, cab, path, hang_, road, truss = bridge()
    paint(p, hang_, "#211617")
    paint(p, truss, "#2a1414")
    paint(p, cab | road | towers, "#3a1c1b")
    p.dashes([(NORTH - 3, TOP, 1), (NORTH + 3, TOP, 1), (SOUTH - 3, TOP, 1), (SOUTH + 3, TOP, 1)], "#e5484d")  # on the legs' tops
    p.dashes([(cx, DECK, 1) for cx in range(DECK_FROM + 2, DECK_TO - 1, 4)], "#e8a650")

    p.tone(wisps(x, y), ["#262c40"], foot=SHORE + 2)
    for shape, level in wafts():
        paint(p, shape, p.level("#2a3044", level))

    # The water: black, the lamps lying on it in broken strokes.
    p.rect(0, SHORE, W, H - SHORE, "#07080f")
    lamp = lambda col: 0.5 * (0.5 + 0.5 * math.cos(col * 1.7)) if DECK_FROM < col < DECK_TO else 0.0
    for runs, colour in strokes(rng, lamp, ["#1a2140", "#8a5f30"], base=0.1, gain=0.3):
        p.dashes(runs, colour)
    return p
