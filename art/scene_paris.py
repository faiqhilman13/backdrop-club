"""Paris: the Eiffel Tower over Haussmann roofs and the Seine, Sacré-Cœur on its hill, in blush pastels by day and indigo by night."""

from __future__ import annotations

import math

import numpy as np

from dither import H, SHORE, W, Picture, grid, noise, stars, strokes

ID = "paris"
NAME = "Paris"
DESCRIPTION = "The Eiffel Tower over zinc rooftops and the Seine, with Sacré-Cœur on its hill and a bridge across the river."
TAGS = ["city", "skyline", "france", "eiffel-tower"]

# The tower: its centre column, the tip of its antenna, the row its feet stand on, and its three platforms.
EIFFEL, TIP, FOOT = 212, 76, 138
THIRD, SECOND, FIRST = 85, 116, 127
# Sacré-Cœur on Montmartre: the basilica's centre column and the hill's top row.
SACRE, HILL_TOP = 338, 126
# The bridge, from one pair of gilt pillars to the other.
BRIDGE = (132, 188)
SUN = (282.0, 124.0, 10.0)
# A bateau-mouche on the river: (first column, first row).
BOAT = (338, 148)


# ---- shapes of whole pixels ----


def blank() -> np.ndarray:
    return np.zeros((H, W), dtype=bool)


