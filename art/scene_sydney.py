"""Sydney: the Opera House on its point and the Harbour Bridge behind, pale harbour blues by day, warm lights by night."""

from __future__ import annotations

import math

import numpy as np

from dither import H, SHORE, W, Picture, Skyline, grid, lights, noise, stars, strokes

ID = "sydney"
NAME = "Sydney"
DESCRIPTION = "The Opera House on its point and the Harbour Bridge's steel arch behind, with Sydney Tower over the city and a ferry on the harbour."
TAGS = ["city", "skyline", "australia", "harbour", "bridge"]

# Where things stand, the same by day and by night.
PODIUM = (170, 238, 138)  # the Opera House's platform: first column, end column, top row
TOWER_X = 156  # Sydney Tower
PYLON_S, PYLON_N = 246, 366  # the centres of the bridge's two pairs of pylons
PYLON_TOP = 117
DECK = 130  # the roadway: this row and the next
CROWN = 105  # the top of the arch
BEAR = 141  # the row the arch springs from, at the foot of the pylons
FERRY = (334, 147)  # the ferry's first column and top row


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


def line(m: np.ndarray, x0: int, x1: int, row):
    """A line of whole pixels from column x0 to x1, its row at each column given by row(x), never broken."""
    last = None
    for x in range(x0, x1 + 1):
        y = int(round(row(x)))
        if last is not None and abs(y - last) > 1:
            step = 1 if y > last else -1
            for yy in range(last + step, y, step):
                m[yy, x if step < 0 else x - 1] = True
        m[y, x] = True
        last = y


# ---- the Opera House ----


def shell(m: np.ndarray, back: float, tip: float, top: float, front: float, base: int):
    """One roof shell side on, like a sail: its ridge climbs steeply from (back, base) and leans over
    to a sharp tip at (tip, top); its open mouth falls from the tip to (front, base).
    A shell whose tip is left of its back faces left."""
    for y in range(int(top), base):
        f = (base - y - 0.5) / (base - top)  # 1 at the tip, 0 at the base
        if f <= 0 or f > 1:
            continue
        ridge = back + (tip - back) * f**1.9
        mouth = tip + (front - tip) * (1 - f) ** 1.2
        a, c = sorted((ridge, mouth))
        a, c = int(round(a)), int(round(c))
        if c > a:
            m[y, a:c] = True


# The shells, each (back, tip, top row, front), from the back of the hall to the front: the first faces
# the city, the rest face the harbour, each nested in front of the one before.
NEAR = [(203, 191, 127, 193), (198, 212, 121, 210), (205, 223, 115, 220), (214, 234, 120, 231)]
FAR = [(198, 186, 124, 188), (194, 208, 117, 206), (200, 218, 111, 215), (209, 229, 115, 226)]
SMALL = [(181, 173, 131, 175), (177, 185, 129, 184)]


def shells(spec, base: int):
    """A row of nested shells: all of them as one shape, and the ridge of each where the ones in front leave it showing."""
    masks = []
    for b, t, top, f in spec:
        one = blank()
        shell(one, b, t, top, f, base)
        masks.append((one, t > b))
    body, ridges = blank(), blank()
    for i, (one, faces_right) in enumerate(masks):
        body |= one
        ridge = blank()
        for y in np.flatnonzero(one.any(axis=1)):
            xs = np.flatnonzero(one[y])
            ridge[y, xs[0] if faces_right else xs[-1]] = True
        for later, _ in masks[i + 1 :]:
            ridge &= ~later
        ridges |= ridge
    return body, ridges


def opera_house():
    """The roof: two rows of shells, the far hall's higher, on a broad podium, and the restaurant's two small shells.
    Returns (far shells, their ridges, near shells, their ridges, podium)."""
    x0, x1, base = PODIUM
    podium = blank()
    podium[base:SHORE, x0 + 6 : x1] = True
    for i in range(3):  # the broad steps at the city end
        podium[base + 2 + 2 * i : SHORE, x0 + 4 - 2 * i : x0 + 6] = True
    far, far_ridges = shells(FAR + SMALL, base)
    near, near_ridges = shells(NEAR, base)
    far_ridges &= ~near
    return far, far_ridges, near, near_ridges, podium


# ---- the Harbour Bridge ----


def chord(x: float) -> float:
    """The row of the arch's top chord at column x."""
    a, b = PYLON_S + 8, PYLON_N - 8
    mid, half = (a + b) / 2, (b - a) / 2
    return DECK - (DECK - CROWN) * (1 - ((x - mid) / half) ** 2)


