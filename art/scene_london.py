"""London: the Thames, with Westminster, the Eye, St Paul's, the Shard and Tower Bridge, in grey-blue haze by day and lit windows by night."""

from __future__ import annotations

import math

import numpy as np

from dither import H, SHORE, W, Picture, Skyline, grid, lights, noise, stars, strokes

ID = "london"
NAME = "London"
DESCRIPTION = "The Thames with Big Ben and Westminster, the London Eye, St Paul's, the Shard and Tower Bridge."
TAGS = ["city", "skyline", "uk", "thames"]

# Where the landmarks stand, left to right: the centre column of each.
VICTORIA, CENTRAL, BIG_BEN = 150, 174, 200
EYE_X, EYE_Y, EYE_R = 234, 119, 17
ST_PAULS = 282
SHARD, SHARD_TIP = 312, 70
BRIDGE = (346, 374)
# A pale sun between the bridge's towers, under its walkways.
SUN = (360.0, 127.0, 8.0)
# A bus crossing the bridge, and a boat on the river: (first column, first row).
BUS, BOAT = (353, 132), (150, 149)


# ---- shapes of whole pixels ----


def blank() -> np.ndarray:
    return np.zeros((H, W), dtype=bool)


def bar(mask: np.ndarray, cx: int, y: int, width: int, rows: int = 1, on: bool = True):
    """`rows` rows of `width` pixels (odd), centred on column cx, from row y down."""
    mask[y : y + rows, cx - width // 2 : cx - width // 2 + width] = on


def line(mask: np.ndarray, x0: int, y0: int, x1: int, y1: int):
    """A one-pixel line from (x0, y0) to (x1, y1)."""
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x1 > x0 else -1), (1 if y1 > y0 else -1)
    err = dx + dy
    while True:
        mask[y0, x0] = True
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def circle(mask: np.ndarray, cx: int, cy: int, r: int):
    """A one-pixel ring of radius r round the pixel (cx, cy)."""
    x, y, d = r, 0, 1 - r
    while x >= y:
        for a, b in ((x, y), (y, x)):
            for sa in (-1, 1):
                for sb in (-1, 1):
                    mask[cy + sb * b, cx + sa * a] = True
        y += 1
        if d < 0:
            d += 2 * y + 1
        else:
            x -= 1
            d += 2 * (y - x) + 1


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


def tops_of(mask: np.ndarray) -> np.ndarray:
    """The first row of a shape in every column, for `lights`."""
    return np.where(mask.any(axis=0), mask.argmax(axis=0), SHORE)


# ---- the landmarks: the same by day and by night ----


def clock_tower():
    """The Elizabeth Tower: a square shaft, the clock stage a pixel wider each side with its dial,
    the belfry, and the iron spire with a pinnacle at each corner of its foot.
    Returns (stone, spire, dial, shade)."""
    stone, spire, dial, shade = blank(), blank(), blank(), blank()
    cx = BIG_BEN
    bar(spire, cx, 86, 1, 5)  # the finial, 86..90
    bar(spire, cx, 91, 3, 4)  # the upper spire and its lantern, 91..94
    bar(spire, cx, 95, 5, 6)  # the spire's foot, 95..100
    spire[98:101, cx - 3] = spire[98:101, cx + 3] = True  # corner pinnacles
    bar(stone, cx, 101, 7, 6)  # the belfry, 101..106
    bar(stone, cx, 107, 9, 10)  # the clock stage, 107..116
    bar(stone, cx, 117, 7, SHORE - 117)  # the shaft
    for dx in (-2, 0, 2):  # the belfry's openings
        shade[102:106, cx + dx] = True
    shade[107, cx - 4 : cx + 5] = True  # the cornice under the belfry
    shade[116, cx - 4 : cx + 5] = True
    for dx in (-2, 2):  # the shaft's tall panels
        shade[119:142, cx + dx] = True
    for y, w in zip(range(110, 115), (3, 5, 5, 5, 3)):
        bar(dial, cx, y, w)
    return stone, spire, dial, shade


