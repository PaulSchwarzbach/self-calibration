"""Build the page's figures from their original sources.

Every web asset is derived here from a named source file, so the page can be
rebuilt and each figure traced back to its publication (README.md, Provenance).
The helpers are those of the HYMN project page (hymn-localization/Landing Page/
tools/build_assets.py).

  tutorial   read with `git show <TUTORIAL_TAG>:<path>` from the RadioCalibration
             repository, so the page shows the figures of the submitted version,
             which is the arXiv preprint
  review     IEEE Access 2026, Fig. 4, the figure file the article includes
  jispin     IEEE JISPIN 2026, Fig. 1, the figure file of the final manuscript
  ipin2022   IPIN 2022, Fig. 5 (a) and (b), the two figure files of the paper,
             clipped to their embedded heat maps and saved as WebP

Requirements: Python 3.11+, PyMuPDF, Pillow, and `pdftocairo` (Poppler, e.g. via
MiKTeX or TeX Live) on PATH.

Usage (from the landing-page root):
    python tools/build_assets.py
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "assets" / "fig"
SRC = ROOT / "_src"
RC = ROOT.parent                                      # the RadioCalibration repository
TUTORIAL_TAG = "submission/comst-2026-11-11"          # 06c0cb6, the submitted 24-pp version
TUT = "Paper/tex/figures"

# (source file in the tutorial at the tag, output name)
TUTORIAL = [
    ("fig_graphical_abstract.pdf", "tutorial-fig1-overview.svg"),          # Fig. 1
    ("fig_topo_a_fully_meshed.pdf", "tutorial-fig3a-fully-meshed.svg"),     # Fig. 3 (a)
    ("fig_topo_b_multi_hop.pdf", "tutorial-fig3b-multi-hop.svg"),           # Fig. 3 (b)
    ("fig_topo_c_mobile_assisted.pdf", "tutorial-fig3c-mobile-assisted.svg"),  # Fig. 3 (c)
    ("fig_topo_d_mobile_only.pdf", "tutorial-fig3d-mobile-only.svg"),       # Fig. 3 (d)
    ("fig_topo_legend.pdf", "tutorial-fig3-legend.svg"),                    # Fig. 3 legend
    ("fig_error_propagation_a_set_b.pdf", "tutorial-fig8a-los.svg"),        # Fig. 8 (a)
    ("fig_error_propagation_b_set_a.pdf", "tutorial-fig8b-nlos.svg"),       # Fig. 8 (b)
    ("fig_decision_tree.pdf", "tutorial-fig12-decision-tree.svg"),          # Fig. 12
    ("fig_release_structure.pdf", "tutorial-fig13-release.svg"),            # Fig. 13
]


def sources() -> dict[str, Path]:
    home = Path.home()
    return {
        # IEEE Access 2026, Fig. 4 (access.tex:526 includes figures/term_frequency.pdf)
        "review_fig4": home / "Nextcloud" / "my-brain" / "Habilitation" / "Collaborative_Self_Calibration"
        / "tex" / "figures" / "term_frequency.pdf",
        # IEEE JISPIN 2026, Fig. 1 (main_rr3.tex:78-82 includes figures/Graphical_abstract.pdf)
        "jispin_fig1": home / "Documents" / "Code" / "autopositioning_torgau" / "Paper" / "figures"
        / "Graphical_abstract.pdf",
        # IPIN 2022, Fig. 5 (a) stationary and (b) non-stationary
        "ipin_fig5a": home / "Nextcloud" / "Veröffentlichungen" / "IPIN 2022" / "grid_variance_range.pdf",
        "ipin_fig5b": home / "Nextcloud" / "Veröffentlichungen" / "IPIN 2022" / "grid_variance_propagation.pdf",
    }


# ------------------------------------------------------------------ helpers
def report(dst: Path) -> None:
    extra = ""
    if dst.suffix == ".webp":
        with Image.open(dst) as im:
            extra = f"  {im.size[0]}x{im.size[1]}"
    print(f"  {dst.relative_to(ROOT)}{extra}  {dst.stat().st_size // 1024} KB")


def pdf_to_svg(pdf: Path, dst: Path) -> None:
    subprocess.run(["pdftocairo", "-svg", str(pdf), str(dst)], check=True)
    report(dst)


def pdf_clip_to_webp(pdf: Path, dst: Path, width: int, clip: fitz.Rect | None = None,
                     quality: int = 86) -> None:
    """Render a page (or a region of it, PDF points) to WebP at the given pixel width."""
    pg = fitz.open(pdf)[0]
    rect = clip or pg.rect
    zoom = width / rect.width
    pix = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=rect, alpha=False)
    Image.frombytes("RGB", (pix.width, pix.height), pix.samples).save(dst, "WEBP", quality=quality,
                                                                      method=6)
    report(dst)


def git_show(rev: str, path: str, dst: Path) -> Path:
    data = subprocess.run(["git", "-C", str(RC), "show", f"{rev}:{path}"], check=True,
                          capture_output=True).stdout
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    return dst


# ------------------------------------------------------------------ figures
def build_figures(src: dict[str, Path]) -> None:
    commit = subprocess.run(["git", "-C", str(RC), "rev-parse", "--short", f"{TUTORIAL_TAG}^{{commit}}"],
                            check=True, capture_output=True, text=True).stdout.strip()
    print(f"tutorial figures from {TUTORIAL_TAG} ({commit})")
    for name, out in TUTORIAL:
        pdf = git_show(TUTORIAL_TAG, f"{TUT}/{name}", SRC / "tutorial" / name)
        pdf_to_svg(pdf, FIG / out)

    print("IEEE Access 2026, Fig. 4")
    pdf_to_svg(src["review_fig4"], FIG / "review-fig4-term-frequency.svg")

    print("IEEE JISPIN 2026, Fig. 1")
    # vector apart from its colour bar; as SVG the many range circles would weigh
    # several megabytes, so it is rendered at twice the display width
    pdf_clip_to_webp(src["jispin_fig1"], FIG / "jispin-fig1-grid-propagation.webp", 1400)

    print("IPIN 2022, Fig. 5")
    for key, out in (("ipin_fig5a", "ipin2022-fig5a-stationary.webp"),
                     ("ipin_fig5b", "ipin2022-fig5b-non-stationary.webp")):
        pg = fitz.open(src[key])[0]
        xref = pg.get_images(full=True)[0][0]
        bbox = pg.get_image_bbox(pg.get_images(full=True)[0])  # the heat map, without the margins
        assert bbox.width > 100, (key, bbox, xref)
        pdf_clip_to_webp(src[key], FIG / out, 720, clip=bbox)


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    FIG.mkdir(parents=True, exist_ok=True)
    src = sources()
    missing = [str(p) for p in src.values() if not p.exists()]
    if missing:
        raise SystemExit("missing sources:\n  " + "\n  ".join(missing))
    build_figures(src)


if __name__ == "__main__":
    main()
