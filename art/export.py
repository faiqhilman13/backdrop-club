#!/usr/bin/env python3
"""Writes scenes into the gallery as themes/<id>/backdrop.svg and theme.json.

    python3 art/export.py scene_london scene_paris

A scene module gives ID, NAME, DESCRIPTION, TAGS, day() and night(). The module
is the source of truth for the details; a theme.json that exists keeps its date.
"""

from __future__ import annotations

import datetime
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from dither import document  # noqa: E402

THEMES = HERE.parent / "themes"
LIMIT = 100_000


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for name in sys.argv[1:]:
        m = importlib.import_module(Path(name).stem)
        svg = document(m.day(), m.night())
        if len(svg) > LIMIT:
            sys.exit(f"{m.ID}: {len(svg)} characters; keep it under {LIMIT}")
        folder = THEMES / m.ID
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "backdrop.svg").write_text(svg)
        meta = folder / "theme.json"
        old = json.loads(meta.read_text()) if meta.exists() else {}
        tags = list(dict.fromkeys([*getattr(m, "TAGS", old.get("tags", [])), "dither"]))[:6]
        details = {
            "name": m.NAME,
            "author": getattr(m, "AUTHOR", old.get("author", "faiqhilman13")),
            "description": getattr(m, "DESCRIPTION", old.get("description", "")),
            "tags": tags,
            "added": old.get("added", datetime.date.today().isoformat()),
            "license": old.get("license", "MIT"),
        }
        meta.write_text(json.dumps(details, indent=2) + "\n")
        print(f"{m.ID}: {len(svg)} characters -> themes/{m.ID}/")


if __name__ == "__main__":
    main()