def palace():
    """The Palace of Westminster: a long, low gothic front topped with pinnacles, the steep roofs behind it,
    two pavilions, the Central Tower's spire, and the Victoria Tower at its south end.
    Returns (front, roof, shade)."""
    front, roof, shade = blank(), blank(), blank()
    x0, x1 = 122, BIG_BEN - 3
    front[129:SHORE, x0:x1] = True
    for x in range(x0 + 1, x1, 3):  # the pinnacles along the parapet
        front[127:129, x] = True
    roof[124:129, x0 + 3 : x1 - 2] = True
    for px in (163, 187):  # two pavilions with steep caps and corner pinnacles
        bar(front, px, 123, 5, 6)
        bar(roof, px, 120, 3, 3)
        roof[118:120, px] = True
        front[121:123, px - 2] = front[121:123, px + 2] = True
    # The Central Tower: a lantern and a needle over the middle of the palace.
    bar(roof, CENTRAL, 117, 5, 7)
    bar(roof, CENTRAL, 113, 3, 4)
    roof[107:113, CENTRAL] = True
    # The Victoria Tower: broad and square, corner turrets, a flagpole.
    vx = VICTORIA
    bar(front, vx, 105, 11, SHORE - 105)
    for dx in (-5, -4, 4, 5):
        front[101:105, vx + dx] = True
    front[99:101, vx - 5] = front[99:101, vx + 5] = True
    for dx in (-2, 0, 2):
        front[103:105, vx + dx] = True
    front[95:103, vx] = True
    front[95:97, vx + 1 : vx + 4] = True
    for dx in (-3, 0, 3):  # its tall windows
        shade[108:126, vx + dx] = True
    # The front's bays: a buttress every six columns, and two rows of windows.
    for x in range(x0 + 2, x1 - 1, 6):
        shade[130:SHORE, x] = True
    for x in range(x0 + 4, x1 - 1, 2):
        if (x - x0) % 6 != 2:
            shade[132:134, x] = shade[137:139, x] = True
    return front & ~shade, roof & ~front, shade & front


def eye():
    """The London Eye: a thin ring, its spokes, the capsules round the rim, and the A-frame it leans on.
    Returns (rim, spokes, pods, legs)."""
    rim, spokes, pods, legs = blank(), blank(), blank(), blank()
    cx, cy, r = EYE_X, EYE_Y, EYE_R
    circle(rim, cx, cy, r)
    for k in range(16):
        a = 2 * math.pi * (k + 0.5) / 16
        line(spokes, cx + round(2 * math.cos(a)), cy + round(2 * math.sin(a)), cx + round((r - 1) * math.cos(a)), cy + round((r - 1) * math.sin(a)))
    for k in range(32):
        a = 2 * math.pi * (k + 0.5) / 32
        pods[cy + round((r + 1.6) * math.sin(a)), cx + round((r + 1.6) * math.cos(a))] = True
    line(legs, cx - 1, cy + 1, cx - 10, SHORE - 1)
    line(legs, cx + 1, cy + 1, cx + 10, SHORE - 1)
    bar(legs, cx, cy - 1, 3, 3)
    return rim, spokes & ~rim & ~legs, pods & ~rim, legs


def st_pauls():
    """St Paul's: the dome on its colonnaded drum, the lantern, ball and cross, the nave and the two west towers.
    Returns (stone, dome, dome's shaded side, gold, shade)."""
    stone, dome, gold, shade = blank(), blank(), blank(), blank()
    cx = ST_PAULS
    gold[95:99, cx] = True
    gold[96, cx - 1 : cx + 2] = True
    bar(gold, cx, 99, 3)
    bar(stone, cx, 100, 3, 4)  # the lantern
    bar(stone, cx, 104, 5)
    for y, w in zip(range(105, 114), (5, 9, 11, 13, 13, 15, 15, 15, 15)):
        bar(dome, cx, y, w)
    bar(stone, cx, 114, 17)  # the stone gallery
    bar(stone, cx, 115, 15, 2)
    bar(stone, cx, 117, 19, 7)  # the colonnade
    bar(stone, cx, 124, 21)
    stone[126:SHORE, cx - 24 : cx + 17] = True  # the church below
    for dx in range(-8, 9, 2):
        shade[118:123, cx + dx] = True
    for tx in (cx - 23, cx - 16):  # the west towers: an open stage, a small cupola, a gilt finial
        bar(stone, tx, 115, 5, SHORE - 115)
        bar(stone, tx, 113, 3, 2)
        gold[110:113, tx] = True
        shade[117:121, tx] = True
        shade[124:128, tx] = True
    stone[124:126, cx - 21 : cx - 17] = True  # the portico between them
    cols = np.arange(W)[None, :]
    return stone, dome & (cols <= cx + 1), dome & (cols > cx + 1), gold, shade & stone


