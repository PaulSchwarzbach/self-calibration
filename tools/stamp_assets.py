"""Stamp the stylesheet and script links of index.html with the hash of their files.

A browser that still holds an older style.css or main.js in its cache would
otherwise render a new page with old styles, which breaks the layout (seen on
2026-11-12: the folding cards unstyled and the funnel of the term scheme as two
blank squares). With `style.css?v=<hash>` the URL changes whenever the file
does, so every browser fetches the new file. make_logo.py stamps the favicon
links the same way. check_page.py fails while a stamp is out of date.

Usage (from the landing-page root), after every edit of style.css or main.js:
    python tools/stamp_assets.py
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ["assets/css/style.css", "assets/js/main.js"]


def digest(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:8]


def stamped(src: str) -> str:
    for rel in FILES:
        src, k = re.subn(rf'(["\']){re.escape(rel)}(?:\?v=\w+)?(["\'])', rf"\g<1>{rel}?v={digest(rel)}\g<2>", src)
        assert k == 1, f"{rel}: {k} references in index.html"
    return src


if __name__ == "__main__":
    page = ROOT / "index.html"
    page.write_text(stamped(page.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    print("index.html: " + ", ".join(f"{Path(r).name}?v={digest(r)}" for r in FILES))