def bar(mask: np.ndarray, cx: int, y: int, width: int, rows: int = 1, on: bool = True):
    """`rows` rows of `width` pixels (odd), centred on column cx, from row y down."""
    mask[y : y + rows, cx - width // 2 : cx - width // 2 + width] = on


def paint(p: Picture, mask: np.ndarray, fill: str):
    """Any shape of whole pixels, as one path: each run of a row, carried down the rows it repeats on."""
    open_boxes: dict[tuple[int, int], int] = {}
    d = ""
    for row in range(H + 1):
        runs = set()
        if row < H and mask[row].any():
            edge = np.flatnonzero(np.diff(np.concatenate(([0], mask[row].astype(np.int8), [0]))))
            runs = {(int(a), int(b - a)) for a, b in zip(edge[::2], edge[1::2])}
        for run in sorted(r for r in open_boxes if r not in runs):
            top = open_boxes.pop(run)
            d += f"M{run[0]} {top}h{run[1]}v{row - top}h-{run[1]}z"
        for run in runs:
            open_boxes.setdefault(run, row)
    if d:
        p.body.append(f'<path fill="{fill}" d="{d}"/>')


def dots(p: Picture, points, fill: str):
    p.dashes([(int(x), int(y), 1) for x, y in points], fill)


def grow(mask: np.ndarray) -> np.ndarray:
    """The shape and a one-pixel ring round it: for outlines."""
    out = mask.copy()
    out[1:] |= mask[:-1]
    out[:-1] |= mask[1:]
    out[:, 1:] |= mask[:, :-1]
    out[:, :-1] |= mask[:, 1:]
    return out


ROWS = np.arange(H)[:, None]
COLS = np.arange(W)[None, :]


# ---- the Eiffel Tower ----


def eiffel():
    """The tower, row by row from its real proportions (about 5.3 m a pixel): legs splayed round the great
    arch, the first platform at 57 m, the legs closing to the second at 116 m, one slender shaft to the top
    platform at 276 m, then the top and the antenna. Only the legs below the first platform are drawn as
    open ironwork; above them the tower is one calm shape, so nothing busy sits behind the chat.

    Returns (body, girders, lattice, soft): the calm fill of the shaft and the upper legs; the platforms,
    the edges, the top and the arch; the open lattice of the lower legs (half-inked); and the half-pixel
    edges down there that keep their curve smooth."""
    body, girders, lattice, soft = blank(), blank(), blank(), blank()
    cx = EIFFEL

    def span(y, outer, inner=0.0, ironwork=False):
        """One row: everything within `outer` of the centre, less an opening within `inner`;
        the outermost pixel each side is a girder. Ironwork rows are lattice with soft edges."""
        whole = int(outer) if ironwork else int(outer + 0.5)
        left, right = cx - whole, cx + whole
        (lattice if ironwork else body)[y, left : right + 1] = True
        girders[y, left] = girders[y, right] = True
        if ironwork and outer - whole > 0.45:
            soft[y, left - 1] = soft[y, right + 1] = True
        hole = int(round(inner))
        if hole > 0:
            for m in (body, lattice, girders):
                m[y, cx - hole + 1 : cx + hole] = False
            girders[y, cx - hole] = girders[y, cx + hole] = True

    girders[TIP:THIRD, cx] = True  # the antenna and the top
    bar(girders, cx, THIRD, 5)  # the top platform, a small ledge
    for y in range(THIRD + 1, SECOND):  # the shaft, widening ever faster toward the second platform
        t = (y - THIRD - 1) / (SECOND - THIRD - 2)
        span(y, 0.8 + 2.6 * t**1.6)
    bar(girders, cx, SECOND, 11)  # the second platform
    bar(girders, cx, SECOND + 1, 9)
    for y in range(SECOND + 2, FIRST):  # four legs, the gap between them closing upward to a point
        t = (y - SECOND - 2) / (FIRST - SECOND - 3)
        span(y, 4.0 + 2.6 * t**1.2, 3.4 * max(0.0, (t - 0.15) / 0.85) ** 0.9)
    bar(girders, cx, FIRST, 17)  # the first platform
    bar(girders, cx, FIRST + 1, 15)
    for y in range(FIRST + 2, FOOT + 1):  # the legs splay out to the feet round the great arch
        t = (y - FIRST - 2) / (FOOT - FIRST - 2)
        rise = (FOOT + 1 - (y + 0.5)) / 9.0
        inner = 7.0 * math.sqrt(max(0.0, 1 - rise * rise)) if rise < 1 else 0.0
        span(y, 6.8 + 4.8 * t**1.4, inner, ironwork=True)
    full = body | girders | lattice
    for y in range(FIRST + 3, FOOT - 2):  # the arch: a solid girder along the top of the opening
        for x in range(cx - 8, cx + 9):
            if not full[y, x] and full[y - 1, x]:
                girders[y - 1, x] = True
    return body & ~girders, girders, lattice & ~girders, soft & ~lattice & ~girders


# ---- Sacré-Cœur and its hill ----


def hill() -> np.ndarray:
    """Montmartre: the first row of hill in every column, a gentle dome."""
    x = np.arange(W) + 0.5
    u = np.clip(np.abs(x - SACRE) / 52.0, 0, 1)
    return np.round(HILL_TOP + (SHORE - HILL_TOP) * u**1.7).astype(int)


def sacre_coeur():
    """The basilica as it looks from below the hill: the tall egg-shaped dome on a colonnaded drum, a small
    dome either side of the porch, and the square bell tower with its own dome behind on the right.
    Each dome is shaded on the side away from the sun. Returns (white, shaded side, openings)."""
    white, side, openings = blank(), blank(), blank()
    cx, base = SACRE, HILL_TOP

    def dome(x, top, widths, drum_w, drum_rows):
        """A dome of the given row widths from row `top`, on a drum; shaded right of its centre."""
        part = blank()
        for i, w in enumerate(widths):
            bar(part, x, top + i, w)
        bar(part, x, top + len(widths), drum_w, drum_rows)
        white[:] |= part
        side[:] |= part & (COLS > x + max(1, widths[-1] // 5))
        return top + len(widths)

    bt = cx + 17  # the bell tower, further back and to the right
    bar(white, bt, base - 18, 5, 18)
    side[base - 18 : base, bt + 2] = True
    openings[base - 17 : base - 13, bt - 1 : bt + 2 : 2] = True
    dome(bt, base - 21, (3, 5, 5), 5, 1)
    white[base - 23 : base - 21, bt] = True
    bar(white, cx, base - 7, 23, 7)  # the porch and the nave
    bar(white, cx, base - 8, 19)
    side[base - 8 : base, cx + 7 : cx + 12] = True
    for dx in (-4, 0, 4):  # its three arches
        openings[base - 3 : base, cx + dx - 1 : cx + dx + 2] = True
        openings[base - 4, cx + dx] = True
    for sx in (cx - 9, cx + 9):  # the small domes
        dome(sx, base - 15, (3, 5, 5), 5, 4)
        white[base - 16, sx] = True
        openings[base - 11 : base - 9, sx] = True
    for tx in (cx - 12, cx + 12):  # the corner turrets
        white[base - 11 : base - 8, tx] = True
    drum = dome(cx, base - 22, (3, 5, 7, 9, 9, 9), 9, 8)  # the great dome and its drum
    bar(white, cx, drum, 11)  # the ring under the dome
    for dx in (-3, -1, 1, 3):  # the drum's colonnade
        openings[drum + 2 : drum + 6, cx + dx] = True
    bar(white, cx, base - 24, 3, 2)  # the lantern
    white[base - 26 : base - 24, cx] = True
    return white, side & white, openings & white


def montmartre(tops: np.ndarray):
    """Houses and trees on the hill's slopes. Returns (houses, roofs, trees)."""
    rng = np.random.default_rng(14)
    houses, roofs, trees = blank(), blank(), blank()
    for x0 in range(SACRE - 50, SACRE + 50, 6):
        if abs(x0 + 3 - SACRE) < 16:
            continue
        ground = int(tops[min(W - 1, max(0, x0 + 3))])
        if rng.random() < 0.55:
            h = int(rng.integers(4, 7))
            houses[ground - h + 2 : SHORE, x0 : x0 + 5] = True
            roofs[ground - h + 1, x0 + 1 : x0 + 4] = True
            roofs[ground - h + 2, x0 : x0 + 5] = True
        else:
            for y, w in zip(range(ground - 3, ground + 3), (3, 5, 5, 5, 3, 1)):
                bar(trees, x0 + 3, y, w)
    return houses, roofs & ~houses, trees


# ---- the city ----


def haussmann(spans, seed: int):
    """Terraces of Haussmann blocks: cream stone, a zinc mansard with dormers, chimney stacks
    with their pots at the party walls, iron balconies at the second and fifth floors.
    `spans` are (x0, x1, lowest cornice row, highest cornice row).
    Returns (facade, roof, stacks, pots, rails, windows, dormers): masks, and lists of points."""
    rng = np.random.default_rng(seed)
    facade, roof, stacks, pots, rails = blank(), blank(), blank(), blank(), blank()
    windows, dormers = [], []
    for x0, x1, low, high in spans:
        x = x0
        while x1 - x >= 7:
            w = min(int(rng.integers(11, 19)), x1 - x)
            if x1 - x - w < 7:
                w = x1 - x
            c = int(rng.integers(high, low + 1))
            facade[c:SHORE, x : x + w] = True
            roof[c - 4, x + 1 : x + w - 1] = True
            roof[c - 3 : c, x : x + w] = True
            for dx in range(2, w - 1, 3):
                dormers.append((x + dx, c - 3))
            for sx in (x, x + w - 2):
                stacks[c - 7 : c - 4, sx : sx + 2] = True
                pots[c - 8, sx] = True
                if rng.random() < 0.5:
                    pots[c - 8, sx + 1] = True
            if w > 14 and rng.random() < 0.6:
                mx = x + w // 2
                stacks[c - 6 : c - 4, mx : mx + 2] = True
                pots[c - 7, mx] = True
            rails[c + 3, x : x + w] = True
            rails[c + 9, x : x + w] = True
            for wy in range(c + 1, SHORE - 2, 3):
                for wx in range(x + 1, x + w - 1, 2):
                    windows.append((wx, wy))
            x += w
    return facade, roof, stacks & ~roof, pots, rails & facade, windows, dormers


def far_city() -> np.ndarray:
    """Distant roofs behind everything, low round the tower so the sky shows through its arch."""
    tops = np.full(W, 140)
    rng = np.random.default_rng(4)
    x = 0
    while x < W:
        w = int(rng.integers(6, 14))
        near_tower = abs(x + w / 2 - EIFFEL) < 22
        tops[x : x + w] = int(rng.integers(136, 141)) if near_tower else int(rng.integers(124, 133))
        x += w
    return tops


def bridge():
    """A bridge like the Pont Alexandre III: a low steel arch, a parapet with lamps,
    and a tall pillar at each end crowned with a gilt figure. Returns (stone, steel, gold, lamps)."""
    stone, steel, gold = blank(), blank(), blank()
    a, b = BRIDGE
    mid, half = (a + b) / 2, (b - a) / 2 - 7
    for x in range(a, b + 1):
        u = (x + 0.5 - mid) / half
        bottom = 147 if abs(u) >= 1 else int(round(146.5 - 4.5 * (1 - u * u)))
        steel[139:bottom, x] = True
    steel[138, a : b + 1] = True
    for px in (a + 2, b - 2):
        bar(stone, px, 124, 3, 23)
        bar(stone, px, 123, 5)
        bar(gold, px, 119, 3, 3)
        gold[117:119, px] = True
        gold[120, px - 2] = gold[120, px + 2] = True
    lamps = [(x, 134) for x in range(a + 9, b - 6, 8)]
    for x, y in lamps:
        stone[y + 1 : 138, x] = True
    return stone, steel & ~stone, gold, lamps


def bateau():
    """A bateau-mouche: a long low hull, a glass cabin along it, a small wheelhouse at the bow.
    Returns (hull, glass, frames)."""
    hull, glass = blank(), blank()
    x, y = BOAT
    glass[y, x + 5 : x + 19] = True
    glass[y + 1, x + 4 : x + 20] = True
    hull[y - 1 : y + 2, x + 20 : x + 22] = True
    hull[y + 2, x : x + 24] = True
    hull[y + 3, x + 1 : x + 23] = True
    frames = blank()
    frames[y : y + 2, x + 6 : x + 19 : 3] = True
    return hull, glass & ~frames, frames & glass


def trees() -> np.ndarray:
    """Plane trees on the quais and the Champ de Mars."""
    m = blank()
    for x, top in [(192, 134), (196, 137), (228, 137), (232, 134), (238, 137), (126, 137), (120, 136), (258, 138), (476, 138)]:
        for y, w in zip(range(top, top + 8), (3, 5, 7, 7, 5, 3, 1, 1)):
            bar(m, x, y, w)
    return m


def landmarks_outer():
    """For wide windows: the Arc de Triomphe on the left; Notre-Dame's two square towers, its rose window
    and its spire on the right. Returns (stone, shade): the arch itself is left open."""
    stone, arch, shade = blank(), blank(), blank()
    ax = 84
    bar(stone, ax, 124, 21, SHORE - 124)
    bar(stone, ax, 122, 23, 2)
    for y, w in zip(range(131, SHORE), (1, 3, 5, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7)):
        bar(arch, ax, y, w)
    shade[126, ax - 9 : ax + 10] = True
    nd = 444
    for tx in (nd - 8, nd + 8):
        bar(stone, tx, 113, 7, SHORE - 113)
        stone[111:113, tx - 3] = stone[111:113, tx + 3] = True
        shade[116:122, tx - 1 : tx + 2] = True
    bar(stone, nd, 120, 9, SHORE - 120)
    bar(stone, nd, 118, 5, 2)
    bar(shade, nd, 123, 3, 3)
    bar(shade, nd, 124, 5)
    bar(stone, nd + 24, 126, 23, SHORE - 126)
    stone[103:126, nd + 26] = True
    bar(stone, nd + 26, 117, 3, 9)
    shade[130:140:3, nd + 14 : nd + 36 : 3] = True
    return stone & ~arch, shade & stone & ~arch


# ---- the two lights ----


def river(p: Picture, rng, lit, tint, base: float, gain: float):
    """Strokes on the water, each taking the colour of what stands above it, and none across the boat."""
    by: dict[str, list] = {}
    bx, byy = BOAT
    for runs, _ in strokes(rng, lit, [None], base=base, gain=gain):
        for col, row, n in runs:
            if bx - 3 < col + n and col < bx + 27 and byy - 2 <= row <= byy + 4:
                continue
            by.setdefault(tint(col + n // 2, row), []).append((col, row, n))
    for colour, runs in by.items():
        p.dashes(runs, colour)


def city_masks():
    """The terraces, with gaps for the tower's feet and for the Arc de Triomphe and Notre-Dame."""
    return haussmann([(0, 68, 134, 128), (101, 196, 136, 129), (229, 302, 136, 128), (302, 392, 140, 134), (392, 424, 136, 129), (474, W, 136, 128)], seed=7)


def day() -> Picture:
    """Light windows: blush and cream haze round a low pale sun, cream stone and zinc-blue roofs, Sacré-Cœur white on its green hill."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()
    sx, sy, sr = SUN

    rise = np.clip((y - 72) / (140 - 72), 0, 1) ** 1.8
    halo = np.exp(-(((x - sx) / 90) ** 2) - ((y - sy) / 46) ** 2)
    drift = 0.88 + 0.24 * noise(W, 31, 3, 8.0)[None, :]
    p.tone(rise * (0.45 + 1.0 * halo) * drift, ["#f9e8dc", "#f5d6cb"])

    p.disc(sx, sy, sr, "#fbe3d4")
    p.disc(sx, sy, sr, p.level("#f6c4b4", 5), rows=(int(sy - 3), int(sy + sr) + 1))

    p.ridge(far_city(), "#efe1db")

    tops = hill()
    p.ridge(tops, "#d6e0cc")
    houses, hroofs, htrees = montmartre(tops)
    paint(p, htrees, "#c3d3b9")
    paint(p, houses, "#f2e7d6")
    paint(p, hroofs, "#c5cfdc")
    white, side, openings = sacre_coeur()
    paint(p, grow(white) & ~white & (ROWS < HILL_TOP - 1), "#e6dfe8")
    paint(p, white, "#fffbf4")
    paint(p, side, "#ebe5ef")
    paint(p, openings, "#d9d1e0")

    body, girders, lattice, soft = eiffel()
    paint(p, body, "#e9cec6")
    paint(p, lattice | soft, "#efdcd5")
    paint(p, lattice, p.level("#d9b0a6", 8))
    paint(p, soft, p.level("#d9b0a6", 4))
    paint(p, girders, "#d5a99f")

    facade, roof, stacks, pots, rails, windows, dormers = city_masks()
    paint(p, facade, "#f3e8d5")
    dots(p, windows, "#e6d8c0")
    paint(p, rails, "#c6cdd9")
    paint(p, roof, "#bcc8d9")
    dots(p, dormers, "#e8edf3")
    paint(p, stacks, "#e9ddce")
    paint(p, pots, "#e9b8a6")
    stone, shade = landmarks_outer()
    paint(p, stone, "#eee4d3")
    paint(p, shade, "#dccfba")

    paint(p, trees(), "#bfd2b7")
    p.rect(EIFFEL - 20, FOOT + 1, 41, 4, "#ece5d2")
    p.rect(0, 143, W, 3, "#ece2d0")

    p.rect(0, SHORE, W, H - SHORE, "#f3eee8")
    rng = np.random.default_rng(5)
    under = lambda col, at, wide: math.exp(-(((col - at) / wide) ** 2))
    lit = lambda col: max(under(col, sx, 16), 0.7 * under(col, EIFFEL, 10), 0.25)

    def tint(col, row):
        if abs(col - sx) < 12:
            return "#f4c3b3"
        if abs(col - EIFFEL) < 9:
            return "#dcb6ab"
        return "#c3cfdf" if (col + row) % 3 else "#f0d3c8"

    river(p, rng, lit, tint, base=0.2, gain=0.5)
    hull, glass, frames = bateau()
    paint(p, hull, "#c3cbdb")
    paint(p, glass, "#e6ecf3")
    paint(p, frames, "#ccd4e2")

    stone, steel, gold, lamps = bridge()
    paint(p, steel, "#c4cddd")
    paint(p, stone, "#efe3cf")
    paint(p, gold, "#eccf91")
    dots(p, lamps, "#e2c58e")
    return p


def night() -> Picture:
    """Dark windows: deep indigo, the tower a dark lattice with a few gold lights low on it, warm windows below."""
    p = Picture("night", "#0b0c14")
    x, y = grid()
    stars(p, 36, ("#25224a", "#6b64a6"), seed=8)

    high = 0.3 * np.clip((y - 72) / (106 - 72), 0, 1) ** 1.6
    low = np.clip((y - 106) / (140 - 106), 0, 1) ** 1.2
    glow = (0.65 + 0.4 * np.exp(-(((x - 250) / 150) ** 2))) * (0.86 + 0.28 * noise(W, 32, 3, 8.0)[None, :])
    p.tone(high + 3.0 * glow * low, ["#15133a", "#211a4b", "#3a2257", "#5e3058"])

    p.ridge(far_city(), "#17163a")

    tops = hill()
    p.ridge(tops, "#111a26")
    houses, hroofs, htrees = montmartre(tops)
    paint(p, htrees, "#0c1418")
    paint(p, houses, "#15152c")
    paint(p, hroofs, "#1c2142")
    white, side, openings = sacre_coeur()
    paint(p, white, "#30325a")
    paint(p, side, "#25274b")
    paint(p, openings, "#6b5236")

    body, girders, lattice, soft = eiffel()
    paint(p, body, "#1a1733")
    paint(p, lattice | soft, "#16132e")
    paint(p, lattice, p.level("#2b2452", 8))
    paint(p, girders, "#211c40")
    cx = EIFFEL
    shape = body | girders | lattice
    edge = lambda yy: [int(np.flatnonzero(shape[yy])[i]) for i in (0, -1)]
    bright = [(cx + dx, FIRST) for dx in range(-8, 9, 2)] + [(xx, yy) for yy in range(FIRST + 4, FOOT + 1, 3) for xx in edge(yy)]
    dim = [(cx + dx, SECOND) for dx in (-4, 0, 4)] + [(xx, yy) for yy in (95, 104, 111, 121) for xx in edge(yy)]
    dots(p, dim, "#7a5d34")
    dots(p, bright, "#e3b860")
    dots(p, [(cx, TIP)], "#c9a35a")

    facade, roof, stacks, pots, rails, windows, dormers = city_masks()
    paint(p, facade, "#100f22")
    paint(p, roof, "#1a1d3c")
    paint(p, stacks | pots, "#1a1d3c")
    stone, shade = landmarks_outer()
    paint(p, stone, "#15142c")
    paint(p, shade, "#6b5232")
    rng = np.random.default_rng(23)
    lit_w = [w for w in windows if rng.random() < 0.3]
    warm = [w for w in lit_w if rng.random() < 0.75]
    dots(p, [w for w in lit_w if w not in warm and w[1] >= 128], "#f2c66a")
    dots(p, warm, "#b5803a")
    dots(p, [d for d in dormers if rng.random() < 0.25], "#8a6a3e")

    paint(p, trees(), "#0a1214")
    p.rect(EIFFEL - 20, FOOT + 1, 41, 4, "#0f0e20")
    p.rect(0, 143, W, 3, "#0d0d1c")

    p.rect(0, SHORE, W, H - SHORE, "#07080f")
    rng = np.random.default_rng(9)
    under = lambda col, at, wide: math.exp(-(((col - at) / wide) ** 2))
    lit = lambda col: max(under(col, EIFFEL, 14), 0.7 * under(col, 159, 30), 0.2)

    def tint(col, row):
        if abs(col - EIFFEL) < 13 or 128 < col < 190:
            return "#a0702e" if (col + row) % 4 else "#e0b25a"
        return "#1d1d48" if (col + row) % 3 else "#3a2450"

    river(p, rng, lit, tint, base=0.12, gain=0.45)
    hull, glass, frames = bateau()
    paint(p, hull | frames, "#121530")
    paint(p, glass, p.level("#d9a650", 8))

    stone, steel, gold, lamps = bridge()
    paint(p, steel, "#121530")
    paint(p, stone, "#191a36")
    paint(p, gold, "#8a6a3a")
    dots(p, lamps, "#f0c468")
    return p