def shard():
    """The Shard: a tall, thin glass pyramid, its top breaking into splinters.
    Returns (light face, dark face, light edge, dark edge): the edges are half-inked so the taper reads straight."""
    light, dark, soft_l, soft_d = blank(), blank(), blank(), blank()
    cx, top = SHARD, SHARD_TIP + 6
    for y in range(top, SHORE):
        f = (y - top) / (SHORE - 1 - top)
        half = 1 + 6.4 * f
        whole = int(half)
        split = cx + int(round(2 * f))
        light[y, cx - whole : split + 1] = True
        dark[y, split + 1 : cx + whole + 1] = True
        if half - whole > 0.4:
            soft_l[y, cx - whole - 1] = True
            soft_d[y, cx + whole + 1] = True
    light[SHARD_TIP + 2 : top, cx - 1] = True
    dark[SHARD_TIP : top, cx + 1] = True
    light[top - 2 : top, cx] = True
    return light, dark, soft_l, soft_d


def tower_bridge():
    """Tower Bridge: two gothic towers with corner turrets and steep caps, the high walkways between them,
    the road deck, and the side spans' chains. Returns (stone, steel, shade)."""
    stone, steel, shade = blank(), blank(), blank()
    for tc in BRIDGE:
        bar(stone, tc, 110, 9, SHORE - 110)
        bar(stone, tc, 107, 3, 3)
        stone[104:107, tc] = True
        for dx in (-4, -3, 3, 4):
            stone[107:110, tc + dx] = True
        stone[105:107, tc - 3] = stone[105:107, tc + 3] = True
        bar(stone, tc, 140, 13, SHORE - 140)  # the pier
        for dx in (-2, 0, 2):
            shade[113:131:2, tc + dx] = True
            shade[114:131:2, tc + dx] = True
    a, b = BRIDGE[0] + 5, BRIDGE[1] - 4
    steel[113, a:b] = steel[117, a:b] = True
    for x in range(a, b, 3):
        steel[114:117, x] = True
    steel[136:138, BRIDGE[0] - 22 : BRIDGE[1] + 23] = True
    # The side spans: a chain from each tower down to the deck at the shore.
    for tc, way in ((BRIDGE[0] - 5, -1), (BRIDGE[1] + 5, 1)):
        last = None
        for i in range(0, 16):
            t = i / 15
            y = int(round(113 + 22 * (2 * t - t * t)))
            x = tc + way * i
            if last is not None:
                for yy in range(last + 1, y):
                    steel[yy, x - way] = True
            steel[y, x] = True
            last = y
        end = tc + way * 18  # the abutment on the shore
        bar(stone, end, 129, 5, SHORE - 129)
        bar(stone, end, 127, 3, 2)
        stone[125:127, end] = True
    return stone, steel & ~stone, shade & stone


def outer_left():
    """For wide windows: Battersea Power Station's four white chimneys, and the BT Tower."""
    body, stacks = blank(), blank()
    body[124:SHORE, 50:86] = True
    for x in (52, 58, 78, 84):
        stacks[102:124, x - 1 : x + 2] = True
        stacks[101, x - 1 : x + 2] = True
    bt = 108
    bar(body, bt, 104, 5, SHORE - 104)
    bar(body, bt, 99, 7, 5)
    bar(body, bt, 94, 3, 5)
    body[88:94, bt] = True
    return body, stacks


def outer_right():
    """For wide windows: the Gherkin and the Walkie-Talkie, then Canary Wharf's three towers."""
    m = blank()
    g = 398
    for y, w in zip(range(108, 114), (1, 3, 5, 5, 7, 7)):
        bar(m, g, y, w)
    bar(m, g, 114, 7, SHORE - 114)
    for y in range(104, SHORE):  # the Cheesegrater: a wedge, its west face sloping
        left = 404 + int(round((SHORE - 1 - y) * 8 / 41))
        m[y, left:418] = True
    for y in range(114, SHORE):  # the Walkie-Talkie: wider as it rises
        w = 7 + 2 * int(round(2 * (SHORE - y) / 32))
        bar(m, 428, y, w)
    m[112:114, 425:433] = True
    one = 452
    bar(m, one, 104, 9, SHORE - 104)
    for y, w in zip(range(98, 104), (1, 1, 3, 5, 7, 9)):
        bar(m, one, y, w)
    bar(m, one - 10, 112, 7, SHORE - 112)
    bar(m, one + 10, 112, 7, SHORE - 112)
    return m


