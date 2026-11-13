"""Keep the last line of every text block of index.html from holding a lone word.

A web page breaks its lines by window width, so a paragraph can end on a line
with a single word (a runt) at some width. The fix is a no-break space (&nbsp;)
before the last word, repeated until the unbreakable tail holds at least two
words and MIN_TAIL visible characters, so a short tail such as "Fig. 1." also
moves with the word before it. CSS text-wrap: pretty is not used: Firefox
ignores it (Paul's screenshot of 2026-11-12: "priors." alone), and Chromium
then shortens several lines of a paragraph.

Text blocks are p, li, dd, dt, figcaption, caption, blockquote, summary, h2 and
h3 that hold no other block. A hyphenated last word is kept whole in a no-wrap
span, since a break at its hyphen would leave its second half alone. Left alone: the header, script, pre, svg and button
contents, and the regions between the generated markers. main.js ties the
texts it writes itself (the decision guide). The pass is idempotent.

Usage (from the landing-page root):
    python tools/no_runts.py            # tie, report how many blocks changed
    python tools/no_runts.py --check    # list untied blocks, exit 1 if any
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_TAIL = 12
CANDIDATES = {"p", "li", "dd", "dt", "figcaption", "caption", "blockquote", "summary", "h2", "h3"}
BLOCKS = CANDIDATES | {"ul", "ol", "div", "figure", "table", "pre", "h1", "h2", "h3", "h4", "dl",
                       "section", "article", "header", "footer", "nav", "main", "details", "form"}
SKIP = {"header", "nav", "pre", "script", "svg", "button"}
# labels in columns of about 20 characters, where a tied tail pushes a short word
# onto a middle line of its own (the timeline, 2026-11-12)
SKIP_CLASSES = {"timeline"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
MARKERS = ["DEPLOYMENTS", "DEPLOYMENT-TABLE", "MARK"]
TOKEN = re.compile(r"<!--.*?-->|<![^>]*>|<(/?)([a-zA-Z][\w-]*)([^>]*)>|[^<]+|<", re.S)
PIECE = re.compile(r"(<[^>]*>)|([^<]+)", re.S)


def skipped_ranges(src: str) -> list[tuple[int, int]]:
    out = []
    for name in MARKERS:
        for m in re.finditer(rf"<!-- {name}:START -->.*?<!-- {name}:END -->", src, re.S):
            out.append(m.span())
    return out


def blocks(src: str) -> list[tuple[int, int, bool]]:
    """(start, end, tie) of the inner HTML of every text block, in document order.
    tie is False inside SKIP_CLASSES, where only the names are kept whole."""
    stack: list[dict] = []
    found = []
    pos = 0
    while pos < len(src):
        m = TOKEN.match(src, pos)
        if not m:
            break
        pos = m.end()
        if m.group(0).startswith("<!--") or m.group(2) is None:
            continue
        closing, name, rest = m.group(1), m.group(2).lower(), m.group(3)
        if not closing:
            if name == "script":  # raw text up to its end tag
                end = src.index("</script>", pos)
                pos = end + len("</script>")
                continue
            if name in VOID or rest.rstrip().endswith("/"):
                continue
            if name in BLOCKS:
                for el in stack:
                    el["has_block"] = True
            cls = re.search(r'class="([^"]*)"', rest)
            stack.append({"name": name, "inner": m.end(), "has_block": False,
                          "skip": bool(cls and SKIP_CLASSES & set(cls.group(1).split()))})
        else:
            while stack:
                el = stack.pop()
                if el["name"] == name:
                    break
            else:
                continue
            if (name in CANDIDATES and not el["has_block"]
                    and not any(a["name"] in SKIP for a in stack)):
                found.append((el["inner"], m.start(), not any(a["skip"] for a in stack)))
    return sorted(found)


def visible(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]*>", "", fragment)).strip()


def tail_ok(tail_html: str) -> bool:
    text = visible(tail_html)
    return len(re.split(r"[ \t\r\n ]+", text)) >= 2 and len(text) >= MIN_TAIL


def tie(inner: str) -> str:
    """Tie the end of one block's inner HTML until its unbreakable tail is long enough.

    Break points are the single-line spaces of the text. Whitespace with a line
    break is source layout between elements (buttons, links in a flex row), where
    a no-break space would render as an extra gap, so it is never tied."""
    while True:
        spaces = []
        seen_text = False
        for m in PIECE.finditer(inner):
            if m.group(2) is None:
                continue
            for w in re.finditer(r"[ \t\r\n]+|[^ \t\r\n]+", m.group(2)):
                if w.group(0)[0] in " \t\r\n":
                    if seen_text and "\n" not in w.group(0):
                        spaces.append((m.start(2) + w.start(), m.start(2) + w.end()))
                else:
                    seen_text = True
        spaces = [s for s in spaces if visible(inner[s[1]:])]
        if not spaces:
            return inner
        a, b = spaces[-1]
        if tail_ok(inner[b:]):
            return keep_last_word(inner)
        inner = inner[:a] + "&nbsp;" + inner[b:]


NOBREAK = ["UWB-ASC", "TWR-CLOUD-Bern"]  # names that must not break at their hyphens
NOBR_TAG = '<span class="nobr">'


def keep_names(inner: str) -> str:
    """Wrap the NOBREAK names of the text (not of attributes) in a no-wrap span.

    A tied tail such as "UWB-ASC recorded" would otherwise break inside the name,
    at its hyphen (seen at phone width on 2026-11-12)."""
    out, prev = [], ""
    for m in PIECE.finditer(inner):
        if m.group(1) is not None:
            out.append(m.group(1))
            prev = m.group(1)
            continue
        text = m.group(2)
        if not (prev == NOBR_TAG and text in NOBREAK):
            for name in NOBREAK:
                text = text.replace(name, f"{NOBR_TAG}{name}</span>")
        out.append(text)
        prev = ""
    return "".join(out)


def keep_last_word(inner: str) -> str:
    """Wrap a hyphenated last word of the block in a no-wrap span."""
    pieces = list(PIECE.finditer(inner))
    for i in range(len(pieces) - 1, -1, -1):
        m = pieces[i]
        if m.group(2) is None or not m.group(2).strip():
            continue
        prev = pieces[i - 1].group(1) if i > 0 else None
        w = re.search(r"([^\s;&<>]+-[^\s;&<>]+)\s*$", m.group(2))
        if not w or prev == NOBR_TAG and m.group(2).strip() == w.group(1):
            return inner
        a, b = m.start(2) + w.start(1), m.start(2) + w.end(1)
        return inner[:a] + f"{NOBR_TAG}{inner[a:b]}</span>" + inner[b:]
    return inner


def process(src: str) -> tuple[str, list[str]]:
    skips = skipped_ranges(src)
    changed = []
    for start, end, tied in reversed(blocks(src)):
        if any(s <= start < e for s, e in skips):
            continue
        inner = src[start:end]
        new = tie(keep_names(inner)) if tied else keep_names(inner)
        if new != inner:
            changed.append(html.unescape(re.sub(r"<[^>]*>", "", inner)).strip()[-60:])
            src = src[:start] + new + src[end:]
    return src, changed[::-1]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    page = ROOT / "index.html"
    src = page.read_text(encoding="utf-8")
    new, changed = process(src)
    if "--check" in sys.argv:
        for c in changed:
            print("untied:", repr(c))
        print(f"{len(changed)} untied blocks")
        sys.exit(1 if changed else 0)
    page.write_text(new, encoding="utf-8", newline="\n")
    print(f"index.html: {len(changed)} blocks tied")