def arch():
    """The arch and what hangs from it: (pylons, pylon shade, chords, lattice, hangers, deck).
    The chords and the posts between them are solid, the lattice between them dotted, the hangers thin."""
    chords, lattice, hangers, deck, pylons, shade = blank(), blank(), blank(), blank(), blank(), blank()
    a, b = PYLON_S + 8, PYLON_N - 8  # the bearings, at the inner feet of the pylons
    mid, half = (a + b) / 2, (b - a) / 2
    bottom = lambda x: BEAR - (BEAR - CROWN - 4) * (1 - ((x - mid) / half) ** 2) ** 0.85
    line(chords, a, b, chord)
    line(chords, a, b, bottom)
    for x in range(a, b + 1):
        y0, y1 = int(round(chord(x))), int(round(bottom(x)))
        lattice[y0 + 1 : y1, x] = True
        if (x - a) % 6 == 0:
            chords[y0:y1, x] = True
        if (x - a) % 4 == 2 and y1 < DECK - 1:
            hangers[y1 + 1 : DECK, x] = True
    chords[BEAR - 1 : SHORE, a - 1 : a + 1] = True
    chords[BEAR - 1 : SHORE, b : b + 2] = True
    lattice &= ~chords
    # the deck, on through the pylons to both shores
    deck[DECK : DECK + 2, 196:430] = True
    for x in list(range(200, PYLON_S - 9, 8)) + list(range(PYLON_N + 11, 430, 8)):
        deck[DECK + 2 : SHORE, x] = True
    # the pylons: stout granite towers, stepping in near the top under a flat parapet, shaded on one side
    for cx in (PYLON_S, PYLON_N):
        pylons[PYLON_TOP : PYLON_TOP + 2, cx - 5 : cx + 6] = True
        pylons[PYLON_TOP + 2 : PYLON_TOP + 3, cx - 6 : cx + 7] = True
        pylons[PYLON_TOP + 3 : DECK + 2, cx - 7 : cx + 8] = True
        pylons[DECK + 2 : SHORE, cx - 8 : cx + 9] = True
        shade[PYLON_TOP : SHORE, cx + 3 : cx + 9] = True
        shade[PYLON_TOP + 2, cx - 6 : cx + 7] = True
    return pylons, shade & pylons, chords, lattice, hangers, deck


# ---- the city ----


def sydney_tower() -> np.ndarray:
    """A thin shaft with the turret near its top and a spire above."""
    m = blank()
    cx = TOWER_X
    m[93:100, cx] = True  # the spire
    m[100:102, cx - 1 : cx + 2] = True
    m[102:103, cx - 3 : cx + 4] = True  # the turret
    m[103:106, cx - 3 : cx + 4] = True
    m[106:107, cx - 2 : cx + 3] = True
    m[107:SHORE, cx - 1 : cx + 1] = True  # the shaft
    return m


def city():
    """The city behind: the business district round Sydney Tower, low again by the bridge, North Sydney beyond it."""
    far, near = Skyline(), Skyline()
    for x0, w, top in [
        (118, 8, 126), (126, 7, 121), (133, 6, 117), (139, 8, 123), (147, 6, 114), (160, 7, 118), (167, 6, 124),
        (173, 8, 120), (181, 6, 126), (187, 9, 122), (196, 7, 127), (203, 8, 124), (211, 6, 129), (217, 9, 126), (226, 8, 130), (234, 6, 132),
    ]:
        far.box(x0, w, top)
    far.blocks(0, 118, 134, 124, seed=61, widths=(5, 11), gap=(0, 2))
    far.blocks(372, 420, 136, 128, seed=62, widths=(5, 9), gap=(0, 2))
    for x0, w, top in [(420, 7, 124), (427, 6, 119), (433, 8, 122), (441, 6, 126), (447, 7, 121), (454, 8, 127)]:
        far.box(x0, w, top)
    far.blocks(462, W, 136, 128, seed=63, widths=(5, 10), gap=(0, 2))
    # The near shore: the gardens and the point at the left, the north shore at the right.
    near.blocks(0, PODIUM[0], 143, 139, seed=64, widths=(4, 9), gap=(0, 1))
    near.blocks(PYLON_N + 6, W, 143, 138, seed=65, widths=(4, 10), gap=(0, 1))
    return far.tops, near.tops


def ferry(p: Picture, hull: str, cabin: str, lamp=None):
    """A harbour ferry, double-ended: a long low hull, a cabin deck, a wheelhouse at each end and a mast between."""
    x, y = FERRY
    p.dashes([(x + 8, y, 1), (x + 3, y + 1, 2), (x + 13, y + 1, 2), (x + 2, y + 2, 14)], cabin)
    p.dashes([(x, y + 3, 18), (x + 1, y + 4, 16)], hull)
    if lamp:
        p.dashes([(x + 4, y + 2, 1), (x + 7, y + 2, 1), (x + 10, y + 2, 1), (x + 13, y + 2, 1)], lamp)


