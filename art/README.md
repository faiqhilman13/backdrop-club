# The drawing kit

The gallery's starter themes are drawn in Python with `dither.py`: chunky ordered-dither pixel art, one picture for light mode and one for dark, in a single SVG. You don't need any of this to submit a theme; it's here so the starter scenes can be redrawn and new ones added in the same style.

Needs Python 3 with numpy (and Pillow plus Chrome for `look.py`).

## A scene

One file, `art/scene_<name>.py`, giving:

| Name | What |
| --- | --- |
| `ID` | the theme's id, lower-case words joined by dashes (`san-francisco`) |
| `NAME` | its name (`San Francisco`) |
| `DESCRIPTION` | one plain sentence about what's in it, under 200 characters |
| `TAGS` | up to five lower-case tags: `city` and `skyline`, or `landscape`, plus place and feature words |
| `day()` | returns `Picture("day", "#f5f2ea")`, the light-mode picture |
| `night()` | returns `Picture("night", "#0b0c14")`, the dark-mode picture |

Read `dither.py` for the tools (`Picture.tone` for dithered skies and haze, `Picture.ridge` for silhouettes, `Skyline` for buildings, `range_of` for mountains, `lights`, `stars`, `strokes` for water, `crescent`, `disc`). The six scenes here show them in use: `scene_new_york.py`, `scene_tokyo.py` and `scene_shanghai.py` for cities; `scene_mountain_lake.py`, `scene_desert_mesas.py` and `scene_island_bay.py` for landscapes.

## The rules

The point of a backdrop is that the chat stays easy to read on top of it. These come from real use:

1. **The grid is 512 by 160**, one unit per dither pixel. The window always shows the full height, scaled to fit, and as much of the middle as its shape allows: a 16:10 window shows only x 128 to 384. Put the landmarks between x 140 and 372; the outer parts just carry the scene on for wide windows.
2. **Keep it low.** Nothing above y 60 except, at night, a few dim stars. Between y 60 and 100 only faint haze and the thin tops of the tallest towers, spires or peaks. The scene itself lives in y 100 to 146; water or ground from y 146 (`SHORE`) to 160.
3. **Day is pale.** Every fill in the day picture is a soft pastel that dark text reads on: relative luminance of at least 0.40 (contrast 7:1 or better against `#1f1e1d`).
4. **Night is dark.** Night fills are deep (relative luminance under about 0.05). Bright colours (lit windows, neon, a moon, a sunset glow) are small accents, kept mostly below y 134.
5. **Recognisable.** A landmark should read at a glance as itself: get its proportions and its one or two telltale shapes right, in whole pixels.
6. **Still and small.** No animation. Under 100,000 characters for the whole SVG.

## Making and checking one

```
python3 art/look.py scene_london /tmp/look          # pictures behind a mock window: london_light.png, london_dark.png, london_both.png
python3 art/export.py scene_london                  # writes themes/london/backdrop.svg and theme.json
node tools/build.mjs --render --check --only=london # the gallery's own rules and readability check
```

The readability check needs at least 4.5:1 for chat text in both modes; aim for 6:1 or better.
