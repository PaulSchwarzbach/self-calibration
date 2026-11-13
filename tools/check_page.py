"""Check index.html before a deploy. Exit code 1 on any FAIL.

  placeholders   no PENDING token and no data-pending attribute is left (the
                 tutorial's arXiv ID)
  prose          visible text and alt texts: Paul's vocabulary blacklist, no
                 semicolon, no em dash, no adverb starters (code, BibTeX, JSON
                 and the generated node table are not prose)
  abbreviations  each listed abbreviation is defined as "Full words (ABBR)" at
                 its first visible use
  links          external links open in a new tab with rel="noopener", every
                 #fragment names an id of the page
  images         every <img> has alt, width and height, and its file exists
  guide          every string of the decision guide (the JSON block) occurs in
                 fig_decision_tree.tex of the tutorial at TUTORIAL_TAG, once the
                 LaTeX markup is stripped
  runts          every text block ends on a tail tied by no-break spaces
                 (tools/no_runts.py), so no paragraph ends on a lone word
  stamps         the ?v= of style.css and main.js in index.html is the hash of
                 the current file (tools/stamp_assets.py), so no browser pairs
                 the page with a cached older stylesheet or script
  numbers        every number in the visible text, outside the generated node
                 table and figure references, occurs in README.md (Provenance)

Usage (from the landing-page root):
    python tools/check_page.py
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RC = ROOT.parent
TUTORIAL_TAG = "submission/comst-2026-11-11"

BLACKLIST = ["delve", "leverage", "utilize", "utilise", "facilitate", "aforementioned", "seamless",
             "holistic", "harness", "paradigm", "pivotal", "underscore", "streamline", "landscape",
             "ecosystem", "cutting-edge", "in terms of", "it is important to note",
             "plays a crucial role", "a myriad of"]
STARTERS = ["Notably", "Importantly", "Crucially", "Interestingly"]
ABBREVIATIONS = ["SLAM", "UWB", "LOS", "NLOS", "RMSE", "ECDF", "PRISMA", "PGP", "CF", "CGP"]
SKIP_TAGS = {"script", "style", "pre", "code", "svg", "title", "table"}


class Page(HTMLParser):
    """Visible text (with the skipped regions left out), attributes and ids."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.skip = 0
        self.text: list[str] = []
        self.tables: list[str] = []
        self.in_table = 0
        self.alts: list[str] = []
        self.ids: set[str] = set()
        self.links: list[dict] = []
        self.imgs: list[dict] = []
        self.pending: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if "data-pending" in a:
            self.pending.append(a["data-pending"])
        if tag == "a":
            self.links.append(a)
        if tag == "img":
            self.imgs.append(a)
            if a.get("alt"):
                self.alts.append(a["alt"])
        if tag == "table":
            self.in_table += 1
            self.table_cls = a.get("class", "")
        if tag in SKIP_TAGS:
            self.skip += 1
        if tag not in ("img", "br", "meta", "link", "input", "source", "path", "circle", "rect", "polygon"):
            self.stack.append(tag)
        if tag in ("p", "li", "dd", "dt", "h1", "h2", "h3", "figcaption", "blockquote", "td", "th",
                   "caption", "summary", "div", "span"):
            self.text.append(" ")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
        if tag == "table":
            self.in_table = max(0, self.in_table - 1)
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        if tag in ("p", "li", "dd", "figcaption", "blockquote", "caption", "h1", "h2", "h3"):
            self.text.append("\n")

    def handle_data(self, data):
        if self.skip == 0:
            self.text.append(data)
        elif self.in_table and "nodes" not in getattr(self, "table_cls", "") and "svg" not in self.stack \
                and "code" not in self.stack and "pre" not in self.stack:
            self.tables.append(data)


def visible(page: Page) -> str:
    return re.sub(r"[ \t]+", " ", "".join(page.text))


def strip_latex(s: str) -> str:
    s = re.sub(r"%.*", "", s)
    s = s.replace("\\\\", " ").replace("~", " ").replace("\\ ", " ").replace("\\_", "_")
    s = re.sub(r"\\(?:textbf|texttt|minortext|emph)\{", "{", s)
    s = re.sub(r"\\color\{[^}]*\}", "", s)
    s = re.sub(r"\$([^$]*)\$", r"\1", s)
    s = s.replace("{", "").replace("}", "")
    s = s.replace("e.g.\\", "e.g.")
    return re.sub(r"\s+", " ", s)


