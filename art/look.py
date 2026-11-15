#!/usr/bin/env python3
"""Draws one scene behind a mock of the app's window and saves pictures of it, to look at.

    python3 tools/look.py scene_tokyo /some/folder

The mock is the window as it really is: two sessions side by side, the chat
text sitting straight on the backdrop with no veil, a status band and the
message box at the foot. It saves <id>_light.png and <id>_dark.png (the whole
window, 2000 x 1300) and <id>_both.png (the lower part of each, light over
dark), and says how large the scene's SVG is.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from dither import alone, document  # noqa: E402

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TEXT = [
    "The picture behind this text is one SVG, scaled to the window's height and pinned to its foot.",
    "Each scene keeps to the lower part of the window. Above it there is only the page colour, so the words stay easy to read.",
    "By day the fills are light pastels that dark text still reads on. By night they are dark, with bright colours kept to small accents.",
    "A window shows the full height of the picture and as much of its middle as the window's shape allows, so the sides are simply cut to fit.",
    "The scenes take turns. A command moves on to the next one, or stays on the one you like.",
]


def page(svg: str, dark: bool) -> str:
    c = (
        dict(text="#ecebe4", muted="#a8a69c", line="#3a3936", box="#30302e", chip="#262624")
        if dark
        else dict(text="#141413", muted="#6c6a63", line="#dedcd1", box="#ffffff", chip="#f0eee6")
    )

    def pane(title: str, n: int) -> str:
        t = TEXT
        return (
            f'<section class="pane"><header><b>{title}</b></header><div class="col"><h4>How it is drawn</h4>'
            f'<ul>{"".join(f"<li>{x}</li>" for x in t[:3])}</ul><p>{t[3]}</p><p>{t[4]}</p><h4>What to look for</h4>'
            f"<p>{t[(n + 1) % 5]} {t[(n + 2) % 5]}</p><p>{t[n % 5]}</p><p>{t[(n + 3) % 5]} {t[(n + 4) % 5]}</p><p>{t[(n + 2) % 5]}</p>"
            f"<p>{t[(n + 1) % 5]} {t[n % 5]}</p><p>{t[(n + 4) % 5]}</p></div>"
            '<div class="foot"><div class="band">a status band</div><div class="box">Type / for commands</div>'
            "<small>model &nbsp; effort &nbsp; mode</small></div></section>"
        )

    return f"""<!doctype html><meta charset="utf-8">
<style>
html,body{{margin:0;height:100%;color:{c['text']};font:15px/1.6 -apple-system,system-ui,sans-serif}}
.bg{{position:fixed;inset:0}}
.app{{position:fixed;inset:0;display:grid;grid-template-columns:1fr 1fr}}
.pane{{display:flex;flex-direction:column;min-width:0;border-left:1px solid {c['line']}}}.pane:first-child{{border:0}}
header{{height:42px;display:flex;align-items:center;padding:0 22px;font-size:13px;border-bottom:1px solid {c['line']}}}
.col{{flex:1;width:min(680px,calc(100% - 96px));margin:0 auto;padding-top:22px;overflow:hidden}}
h4{{margin:14px 0 6px;font-size:15px}}ul{{margin:0 0 10px;padding-left:22px}}p{{margin:0 0 12px}}
.foot{{width:min(700px,calc(100% - 76px));margin:0 auto 12px}}
.band{{font:12px Menlo,monospace;color:{c['muted']};background:{c['chip']};border-radius:10px;padding:26px 14px;margin-bottom:8px}}
.box{{border:1px solid {c['line']};border-radius:14px;background:{c['box']};color:{c['muted']};padding:10px 16px}}
small{{display:block;text-align:right;color:{c['muted']};padding:6px 8px 0;font-size:12px}}
</style>
<div class="bg">{svg}</div><div class="app">{pane('First session', 0)}{pane('Second session', 2)}</div>"""


def main():
    from PIL import Image

    module = importlib.import_module(sys.argv[1].removesuffix(".py"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    day, night = module.day(), module.night()
    shots = []
    for tag, picture, dark in (("light", day, False), ("dark", night, True)):
        html = out / f"{module.ID}_{tag}.html"
        html.write_text(page(alone(picture), dark))
        png = out / f"{module.ID}_{tag}.png"
        subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1", "--window-size=2000,1300", f"--screenshot={png}", f"file://{html}"],
            check=True,
            capture_output=True,
        )
        html.unlink()
        shots.append(Image.open(png))
    cut = 520
    both = Image.new("RGB", (2000, (1300 - cut) * 2 + 8), (200, 60, 60))
    both.paste(shots[0].crop((0, cut, 2000, 1300)), (0, 0))
    both.paste(shots[1].crop((0, cut, 2000, 1300)), (0, 1300 - cut + 8))
    both.save(out / f"{module.ID}_both.png")
    size = len(document(day, night))
    print(f"{module.NAME}: SVG {size} characters of 131072 allowed ({'ok' if size <= 110000 else 'TOO CLOSE: trim it under 110000'}); pictures in {out}")


if __name__ == "__main__":
    main()