def city():
    """The ordinary buildings: a far row behind the landmarks, a middle row of City blocks and spires,
    and a low row of trees and roofs along the water."""
    far, mid, near = Skyline(), Skyline(), Skyline()
    far.box(0, W, 138)
    far.blocks(0, 122, 134, 124, seed=3, widths=(6, 12), gap=(0, 2))
    far.blocks(392, W, 136, 127, seed=4, widths=(6, 12), gap=(0, 2))
    for x0, w, top in [
        (204, 6, 131), (210, 7, 128),  # between the clock tower and the Eye
        (252, 6, 130), (258, 8, 127),
        (300, 6, 129), (322, 6, 131), (329, 7, 130),
    ]:
        far.box(x0, w, top)
    mid.box(0, W, 142)
    for x0, w, top in [
        (204, 8, 136), (212, 5, 138), (250, 9, 135), (262, 7, 133),
        (292, 8, 132), (300, 6, 136), (318, 8, 134),
    ]:
        mid.box(x0, w, top)
    for x, top in ((296, 121), (303, 125), (209, 126)):  # church spires
        mid.box(x - 1, 3, top + 6).spire(x, top)
    mid.blocks(0, 120, 140, 132, seed=13, widths=(5, 10), gap=(3, 10))
    mid.blocks(394, W, 140, 131, seed=14, widths=(5, 10), gap=(3, 10))
    near.box(0, W, 144)
    near.blocks(0, 120, 144, 138, seed=23, widths=(7, 14), gap=(0, 4))
    near.blocks(392, W, 144, 138, seed=24, widths=(7, 14), gap=(0, 4))
    for x0, w, top in [(250, 10, 140), (262, 9, 138), (288, 12, 141), (300, 9, 139)]:
        near.box(x0, w, top)
    return far.tops, mid.tops, near.tops


def bus():
    """A double-decker on the bridge's deck. Returns (body, windows)."""
    body, glass = blank(), blank()
    x, y = BUS
    body[y, x + 1 : x + 7] = True
    body[y + 1 : y + 4, x : x + 7] = True
    for dx in (1, 3, 5):
        glass[y + 1, x + dx] = True
    for dx in (2, 4):
        glass[y + 3, x + dx] = True
    return body & ~glass, glass


def boat():
    """A river boat: a low hull and a long cabin. Returns (hull, cabin, windows)."""
    hull, cabin, glass = blank(), blank(), blank()
    x, y = BOAT
    cabin[y, x + 4 : x + 11] = True
    cabin[y + 1, x + 3 : x + 12] = True
    glass[y + 1, x + 4 : x + 11 : 2] = True
    hull[y + 2, x : x + 15] = True
    hull[y + 3, x + 1 : x + 14] = True
    return hull, cabin & ~glass, glass


def trees() -> np.ndarray:
    """Plane trees along the embankments: small round crowns."""
    m = blank()
    for x in (205, 211, 217, 251, 257, 263, 300, 306, 404, 410, 436):
        for y, w in zip(range(138, 146), (3, 5, 5, 5, 5, 3, 1, 1)):
            bar(m, x, y, w)
    return m