def main() -> int:
    fails, warns = [], []
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    page = Page()
    page.feed(src)
    text = visible(page)

    # placeholders
    for tok in sorted(set(re.findall(r"[A-Z][A-Z-]*PENDING", src))):
        fails.append(f"placeholder left: {tok}")
    for p in page.pending:
        fails.append(f"data-pending left: {p}")

    # prose
    prose = text + "\n" + "\n".join(page.alts)
    low = prose.lower()
    for w in BLACKLIST:
        if re.search(rf"\b{re.escape(w)}", low):
            fails.append(f"blacklisted word: {w}")
    for s in STARTERS:
        if re.search(rf"(^|[.!?]\s+){s}\b", prose):
            fails.append(f"adverb starter: {s}")
    for line in prose.splitlines():
        if ";" in line:
            fails.append(f"semicolon in prose: {line.strip()[:90]}")
        if "—" in line:
            fails.append(f"em dash in prose: {line.strip()[:90]}")

    # abbreviations: the first use is the definition "... (ABBR)"
    for ab in ABBREVIATIONS:
        m = re.search(rf"(?<![\w-]){ab}(?![\w-])", text)
        if not m:
            warns.append(f"abbreviation never used: {ab}")
            continue
        if text[max(0, m.start() - 1):m.start()] != "(":
            fails.append(f"abbreviation {ab} used before its definition: …{text[max(0, m.start() - 60):m.end() + 10]!r}")

    # links
    for a in page.links:
        href = a.get("href", "")
        if href.startswith("http"):
            if a.get("target") != "_blank" or "noopener" not in a.get("rel", ""):
                fails.append(f"external link without new tab or noopener: {href}")
        elif href.startswith("#") and href[1:] not in page.ids:
            fails.append(f"fragment without target: {href}")

    # images
    for im in page.imgs:
        s = im.get("src", "")
        if not im.get("alt"):
            fails.append(f"image without alt: {s}")
        if not (im.get("width") and im.get("height")):
            fails.append(f"image without width/height: {s}")
        if not (ROOT / s.split("?")[0]).exists():
            fails.append(f"image file missing: {s}")

    # guide strings against the TikZ source of Fig. 12
    tex = subprocess.run(["git", "-C", str(RC), "show",
                          f"{TUTORIAL_TAG}:Paper/tex/figures/fig_decision_tree.tex"],
                         check=True, capture_output=True, text=True, encoding="utf-8").stdout
    flat = strip_latex(tex.split("\\begin{tikzpicture}")[1])
    data = json.loads(re.search(r'<script type="application/json" id="guide-data">(.*?)</script>',
                                src, re.S).group(1))
    strings = []
    for nd in data["nodes"].values():
        strings += [nd.get(k) for k in ("q", "name", "evidence", "cond", "advice", "prefix", "ref") if nd.get(k)]
        strings += [lbl for lbl, _ in nd.get("answers", [])]
        if nd.get("method"):
            strings.append("".join(p.get("text", p.get("code", "")) for p in nd["method"]))
    for s in strings:
        if s not in flat:
            fails.append(f"guide string not in fig_decision_tree.tex: {s!r}")

    # stamps of the stylesheet and the script
    sys.path.insert(0, str(ROOT / "tools"))
    import stamp_assets
    if stamp_assets.stamped(src) != src:
        fails.append("style.css or main.js changed since its ?v= stamp, run tools/stamp_assets.py")

    # runts: every text block ends on a tied tail
    import no_runts
    _, untied = no_runts.process(src)
    for u in untied:
        fails.append(f"block may end on a lone word, run tools/no_runts.py: …{u[-50:]!r}")

    # numbers against the provenance in README.md
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    prov = readme.split("## Provenance", 1)[-1]
    body = re.sub(r"\b(Fig\.|Figs\.|Table|Section|Sections|Sec\.|Conf\.|scenario|arXiv:)\s*[\dIVX]+(?:[-–][A-Z\d]+)?", " ", text)
    body = re.sub(r"\bs\d\d\b|set_[ab]", " ", body)
    nums = set(re.findall(r"\d+(?:[.,]\d+)?(?:–\d+(?:[.,]\d+)?)?", body + " " + " ".join(page.tables)))
    for n in sorted(nums):
        if n not in prov:
            fails.append(f"number without a provenance row in README.md: {n}")

    for w in warns:
        print("WARN ", w)
    for f in fails:
        print("FAIL ", f)
    print(f"{len(fails)} FAIL, {len(warns)} WARN, {len(page.links)} links, {len(page.imgs)} images, "
          f"{len(strings)} guide strings, {len(nums)} distinct numbers")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
