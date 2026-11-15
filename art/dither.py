#!/usr/bin/env python3
"""The drawing kit every scene shares: chunky ordered dither on a pixel grid.

A scene is two pictures, one for a light window and one for a dark one. Each
is drawn on a grid of 512 x 160 dither pixels, one SVG unit each. A window
shows the grid's full height and as much of its middle as the window's shape
allows (256 pixels across for a 16:10 window), so what matters goes in the
middle half and the outer quarters only carry the scene on for wide windows.

A tone is dithered the way a one-bit game does it: the 4 x 4 threshold matrix
is laid over the grid, and a pixel is inked where the tone there beats its
threshold. In the SVG that is one pattern per threshold (a single pixel in its
place in the tile) filling the region where the tone beats it.
"""

from __future__ import annotations

import math

import numpy as np

# Twice as wide as the widest window needs: the picture is scaled to the window's height, so its art
# always fills the same share of it, and the sides are simply cut to fit.
W, H = 512, 160
MID = W / 2
TILE = 4
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
# Where each threshold's pixel sits in the tile: threshold -> (x, y).
PLACE = {BAYER[y][x]: (x, y) for y in range(TILE) for x in range(TILE)}
# The water's surface, and so the foot of every tone above it.
SHORE = 146


def noise(n: int, seed: int, octaves=4, base=3.0, gain=0.5) -> np.ndarray:
    """Fractal noise along a line: n samples, 0 to 1."""
    rng = np.random.default_rng(seed)
    x = np.linspace(0.0, 1.0, n)
    y = np.zeros(n)
    amp, freq, total = 1.0, base, 0.0
    for _ in range(octaves):
        knots = rng.random(int(freq) + 3)
        xi = x * freq
        i = np.floor(xi).astype(int)
        f = xi - i
        f = f * f * (3 - 2 * f)
        y += amp * (knots[i] * (1 - f) + knots[i + 1] * f)
        total += amp
        amp *= gain
        freq *= 2.0
    y /= total
    return (y - y.min()) / max(1e-9, y.max() - y.min())


class Picture:
    def __init__(self, name: str, page: str):
        self.name = name
        self.page = page
        self.defs: list[str] = []
        self.body: list[str] = []
        self.inks = 0

    # ---- dithered tone ----

    def tone(self, field: np.ndarray, inks: list[str], foot: int = SHORE):
        """Dithers a tone field (H x W, 0 up to len(inks)) down to row `foot`.

        Each whole step of tone is one ink laid solid; the fraction above it is
        the next ink's dots. The tone must not fall as it nears the foot, so the
        region a threshold inks is everything under one staircase."""
        field = np.maximum.accumulate(field[:foot], axis=0)
        rows = foot // TILE
        for k, colour in enumerate(inks):
            layer = np.clip(field - k, 0.0, 1.0)
            name = f"{self.name[0]}{self.inks}"
            self.inks += 1
            # Solid first, so that full tone is one flat fill with no seams in it.
            solid = self._staircase(layer >= 1.0, rows, 0, 0)
            if solid:
                self.body.append(f'<path fill="{colour}" d="{solid}"/>')
            for t in range(TILE * TILE):
                ox, oy = PLACE[t]
                d = self._staircase(layer > (t + 0.5) / (TILE * TILE), rows, ox, oy)
                if not d:
                    continue
                # The tile is shifted so its one pixel sits clear of the tile's edge,
                # and the pixel is a hair oversize so that neighbours leave no gap.
                self.defs.append(
                    f'<pattern id="{name}{t:x}" x="{ox - 1.5}" y="{oy - 1.5}" width="{TILE}" height="{TILE}" patternUnits="userSpaceOnUse">'
                    f'<rect x="1.48" y="1.48" width="1.04" height="1.04" fill="{colour}"/></pattern>'
                )
                self.body.append(f'<path fill="url(#{name}{t:x})" d="{d}"/>')

    def _staircase(self, on: np.ndarray, rows: int, ox: int, oy: int) -> str:
        """The region under the first inked tile of each tile column, as one path."""
        cols = W // TILE
        tops = []
        for i in range(cols):
            column = on[oy::TILE, i * TILE + ox][:rows]
            hit = np.flatnonzero(column)
            tops.append(int(hit[0]) if hit.size else rows)
        if all(top >= rows for top in tops):
            return ""
        foot = rows * TILE
        d = f"M0 {foot}"
        last = None
        for i, top in enumerate(tops):
            if top != last:
                d += f"V{top * TILE}"
                last = top
            if i == cols - 1 or tops[i + 1] != top:
                d += f"H{(i + 1) * TILE}"
        return d + f"V{foot}z"

    def level(self, colour: str, level: int) -> str:
        """A pattern holding every pixel whose threshold is under `level`, for filling a shape."""
        name = f"{self.name[0]}L{len(self.defs):x}"
        squares = "".join(f"M{x} {y}h1v1h-1z" for t in range(level) for x, y in [PLACE[t]])
        self.defs.append(
            f'<pattern id="{name}" width="{TILE}" height="{TILE}" patternUnits="userSpaceOnUse"><path fill="{colour}" d="{squares}"/></pattern>'
        )
        return f"url(#{name})"

    # ---- shapes on the pixel grid ----

    def ridge(self, tops: np.ndarray, fill: str, foot: int = SHORE):
        """A skyline as a staircase: tops[x] is the first row of land in column x."""
        d = f"M0 {foot}"
        last = None
        for x in range(W):
            top = int(tops[x])
            if top != last:
                d += f"V{top}"
                last = top
            if x == W - 1 or int(tops[x + 1]) != top:
                d += f"H{x + 1}"
        self.body.append(f'<path fill="{fill}" d="{d}V{foot}z"/>')

    def disc(self, cx: float, cy: float, r: float, fill: str, rows=None):
        """A circle of whole pixels, or just its rows y0..y1."""
        d = ""
        y0, y1 = (int(cy - r), int(cy + r) + 1) if rows is None else rows
        for y in range(y0, y1):
            half = r * r - (y + 0.5 - cy) ** 2
            if half <= 0:
                continue
            w = int(round(math.sqrt(half)))
            if w > 0:
                d += f"M{int(cx) - w} {y}h{2 * w}v1h-{2 * w}z"
        if d:
            self.body.append(f'<path fill="{fill}" d="{d}"/>')

    def dashes(self, runs, fill: str):
        """Short horizontal strokes: (x, y, length) each, one pixel tall."""
        d = "".join(f"M{x} {y}h{n}v1h-{n}z" for x, y, n in runs if n > 0)
        if d:
            self.body.append(f'<path fill="{fill}" d="{d}"/>')

    def rect(self, x, y, w, h, fill: str):
        self.body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>')

    def svg_group(self, cls: str) -> str:
        return f'<g class="{cls}"><rect width="{W}" height="{H}" fill="{self.page}"/>{"".join(self.body)}</g>'