def river(p: Picture, rng, lit, tint, base: float, gain: float):
    """Strokes on the water, each taking the colour of what stands above it, and none across the boat."""
    by: dict[str, list] = {}
    bx, byy = BOAT
    for runs, _ in strokes(rng, lit, [None], base=base, gain=gain):
        for col, row, n in runs:
            if bx - 3 < col + n and col < bx + 18 and byy - 1 <= row <= byy + 4:
                continue
            by.setdefault(tint(col + n // 2, row), []).append((col, row, n))
    for colour, runs in by.items():
        p.dashes(runs, colour)


# ---- the two lights ----


def day() -> Picture:
    """Light windows: pale grey-blue haze, the stone in sand and white, sage trees, a pale sun under Tower Bridge."""
    p = Picture("day", "#f5f2ea")
    x, y = grid()
    sx, sy, sr = SUN

    rise = np.clip((y - 74) / (140 - 74), 0, 1) ** 1.8
    halo = np.exp(-(((x - sx) / 70) ** 2) - ((y - sy) / 40) ** 2)
    drift = 0.88 + 0.24 * noise(W, 21, 3, 8.0)[None, :]
    p.tone(rise * (0.55 + 0.6 * halo) * drift, ["#e8ebf1", "#dce2ec"])

    p.disc(sx, sy, sr, "#fbefd2")
    p.disc(sx, sy, sr, p.level("#f6dcae", 6), rows=(int(sy - 2), int(sy + sr) + 1))

    far, mid, near = city()
    body, stacks = outer_left()
    p.ridge(far, "#e0e4ec")
    paint(p, body | outer_right(), "#d6dce7")
    paint(p, stacks, "#ece6da")

    light, dark, soft_l, soft_d = shard()
    paint(p, light, "#c9d3e3")
    paint(p, soft_l, p.level("#c9d3e3", 8))
    paint(p, dark, "#b3c0d6")
    paint(p, soft_d, p.level("#b3c0d6", 8))

    stone, dome, dome_shade, gold, shade = st_pauls()
    paint(p, stone, "#e3ded2")
    paint(p, shade, "#cfc8b8")
    paint(p, dome, "#ccd2dd")
    paint(p, dome_shade, "#b8c0cf")
    paint(p, gold, "#e6cf98")
    p.ridge(mid, "#d3d8e2")

    rim, spokes, pods, legs = eye()
    paint(p, spokes, "#d0d7e4")
    paint(p, legs | rim, "#a7b4cc")
    paint(p, pods, "#b7c3d8")

    front, roof, pshade = palace()
    paint(p, roof, "#b9c0cf")
    paint(p, front, "#e6dabd")
    paint(p, pshade, "#d0c29f")
    stone, spire, dial, bshade = clock_tower()
    paint(p, spire, "#aab4c8")
    paint(p, stone, "#e2d3ac")
    paint(p, bshade, "#cbb98f")
    paint(p, dial, "#fbf6e8")
    dots(p, [(BIG_BEN, 111), (BIG_BEN, 112)], "#c0ad85")

    stone, steel, bshade = tower_bridge()
    paint(p, stone, "#ddd6c7")
    paint(p, bshade, "#c9c1af")
    paint(p, steel, "#a9bcd8")
    body, glass = bus()
    paint(p, body, "#e6aea8")
    paint(p, glass, "#f7ebe6")

    p.ridge(near, "#c6d0c3")
    paint(p, trees(), "#afc5ab")

    p.rect(0, SHORE, W, H - SHORE, "#eff0ee")
    rng = np.random.default_rng(5)
    under = lambda col, at, wide: math.exp(-(((col - at) / wide) ** 2))
    lit = lambda col: max(under(col, sx, 14), 0.5 * under(col, 170, 40), 0.25)

    def tint(col, row):
        if abs(col - sx) < 10:
            return "#f3d9a6"
        if 120 < col < BIG_BEN + 4:
            return "#e2d4b2"
        return "#cfd8e5" if (col + row) % 3 else "#c4d4c0"

    river(p, rng, lit, tint, base=0.2, gain=0.5)
    hull, cabin, glass = boat()
    paint(p, hull, "#b9c3d3")
    paint(p, cabin, "#ece7dd")
    paint(p, glass, "#c9d2e0")
    return p


def night() -> Picture:
    """Dark windows: a navy sky, the city's glow low over the roofs, warm windows, the clock lit, the Eye a dim ring."""
    p = Picture("night", "#0b0c14")
    x, y = grid()
    stars(p, 34, ("#1f2546", "#5d6796"), seed=6)

    high = 0.3 * np.clip((y - 70) / (104 - 70), 0, 1) ** 1.6
    low = np.clip((y - 104) / (140 - 104), 0, 1) ** 1.2
    glow = (0.65 + 0.4 * np.exp(-(((x - 240) / 150) ** 2))) * (0.86 + 0.28 * noise(W, 22, 3, 8.0)[None, :])
    p.tone(high + 3.0 * glow * low, ["#121734", "#1d2044", "#36294a", "#5e4148"])

    far, mid, near = city()
    body, stacks = outer_left()
    p.ridge(far, "#1a1f3e")
    lights(p, far, [("#5b4630", 1)], chance=0.08, seed=41)
    paint(p, body | outer_right(), "#181d3a")
    paint(p, stacks, "#262c4c")
    dots(p, [(452, 98)], "#d9d4f0")

    light, dark, soft_l, soft_d = shard()
    paint(p, light | soft_l, "#1b2347")
    paint(p, dark | soft_d, "#141a38")
    lights(p, np.maximum(tops_of(light | dark), 104), [("#3e4f86", 2), ("#8a6a40", 1)], chance=0.14, step=(2, 4), seed=42, x0=SHARD - 6, x1=SHARD + 7)
    dots(p, [(SHARD + 1, SHARD_TIP), (SHARD - 1, SHARD_TIP + 2)], "#6d7cc0")

    stone, dome, dome_shade, gold, shade = st_pauls()
    paint(p, stone, "#171c39")
    paint(p, dome, "#262d54")
    paint(p, dome_shade, "#1c2244")
    paint(p, gold, "#7d6a45")
    paint(p, shade, "#5a4a32")
    p.ridge(mid, "#121630")
    lights(p, mid, [("#7a5a34", 2), ("#c99a52", 1)], chance=0.14, seed=43)

    rim, spokes, pods, legs = eye()
    paint(p, spokes, "#191f42")
    paint(p, legs | rim, "#2a3262")
    paint(p, pods & (np.arange(H)[:, None] > EYE_Y + 6), "#c88aa8")
    paint(p, pods & (np.arange(H)[:, None] <= EYE_Y + 6), "#5a5f96")

    front, roof, pshade = palace()
    paint(p, roof, "#10142c")
    paint(p, front, "#1d1d38")
    paint(p, front & (np.arange(H)[:, None] >= 132), p.level("#3a2c32", 6))
    lights(p, np.maximum(tops_of(front), 130), [("#b5803a", 3), ("#e6b45c", 1)], chance=0.3, step=(2, 3), seed=44, x0=122, x1=197)
    dots(p, [(VICTORIA - 3, 112), (VICTORIA + 3, 118), (VICTORIA, 124)], "#7a5a34")
    stone, spire, dial, bshade = clock_tower()
    paint(p, spire, "#141833")
    paint(p, stone, "#1f2040")
    paint(p, dial, "#e9d49a")
    dots(p, [(BIG_BEN, 111), (BIG_BEN, 112)], "#5a4628")
    dots(p, [(BIG_BEN, 103), (BIG_BEN - 2, 104), (BIG_BEN + 2, 104)], "#6b5434")

    stone, steel, bshade = tower_bridge()
    paint(p, stone, "#161a36")
    paint(p, steel, "#252c55")
    dots(p, [(xx, 113) for xx in range(BRIDGE[0] + 5, BRIDGE[1] - 4, 2)] + [(xx, 136) for xx in range(BRIDGE[0] - 20, BRIDGE[1] + 22, 3)], "#d9b36a")
    dots(p, [(tc + dx, yy) for tc in BRIDGE for dx in (-2, 2) for yy in (120, 126)], "#8a6a40")
    body, glass = bus()
    paint(p, body, "#2a1426")
    paint(p, glass, "#d9a650")

    p.ridge(near, "#07080f")
    lights(p, near, [("#b5803a", 2), ("#f0c468", 1)], chance=0.3, seed=45)
    paint(p, trees(), "#0a1210")

    p.rect(0, SHORE, W, H - SHORE, "#07080f")
    rng = np.random.default_rng(9)
    under = lambda col, at, wide: math.exp(-(((col - at) / wide) ** 2))
    lit = lambda col: max(0.8 * under(col, 160, 40), under(col, BIG_BEN, 6), 0.7 * under(col, 360, 24), 0.18)

    def tint(col, row):
        if 120 < col < BIG_BEN + 4 or abs(col - 360) < 22:
            return "#9a6a32" if (col + row) % 4 else "#d9a650"
        if abs(col - EYE_X) < 14:
            return "#6a3f62"
        return "#1a2142"

    river(p, rng, lit, tint, base=0.12, gain=0.45)
    hull, cabin, glass = boat()
    paint(p, hull | cabin, "#141a33")
    paint(p, glass, "#d9a650")
    return p
