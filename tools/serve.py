"""Serve the page locally for a preview, without browser caching.

`python -m http.server` sends no Cache-Control header, so a browser may reuse a
cached stylesheet with a new page. This server answers with
`Cache-Control: no-store`, so every reload shows the current files.

Usage (from anywhere):
    python tools/serve.py [port]      # default 8765, http://127.0.0.1:8765/
"""

from __future__ import annotations

import functools
import http.server
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NoStore(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    handler = functools.partial(NoStore, directory=str(ROOT))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"serving {ROOT} at http://127.0.0.1:{port}/ (no-store)", flush=True)
        httpd.serve_forever()