def range_of(base: float, peaks, seed: int, rough=1.6, sharp=1.15) -> np.ndarray:
    """A mountain skyline: `peaks` are (x, height, half_width) each, roughened a little.
    The result is the first row of land in every column."""
    x = np.arange(W) + 0.5
    rise = np.zeros(W)
    for at, height, half in peaks:
        rise = np.maximum(rise, height * np.clip(1 - np.abs(x - at) / half, 0, 1) ** sharp)
    rise += rough * (noise(W, seed, 5, 18.0) - 0.5) * 2
    return np.round(base - np.maximum(rise, 0)).astype(int)


def grid():
    y, x = np.mgrid[0:H, 0:W].astype(float)
    return x + 0.5, y + 0.5


def strokes(rng, lit, colours, rows=(SHORE + 1, H), base=0.2, gain=0.5):
    """Broken horizontal strokes on the water, thicker under what is bright above.
    `lit(x)` is 0 to 1; a stroke takes a later colour the brighter its place is."""
    out = [[] for _ in colours]
    for row in range(*rows):
        depth = (row - rows[0]) / max(1, rows[1] - rows[0])
        col = int(rng.integers(0, 10))
        while col < W:
            n = int(rng.integers(2, 6 + int(5 * depth)))
            glow = float(lit(min(W - 1, col + n // 2)))
            if rng.random() < (base + gain * glow) * (1.0 - 0.45 * depth):
                out[min(len(colours) - 1, int(glow * len(colours) * 0.999))].append((col, row, min(n, W - col)))
            col += n + int(rng.integers(3, 9 + int(12 * depth)))
    return zip(out, colours)




class Skyline:
    """A row of buildings as one silhouette: the first row of building in every column.

    Buildings are added in any order; where two overlap the taller wins. Draw it
    with `picture.ridge(skyline.tops, colour)`, light it with `picture.lights`."""

    def __init__(self, foot: int = SHORE):
        self.foot = foot
        self.tops = np.full(W, foot, dtype=int)

    def box(self, x0: int, w: int, top: int):
        a, b = max(0, int(x0)), min(W, int(x0) + int(w))
        if b > a:
            self.tops[a:b] = np.minimum(self.tops[a:b], int(top))
        return self

    def stack(self, cx: int, parts, foot=None):
        """Setbacks: `parts` are (width, height) from the ground up, each centred on cx. Returns the top row."""
        y = self.foot if foot is None else foot
        for w, h in parts:
            y -= h
            self.box(cx - w // 2, w, y)
        return y

    def taper(self, cx: int, w_bottom: int, w_top: int, top: int, bottom: int):
        """A tower that narrows evenly from `bottom` up to `top`."""
        for y in range(int(top), int(bottom)):
            f = (y - top) / max(1, bottom - top)
            w = int(round(w_top + (w_bottom - w_top) * f))
            self.box(cx - w // 2, max(1, w), y)
        return self

    def spire(self, x: int, top: int):
        return self.box(x, 1, top)

    def dome(self, cx: int, r: int, base: int):
        for dx in range(-r, r + 1):
            self.box(cx + dx, 1, base - int(round(math.sqrt(max(0, r * r - dx * dx)))))
        return self

    def blocks(self, x0: int, x1: int, low: int, high: int, seed: int, widths=(5, 14), gap=(0, 3)):
        """Ordinary buildings from x0 to x1, their roofs between rows `high` (tallest) and `low`."""
        rng = np.random.default_rng(seed)
        x = x0
        while x < x1:
            w = int(rng.integers(widths[0], widths[1] + 1))
            self.box(x, min(w, x1 - x), int(rng.integers(high, low + 1)))
            x += w + int(rng.integers(gap[0], gap[1] + 1))
        return self


def lights(picture: Picture, tops: np.ndarray, colours, chance=0.4, step=(2, 3), seed=0, x0=0, x1=W, foot=SHORE, inset=2):
    """Lit windows: single pixels on a grid inside a silhouette, each lit by chance.
    `colours` are (colour, weight) pairs; the commoner the weight the more windows take it."""
    rng = np.random.default_rng(seed)
    names = [c for c, _ in colours]
    weights = np.array([w for _, w in colours], float)
    weights /= weights.sum()
    runs = {c: [] for c in names}
    for x in range(int(x0), int(x1), step[0]):
        top = int(tops[x])
        for y in range(top + inset, foot - 1, step[1]):
            if rng.random() < chance:
                runs[names[int(rng.choice(len(names), p=weights))]].append((x, y, 1))
    for colour in names:
        picture.dashes(runs[colour], colour)


def stars(picture: Picture, count: int, colours, seed=0, depth=70):
    """A few stars, most of them high: `colours` is (dim, bright); one in nine is bright."""
    rng = np.random.default_rng(seed)
    dim, bright = [], []
    for i in range(count):
        sx, sy = int(rng.integers(2, W - 2)), int(abs(rng.triangular(-depth, 0, depth)))
        (bright if i % 9 == 0 else dim).append((sx, sy, 1))
    picture.dashes(dim, colours[0])
    picture.dashes(bright, colours[1])


def crescent(picture: Picture, cx: float, cy: float, r: float, fill: str, bite=0.55):
    """A crescent moon of whole pixels: a disc with another bitten out of its right side."""
    d = ""
    for y in range(int(cy - r), int(cy + r) + 1):
        for x in range(int(cx - r), int(cx + r) + 1):
            inside = (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r
            bitten = (x + 0.5 - cx - r * bite) ** 2 + (y + 0.5 - cy + r * 0.15) ** 2 <= (r * 0.92) ** 2
            if inside and not bitten:
                d += f"M{x} {y}h1v1h-1z"
    if d:
        picture.body.append(f'<path fill="{fill}" d="{d}"/>')


def document(day: Picture, night: Picture) -> str:
    """Both pictures in one SVG: the day one shows unless the window is dark.

    It is scaled to the window's height and pinned to its foot (`xMidYMax slice`),
    where the art is, and says it suits both colour schemes so its frame stays
    see-through."""
    css = (
        ":root{color-scheme:light dark}"
        ".n{display:none}@media (prefers-color-scheme:dark){.d{display:none}.n{display:inline}}"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%" preserveAspectRatio="xMidYMax slice">'
        f"<style>{css}</style><defs>{''.join(day.defs)}{''.join(night.defs)}</defs>"
        f"{day.svg_group('d')}{night.svg_group('n')}</svg>"
    )


def alone(p: Picture) -> str:
    """One picture by itself, to look at."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%" preserveAspectRatio="xMidYMax slice">'
        f"<defs>{''.join(p.defs)}</defs>{p.svg_group('x')}</svg>"
    )
