"""Generate the logo of the self-calibration project page as scalable SVG files.

The mark speaks the notation of the tutorial's factor graphs: anchors are circles
in the palette of `Paper/tex/figures/figure_common.tex` (palBlue #2166AC, the
"self-calibration family" of the terminology review's figures), range factors
are filled squares on the links, and an open ring marks the position that is
still to be found, as on the HYMN page.

Concept "rigid frame" (Paul's pick of 2026-11-12 from three drafts, the others
being "the start decides" and "grid posterior"): four anchors as a complete
graph, three calibrated and one open ring with a dashed belief in the middle.
A "?" in the open ring, as the tutorial's figures mark unknown anchors, was
tried and left out: below about 100 px it turns into noise, while the open ring
stays legible at 16 px and carries the same meaning.

Lettering: wordmark in Source Serif 4 Bold, tagline in Source Serif 4
Semibold, both converted to outlines with fontTools (fonts located via MiKTeX
kpsewhich), so the files do not depend on installed fonts. Dashes and dots are
drawn as separate shapes, so every renderer (PyMuPDF, browsers, GitHub) shows
them alike.

Outputs in logo/:
  selfcal-mark[-dark|-white].svg            mark on a 100 x 100 square
  selfcal-mark-inline.svg                   mark coloured by the page's CSS tokens
                                            (--ink, --ink-2, --brand-*), an HTML
                                            snippet for the topbar, not standalone
  selfcal-icon.svg                          favicon: simplified mark on a dark tile
  selfcal-icon-full.svg                     the same tile without corner radius
  apple-touch-icon.png                      selfcal-icon-full.svg at 180 px
  selfcal-logo[-dark|-white].svg            mark + title + tagline, cropped to ink
  selfcal-logo-compact[-dark|-white].svg    mark + compact wordmark, cropped to ink
  pdf/<name>.pdf                            every mark and lockup above as PDF

Usage:
    python make_logo.py            # write all outputs for CONCEPT, check the geometry
    python make_logo.py --png      # also write control renderings to logo/png/
    python make_logo.py --drafts   # contact sheet of the mark at its sizes to ../_src/drafts/
"""

from __future__ import annotations

import io
import math
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "logo"
DRAFTS = HERE.parent / "_src" / "drafts"

CONCEPT = "a"  # Paul's pick (2026-11-12)

# Palettes. Light values derive from figure_common.tex / radiocal_common.tex:
# anchor stroke palBlue!60!black, anchor fill palBlue!15, range factor palBlue,
# belief palLightBlue, links in the page's secondary ink.
PALETTES = {
    "light": dict(ink="#0b0b0b", link="#52514e", anc="#143d67", fill="#dee8f3",
                  fac="#2166ac", halo="#67a9cf"),
    "dark": dict(ink="#ffffff", link="#a3a29b", anc="#8fc1e3", fill="#1d3550",
                 fac="#67a9cf", halo="#4393c3"),
    "white": dict(ink="#ffffff", link="#ffffff", anc="#ffffff", fill="#ffffff",
                  fac="#ffffff", halo="#ffffff"),
    # favicon tile: bright variants on near-black
    "tile": dict(ink="#fcfcfb", link="#c3c2b7", anc="#8fc1e3", fill="#4393c3",
                 fac="#67a9cf", halo="#67a9cf"),
    # inline mark: the page's tokens resolve to the light or dark values above
    "css": dict(ink="var(--ink)", link="var(--ink-2)", anc="var(--brand-anc)",
                fill="var(--brand-fill)", fac="var(--brand-fac)", halo="var(--brand-halo)"),
}
TILE_BG = "#0b0b0b"

WORDMARK_FONT = "SourceSerif4-Bold.otf"
TAGLINE_FONT = "SourceSerif4-Semibold.otf"
TITLE_FULL = "Infrastructure Self-Calibration"
TITLE_COMPACT = "Self-Calibration"
TAGLINE = "for radio-based indoor positioning"
TITLE = "Infrastructure Self-Calibration for radio-based indoor positioning"

MIN_GAP = 2.5          # clearance between shapes that do not touch, in grid units
MIN_ICON_STROKE = 6.0  # thinnest favicon stroke: 6 units = about 1 px at 16 px