# ---- the two lights ----


def day() -> Picture:
    """Light windows: cream sails and a pale steel arch over a soft harbour blue."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()

    rise = np.clip((y - 74) / (140 - 74), 0, 1) ** 1.8
    drift = 0.88 + 0.24 * noise(W, 7, 3, 8.0)[None, :]
    p.tone(rise * 1.6 * drift, ["#e0ecef", "#cfe4ea"])

    far, near = city()
    p.ridge(far, "#d4d9ea")
    paint(p, sydney_tower(), "#bcc3dc")
    p.dashes([(TOWER_X - 3, 103, 7), (TOWER_X - 3, 105, 7)], "#ecd29a")

    pylons, shade, chords, lattice, hangers, deck = arch()
    paint(p, hangers, "#cfd7e4")
    paint(p, lattice, p.level("#aab6cd", 7))
    paint(p, chords, "#a7b4cc")
    paint(p, deck, "#9fadc6")
    paint(p, pylons, "#ddd5c6")
    paint(p, shade, "#d0c7b6")

    p.ridge(near, "#b5d0c2")
    far_shells, far_ridges, near_shells, near_ridges, podium = opera_house()
    paint(p, podium, "#e8cfc0")
    paint(p, far_shells, "#ece4d0")
    paint(p, far_ridges, "#d9ccb0")
    paint(p, near_shells, "#fdfaf1")
    paint(p, near_ridges, "#dacfb6")

    p.rect(0, SHORE, W, H - SHORE, "#ecf1f0")
    rng = np.random.default_rng(5)
    under = lambda col: math.exp(-(((col - 210) / 14) ** 2))  # the sails lying on the water
    for runs, colour in strokes(rng, under, ["#bfd6e3", "#f3ead2"], base=0.24, gain=0.6):
        p.dashes(runs, colour)
    ferry(p, "#8fbf9f", "#f6e7b8")
    return p


def night() -> Picture:
    """Dark windows: the sails a dim blue-grey, small warm lights along the bridge and in the city."""
    p = Picture("night", "#0b0c14")
    x, y = grid()
    rng = np.random.default_rng(9)
    stars(p, 36, ("#232a48", "#717cae"), seed=8)

    rise = np.clip((y - 84) / (142 - 84), 0, 1) ** 1.6
    drift = 0.88 + 0.24 * noise(W, 8, 3, 8.0)[None, :]
    p.tone(rise * 2.0 * drift, ["#13162c", "#1d2140", "#2a2747"])

    far, near = city()
    p.ridge(far, "#151a33")
    lights(p, far, [("#8a6a3c", 3), ("#d9ad5f", 1), ("#6f8fb0", 1)], chance=0.2, seed=71)
    paint(p, sydney_tower(), "#1d2343")
    p.dashes([(TOWER_X - 3, 104, 7)], "#a5803f")
    p.dashes([(TOWER_X, 93, 1)], "#e5484d")

    pylons, shade, chords, lattice, hangers, deck = arch()
    paint(p, hangers, "#1c2240")
    paint(p, lattice, p.level("#29304f", 7))
    paint(p, chords, "#2d355a")
    paint(p, deck, "#1a1f38")
    paint(p, pylons, "#22253a")
    paint(p, shade, "#1a1c2e")
    p.dashes([(cx, int(round(chord(cx))), 1) for cx in range(PYLON_S + 10, PYLON_N - 9, 5)], "#7a6238")
    p.dashes([(cx, DECK, 1) for cx in range(198, 430, 4)], "#e0a24c")

    p.ridge(near, "#07080e")
    lights(p, near, [("#c99448", 2), ("#f0c674", 1)], chance=0.25, seed=72)
    far_shells, far_ridges, near_shells, near_ridges, podium = opera_house()
    paint(p, podium, "#1a1a2a")
    paint(p, far_shells, "#2a3146")
    paint(p, far_ridges, "#20263a")
    paint(p, near_shells, "#3a425a")
    paint(p, near_ridges, "#262c41")
    p.dashes([(cx, PODIUM[2] + 2, 1) for cx in range(PODIUM[0] + 8, PODIUM[1] - 1, 3)], "#d9a85a")

    p.rect(0, SHORE, W, H - SHORE, "#07080f")
    lamp = lambda col: 0.5 if 196 < col < 430 else 0.15
    for runs, colour in strokes(rng, lamp, ["#1a2140", "#8a6232"], base=0.1, gain=0.35):
        p.dashes(runs, colour)
    ferry(p, "#141a2c", "#262c44", "#f0c674")
    return p
