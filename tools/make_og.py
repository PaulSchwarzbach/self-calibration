"""Render the Open Graph preview image (assets/img/og-image.png, 1200x630).

Builds a small HTML page from the logo lockup (brand/logo/selfcal-logo.svg) and
tutorial Fig. 1 (assets/fig/tutorial-fig1-overview.svg) and screenshots it with a
headless Chromium browser (Edge or Chrome), as the HYMN page does
(hymn-localization/Landing Page/tools/make_og.py). The page must be served from
the landing-page root, e.g. `python tools/serve.py`.

Usage: python tools/make_og.py [--browser PATH] [--port 8765]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google-chrome", "chromium", "msedge",
]

OG_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<link rel="stylesheet" href="/assets/css/style.css">
<style>
  :root { color-scheme: light; }
  html, body { margin: 0; width: 1200px; height: 630px; overflow: hidden; background: #f9f9f7; color: #0b0b0b; }
  .og { display: grid; grid-template-columns: 1fr 470px; gap: 44px; align-items: center; height: 630px; padding: 0 56px; box-sizing: border-box; }
  .og .logo { width: 100%; height: auto; }
  .og p { font-size: 25px; line-height: 1.42; color: #0b0b0b; margin: 34px 0 0; }
  .og .fig { background: #fff; border-radius: 14px; padding: 14px; box-shadow: 0 0 0 1px rgba(11,11,11,.1); }
  .og .fig img { width: 100%; height: auto; display: block; }
</style></head><body><div class="og">
<div><img class="logo" src="/brand/logo/selfcal-logo.svg" alt="">
<p>A tutorial with reference implementations, an open UWB dataset, a terminology review and two studies of grid-based Bayesian estimation.</p></div>
<div class="fig"><img src="/assets/fig/tutorial-fig1-overview.svg" alt=""></div></div></body></html>"""


def find_browser(explicit: str | None) -> str:
    browser = explicit or next(
        (c for c in CANDIDATES if Path(c).exists() or shutil.which(c)), None)
    if browser is None:
        raise SystemExit("no Chromium-based browser found, pass --browser")
    return browser


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    browser = find_browser(args.browser)
    tmp = ROOT / "_src" / "og.html"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(OG_PAGE, encoding="utf-8")
    out = ROOT / "assets" / "img" / "og-image.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    # an absolute path: a relative one lands in the browser's temporary profile
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--blink-settings=preferredColorScheme=1", "--window-size=1200,630",
                    "--virtual-time-budget=4000", f"--screenshot={out.resolve()}",
                    f"http://127.0.0.1:{args.port}/_src/og.html"],
                   check=True, capture_output=True)
    print("wrote", out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