def n(v: float) -> str:
    """Compact number formatting for SVG coordinates."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# --------------------------------------------------------------- shapes ---

def circle(cx, cy, r, fill, stroke=None, width=0.0):
    st = f' stroke="{stroke}" stroke-width="{n(width)}"' if stroke else ""
    return f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="{fill}"{st}/>'


def ring(cx, cy, r_out, r_in, fill):
    """Open ring as one even-odd path, so it stays transparent inside."""
    def circ(r, sweep):
        return (f"M{n(cx - r)},{n(cy)}a{n(r)},{n(r)} 0 1,{sweep} {n(2 * r)},0"
                f"a{n(r)},{n(r)} 0 1,{sweep} {n(-2 * r)},0Z")
    return f'<path d="{circ(r_out, 0)}{circ(r_in, 1)}" fill="{fill}" fill-rule="evenodd"/>'


def segment(x0, y0, x1, y1, width, stroke):
    return (f'<path d="M{n(x0)},{n(y0)}L{n(x1)},{n(y1)}" fill="none" stroke="{stroke}" '
            f'stroke-width="{n(width)}" stroke-linecap="round"/>')


def square(cx, cy, s, fill):
    return f'<rect x="{n(cx - s / 2)}" y="{n(cy - s / 2)}" width="{n(s)}" height="{n(s)}" fill="{fill}"/>'


def dashed_circle(cx, cy, r, width, stroke, dashes=12, duty=0.55, phase=0.0):
    """A dashed circle as separate round-capped arcs (renderer-independent)."""
    out = []
    step = 360 / dashes
    for k in range(dashes):
        a0 = math.radians(phase + k * step)
        a1 = math.radians(phase + k * step + duty * step)
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        out.append(f'<path d="M{n(x0)},{n(y0)}A{n(r)},{n(r)} 0 0,1 {n(x1)},{n(y1)}" fill="none" '
                   f'stroke="{stroke}" stroke-width="{n(width)}" stroke-linecap="round"/>')
    return "".join(out)


def link(a, b, ra, rb, gap, width, stroke):
    """Segment between two node centres, trimmed by their radii plus a gap."""
    (x0, y0), (x1, y1) = a, b
    d = math.dist(a, b)
    ux, uy = (x1 - x0) / d, (y1 - y0) / d
    s0, s1 = ra + gap, rb + gap
    return segment(x0 + ux * s0, y0 + uy * s0, x1 - ux * s1, y1 - uy * s1, width, stroke)


def anchor(cx, cy, r, sw, p):
    """Calibrated anchor: a solid disc in palBlue, so that only the position still
    to be found is drawn open."""
    return circle(cx, cy, r, p["fac"])


# -------------------------------------------------------------- concepts ---
# Each concept returns (markup, shapes): shapes is a list of ("node", x, y, r) and
# ("link", x0, y0, x1, y1, half_width, i, j) for the geometry check.

def rot(points, deg, cx=50.0, cy=50.0):
    a = math.radians(deg)
    return [(cx + (x - cx) * math.cos(a) - (y - cy) * math.sin(a),
             cy + (x - cx) * math.sin(a) + (y - cy) * math.cos(a)) for x, y in points]


def concept_a(p, icon=False):
    """Rigid frame: K4 drawn as a triangle of calibrated anchors around an open ring."""
    R, turn = (40.0, 12) if not icon else (36.0, 12)
    c = (50.0, 52.0)
    corners = [(c[0] + R * math.cos(math.radians(a + turn)), c[1] + R * math.sin(math.radians(a + turn)))
               for a in (-90, 30, 150)]
    r_node, sw, lw, fs, gap = (8.6, 0, 2.1, 5.6, 2.6) if not icon else (12.5, 0, 6.5, 0, 0)
    r_c_out, r_c_in = (8.6, 5.0) if not icon else (12.0, 6.4)
    out, shapes = [], []
    nodes = corners + [c]
    radii = [r_node] * 3 + [r_c_out]
    pairs = [(0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3)]
    for i, j in pairs:
        out.append(link(nodes[i], nodes[j], radii[i], radii[j], gap, lw, p["link"]))
        shapes.append(("link", *nodes[i], *nodes[j], lw / 2, i, j))
    if not icon:
        for i, j in pairs:
            mx, my = (nodes[i][0] + nodes[j][0]) / 2, (nodes[i][1] + nodes[j][1]) / 2
            if j == 3:  # spokes: factor nearer the corner, clear of the belief
                mx, my = nodes[i][0] + 0.42 * (c[0] - nodes[i][0]), nodes[i][1] + 0.42 * (c[1] - nodes[i][1])
            out.append(square(mx, my, fs, p["fac"]))
    for (x, y) in corners:
        out.append(anchor(x, y, r_node, sw, p) if not icon else circle(x, y, r_node, p["fill"]))
        shapes.append(("node", x, y, r_node))
    if not icon:
        out.append(dashed_circle(*c, 14.2, 1.9, p["halo"], dashes=14, duty=0.5, phase=-90))
    out.append(ring(*c, r_c_out, r_c_in, p["ink"]))
    shapes.append(("node", *c, r_c_out if icon else 15.2))
    return "".join(out), shapes


CONCEPTS = {"a": concept_a}


def recentre(markup: str, shapes, icon: bool) -> tuple[str, tuple]:
    """Shift the mark so its node bounding box sits centred on the 100 x 100 grid."""
    xs = [s[1] - s[3] for s in shapes if s[0] == "node"] + [s[1] + s[3] for s in shapes if s[0] == "node"]
    ys = [s[2] - s[3] for s in shapes if s[0] == "node"] + [s[2] + s[3] for s in shapes if s[0] == "node"]
    dx, dy = 50 - (min(xs) + max(xs)) / 2, 50 - (min(ys) + max(ys)) / 2
    box = (min(xs) + dx, min(ys) + dy, max(xs) + dx, max(ys) + dy)
    return f'<g transform="translate({n(dx)} {n(dy)})">{markup}</g>', box


def mark(p, concept=None, icon=False, radius=22.0):
    """Inner SVG markup of the mark (or the favicon, tile corner `radius`) on a 100 x 100 grid."""
    markup, shapes = CONCEPTS[concept or CONCEPT](p, icon)
    markup, _ = recentre(markup, shapes, icon)
    tile = f'<rect width="100" height="100" rx="{n(radius)}" fill="{TILE_BG}"/>' if icon else ""
    return tile + markup


def mark_box(concept=None):
    markup, shapes = CONCEPTS[concept or CONCEPT](PALETTES["light"], False)
    return recentre(markup, shapes, False)[1]


def _seg_dist(px, py, x0, y0, x1, y1):
    vx, vy = x1 - x0, y1 - y0
    t = max(0.0, min(1.0, ((px - x0) * vx + (py - y0) * vy) / (vx * vx + vy * vy)))
    return math.dist((px, py), (x0 + t * vx, y0 + t * vy))


def check_geometry(concept=None, strict=True) -> None:
    """Assert clearances (node to node, link to the nodes it does not join) and the
    thinnest favicon stroke."""
    for icon in (False, True):
        _, shapes = CONCEPTS[concept or CONCEPT](PALETTES["light"], icon)
        nodes = [s for s in shapes if s[0] == "node"]
        links = [s for s in shapes if s[0] == "link"]
        gaps = [math.dist(a[1:3], b[1:3]) - a[3] - b[3] for i, a in enumerate(nodes) for b in nodes[i + 1:]]
        for lk in links:
            _, x0, y0, x1, y1, hw, *_ = lk
            for nd in nodes:
                if min(math.dist(nd[1:3], (x0, y0)), math.dist(nd[1:3], (x1, y1))) < 1e-6:
                    continue  # the link joins this node
                gaps.append(_seg_dist(nd[1], nd[2], x0, y0, x1, y1) - nd[3] - hw)
        gap = min(gaps)
        name = f"{concept or CONCEPT}-{'icon' if icon else 'mark'}"
        print(f"{name}: smallest clearance {gap:.2f}")
        ok = gap >= MIN_GAP
        if icon:
            widths = [2 * s[5] for s in links]
            ok = ok and min(widths) >= MIN_ICON_STROKE
        if strict:
            assert ok, f"{name}: clearance {gap:.2f} or favicon stroke below the minimum"
        elif not ok:
            print(f"  {name}: FAILS the geometry check")


# ------------------------------------------------------------ lettering ---
# Copied from the HYMN logo source (hymn-localization/Landing Page/brand/make_logo.py).

@lru_cache
def font(name: str) -> TTFont:
    path = subprocess.run(["kpsewhich", name], capture_output=True, text=True).stdout.strip()
    if not path:
        raise FileNotFoundError(f"kpsewhich cannot find {name}")
    return TTFont(path)


def _pair_kern(f: TTFont, left: str, right: str) -> int:
    """Horizontal pair adjustment from the GPOS 'kern' feature (PairPos 1/2)."""
    if "GPOS" not in f:
        return 0
    table = f["GPOS"].table
    idx = sorted({i for fr in table.FeatureList.FeatureRecord if fr.FeatureTag == "kern"
                  for i in fr.Feature.LookupListIndex})
    for li in idx:
        lookup = table.LookupList.Lookup[li]
        for st in lookup.SubTable:
            if lookup.LookupType == 9:
                st = st.ExtSubTable
            if getattr(st, "LookupType", 2) != 2 or left not in st.Coverage.glyphs:
                continue
            if st.Format == 1:
                ps = st.PairSet[st.Coverage.glyphs.index(left)]
                for rec in ps.PairValueRecord:
                    if rec.SecondGlyph == right and rec.Value1 is not None:
                        return getattr(rec.Value1, "XAdvance", 0) or 0
            elif st.Format == 2:
                c1 = st.ClassDef1.classDefs.get(left, 0)
                c2 = st.ClassDef2.classDefs.get(right, 0)
                v = st.Class1Record[c1].Class2Record[c2].Value1
                adv = getattr(v, "XAdvance", 0) if v is not None else 0
                if adv:
                    return adv
    return 0


def text_path(font_name: str, text: str, size: float, x: float, baseline: float,
              tracking: float = 0.0) -> tuple[str, float, tuple]:
    """Outline `text` as one SVG path string. Returns (d, advance width, ink bbox)."""
    f = font(font_name)
    gs, cmap = f.getGlyphSet(), f.getBestCmap()
    s = size / f["head"].unitsPerEm
    names = [cmap[ord(c)] for c in text]
    pen = SVGPathPen(gs, ntos=n)
    bounds = BoundsPen(gs)
    cursor = 0.0
    for i, name in enumerate(names):
        m = (s, 0, 0, -s, x + cursor, baseline)
        gs[name].draw(TransformPen(pen, m))
        gs[name].draw(TransformPen(bounds, m))
        cursor += f["hmtx"][name][0] * s
        if i + 1 < len(names):
            cursor += _pair_kern(f, name, names[i + 1]) * s + tracking * size
    return pen.getCommands(), cursor, bounds.bounds


def cap_height(font_name: str) -> float:
    f = font(font_name)
    return f["OS/2"].sCapHeight / f["head"].unitsPerEm


# -------------------------------------------------------------- lockups ---

def lockup(p, tagline: bool, concept=None) -> tuple[str, tuple]:
    """Mark left, wordmark right (mark height 100). Returns (markup, ink viewBox)."""
    x = 118  # mark grid (100) + gap
    text = TITLE_FULL if tagline else TITLE_COMPACT
    cap, base = (30.0, 52.0) if tagline else (34.0, 67.0)
    d, _, bb = text_path(WORDMARK_FONT, text, cap / cap_height(WORDMARK_FONT), x, base, tracking=0.005)
    shift = x - bb[0]  # align the ink edge of the first letter with x
    parts = [mark(p, concept), f'<path transform="translate({n(shift)} 0)" d="{d}" fill="{p["ink"]}"/>']
    x0, y0, x1, y1 = mark_box(concept)
    x1, y0, y1 = max(x1, bb[2] + shift), min(y0, bb[1]), max(y1, bb[3])
    if tagline:
        # set the tagline to the width of the title
        _, _, pb = text_path(TAGLINE_FONT, TAGLINE, 10, 0, 0, tracking=0.01)
        t_size = min(22.0, 10 * (bb[2] - bb[0]) / (pb[2] - pb[0]))
        td, _, tb = text_path(TAGLINE_FONT, TAGLINE, t_size, x, 80, tracking=0.01)
        parts.append(f'<path transform="translate({n(x - tb[0])} 0)" d="{td}" fill="{p["link"]}"/>')
        x1, y1 = max(x1, tb[2] + x - tb[0]), max(y1, tb[3])
    return "".join(parts), (x0, y0, x1 - x0, y1 - y0)


def svg(inner: str, box: tuple) -> str:
    vb = " ".join(n(v) for v in box)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" '
            f'aria-label="{TITLE}"><title>{TITLE}</title>{inner}</svg>\n')


def inline_mark(concept=None) -> str:
    """Topbar snippet: the mark coloured by the page's CSS tokens.

    var() goes into style attributes, because presentation attributes with var()
    are not reliable across browsers. The page keeps the title as live text next
    to it, so the SVG is hidden from assistive technology.
    """
    inner = re.sub(r'(fill|stroke)="(var\(--[\w-]+\))"', r'style="\1:\2"', mark(PALETTES["css"], concept))
    return (f'<svg class="brand-mark" viewBox="0 0 100 100" aria-hidden="true" '
            f'focusable="false">{inner}</svg>\n')


def build(concept=None) -> dict[str, str]:
    """Write the SVGs. Returns the standalone ones (not the inline snippet) by name."""
    files = {"selfcal-icon.svg": svg(mark(PALETTES["tile"], concept, icon=True), (0, 0, 100, 100)),
             "selfcal-icon-full.svg": svg(mark(PALETTES["tile"], concept, icon=True, radius=0),
                                          (0, 0, 100, 100))}
    for suffix, pal in [("", "light"), ("-dark", "dark"), ("-white", "white")]:
        p = PALETTES[pal]
        files[f"selfcal-mark{suffix}.svg"] = svg(mark(p, concept), (0, 0, 100, 100))
        files[f"selfcal-logo{suffix}.svg"] = svg(*lockup(p, tagline=True, concept=concept))
        files[f"selfcal-logo-compact{suffix}.svg"] = svg(*lockup(p, tagline=False, concept=concept))
    OUT.mkdir(exist_ok=True)
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8")
    (OUT / "selfcal-mark-inline.svg").write_text(inline_mark(concept), encoding="utf-8")
    return files


def export(files: dict[str, str]) -> int:
    """Apple touch icon (180 px PNG) and PDFs of all marks and lockups via PyMuPDF."""
    import fitz

    page = fitz.open(stream=files["selfcal-icon-full.svg"].encode(), filetype="svg")[0]
    zoom = 180 / page.rect.height
    page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False).save(OUT / "apple-touch-icon.png")
    pdf = OUT / "pdf"
    pdf.mkdir(exist_ok=True)
    names = [name for name in files if not name.startswith("selfcal-icon")]
    for name in names:
        doc = fitz.open(stream=files[name].encode(), filetype="svg")
        (pdf / f"{Path(name).stem}.pdf").write_bytes(doc.convert_to_pdf())
    return len(names)


def _with_bg(text: str, bg: str) -> str:
    head, body = text.split(">", 1)
    x, y, w, h = head.split('viewBox="')[1].split('"')[0].split()
    return f'{head}><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{bg}"/>{body}'


def _png(text: str, px: int, by_height=True):
    import fitz
    from PIL import Image

    page = fitz.open(stream=text.encode(), filetype="svg")[0]
    zoom = px / (page.rect.height if by_height else page.rect.width)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def render_pngs(files: dict[str, str]) -> None:
    """Control renderings on the background each variant is made for."""
    png = OUT / "png"
    png.mkdir(exist_ok=True)
    for name, text in files.items():
        bg = "#0d0d0d" if "-dark" in name else "#2166ac" if "-white" in name else "#f9f9f7"
        if not name.startswith("selfcal-icon"):
            text = _with_bg(text, bg)
        for px in ([16, 32, 180, 512] if "mark" in name or "icon" in name else [48, 400]):
            _png(text, px).save(png / f"{Path(name).stem}-{px}.png")


def drafts() -> Path:
    """Contact sheet of every concept: marks on light and dark ground, the favicon at
    its real sizes (enlarged without smoothing beside them) and the compact lockup."""
    from PIL import Image, ImageDraw, ImageFont

    DRAFTS.mkdir(parents=True, exist_ok=True)
    rows = []
    for key in CONCEPTS:
        check_geometry(key, strict=False)
        light = _png(_with_bg(svg(mark(PALETTES["light"], key), (0, 0, 100, 100)), "#f9f9f7"), 220)
        dark = _png(_with_bg(svg(mark(PALETTES["dark"], key), (0, 0, 100, 100)), "#0d0d0d"), 220)
        icon_svg = svg(mark(PALETTES["tile"], key, icon=True), (0, 0, 100, 100))
        icons = []
        for px in (16, 32):
            im = _png(icon_svg, px)
            icons.append(im.resize((px * 4, px * 4), Image.NEAREST))
        icon180 = _png(icon_svg, 120)
        lock = _png(_with_bg(svg(*lockup(PALETTES["light"], False, key)), "#f9f9f7"), 90)
        lock_full = _png(_with_bg(svg(*lockup(PALETTES["light"], True, key)), "#f9f9f7"), 90)
        rows.append((key, light, dark, icons, icon180, lock, lock_full))
        for nm, im in (("mark-light", light), ("mark-dark", dark), ("icon-120", icon180),
                       ("lockup-compact", lock), ("lockup-full", lock_full)):
            im.save(DRAFTS / f"concept-{key}-{nm}.png")
    W, pad = 2150, 24
    H = sum(max(220, 90 * 2 + pad) + 2 * pad + 30 for _ in rows) + pad
    sheet = Image.new("RGB", (W, H), "#ffffff")
    draw = ImageDraw.Draw(sheet)
    try:
        label = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        label = ImageFont.load_default()
    y = pad
    names = {"a": "A  rigid frame"}
    for key, light, dark, icons, icon180, lock, lock_full in rows:
        draw.text((pad, y), names[key], fill="#0b0b0b", font=label)
        y += 34
        x = pad
        sheet.paste(light, (x, y)); x += light.width + pad
        sheet.paste(dark, (x, y)); x += dark.width + pad
        for im in icons:
            sheet.paste(im, (x, y)); x += im.width + 12
        sheet.paste(icon180, (x, y)); x += icon180.width + pad
        sheet.paste(lock, (x, y)); sheet.paste(lock_full, (x, y + lock.height + pad))
        y += max(220, lock.height + lock_full.height + pad) + 2 * pad
    out = DRAFTS / "sheet.png"
    sheet.save(out)
    return out


def apply_to_page(files: dict[str, str]) -> None:
    """Carry the logo into the page: favicon and touch icon into assets/img, the
    inline mark between every <!-- MARK:START --> and <!-- MARK:END --> of
    index.html, and a ?v= on both icon links derived from the icon, so that
    browsers drop a cached icon whenever it changes (the HYMN page learned this
    from Firefox)."""
    import hashlib
    import shutil

    page = HERE.parent / "index.html"
    img = HERE.parent / "assets" / "img"
    if not page.exists():
        return
    img.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUT / "selfcal-icon.svg", img / "favicon.svg")
    shutil.copyfile(OUT / "apple-touch-icon.png", img / "apple-touch-icon.png")
    v = hashlib.sha256(files["selfcal-icon.svg"].encode()).hexdigest()[:8]
    text = page.read_text(encoding="utf-8")
    snippet = inline_mark().strip()
    text, k = re.subn(r"(<!-- MARK:START -->).*?(<!-- MARK:END -->)",
                      lambda m: m.group(1) + snippet + m.group(2), text, flags=re.S)
    text = re.sub(r"(favicon\.svg|apple-touch-icon\.png)\?v=\w+", lambda m: f"{m.group(1)}?v={v}", text)
    page.write_text(text, encoding="utf-8", newline="\n")
    print(f"page: inline mark in {k} places, icons copied, ?v={v}")


if __name__ == "__main__":
    if "--drafts" in sys.argv:
        print("wrote", drafts())
        sys.exit(0)
    check_geometry()
    files = build()
    n_pdf = export(files)
    if "--png" in sys.argv:
        render_pngs(files)
    print(f"wrote {len(files) + 1} SVGs, apple-touch-icon.png and {n_pdf} PDFs to {OUT}")
    apply_to_page(files)
