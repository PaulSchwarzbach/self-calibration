"""Generate the interactive deployment map of UWB-ASC for the project page.

The map is an interactive form of Fig. 2 of the UWB-ASC data descriptor
("Layout of both deployments from the survey and the field labels, with the
logged tag poses of the walks set_b/s01 and s02"). It reads the released files
of UWB-ASC 1.0.0 from the tag v1.0.0 of the descriptor's release repository and
imports the helpers that draw Fig. 2 from validation_figures.py of the same tag,
so the pairs labeled NLOS bend exactly as in the article:

  Data/set_*/nodes.yaml                   surveyed nodes, control points, markers
  Data/set_*/los_nlos_field_labels.csv    pairs labeled NLOS (nlos_segments)
  Data/set_*/masks/mobile_assisted.yaml   the prior subset
  Data/set_b/s01|s02/groundtruth.parquet  logged tag poses, mapped to the survey
  Data/set_b/s01|s02/session.yaml         frame by transform_vicon_to_local

Each deployment is one panel in its own survey frame (the two frames are not
tied to each other), drawn with screen u = x and v = -y. As in Fig. 2, GCP-12
(conflicting shots) and WAND-001 stay out. The poses are drawn as dots, never
joined, so nothing is interpolated across the gaps of the logged stream.

Writes into index.html:
  <!-- DEPLOYMENTS:START --> ... <!-- DEPLOYMENTS:END -->            two panels
  <!-- DEPLOYMENT-TABLE:START --> ... <!-- DEPLOYMENT-TABLE:END -->  node table

Usage (from the landing-page root):
    python tools/make_deployment_map.py
    python tools/make_deployment_map.py --release "../Data Descriptor/Published_repo" --tag v1.0.0
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import io
import re
import subprocess
import sys
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT.parent / "Data Descriptor" / "Published_repo"
TAG = "v1.0.0"
PATHS = ["Data/set_a/nodes.yaml", "Data/set_b/nodes.yaml",
         "Data/set_a/los_nlos_field_labels.csv", "Data/set_b/los_nlos_field_labels.csv",
         "Data/set_a/masks", "Data/set_b/masks",
         "Data/set_b/s01/session.yaml", "Data/set_b/s01/groundtruth.parquet",
         "Data/set_b/s02/session.yaml", "Data/set_b/s02/groundtruth.parquet",
         "Code/descriptor/validation_figures.py", "Code/datasets/radiocal/src"]

DEPLOYMENTS = (("set_b", "los", "LOS deployment"), ("set_a", "nlos", "NLOS deployment"))
POSE_STEP = 3        # every third logged pose; dots only, so no pose is invented
REF_PX = 640         # marker sizes in px at this rendered size of the panel's long side
GRID_M = 5.0


# ------------------------------------------------------------------ inputs
def extract(release: Path, tag: str, dst: Path) -> Path:
    """The files of PATHS at the tag, unpacked into dst (a cache, gitignored)."""
    commit = subprocess.run(["git", "-C", str(release), "rev-parse", f"{tag}^{{commit}}"],
                            check=True, capture_output=True, text=True).stdout.strip()
    out = dst / f"uwb-asc-{tag}"
    stamp = out / ".commit"
    if not (stamp.exists() and stamp.read_text() == commit):
        data = subprocess.run(["git", "-C", str(release), "-c", "core.autocrlf=false", "archive",
                               "--format=tar", tag, *PATHS], check=True, capture_output=True).stdout
        out.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(out, filter="data")
        stamp.write_text(commit)
    print(f"UWB-ASC {tag} = {commit[:7]} from {release}")
    return out


def load_vf(tree: Path):
    """validation_figures.py of the tag, the source of descriptor Fig. 2."""
    path = tree / "Code" / "descriptor" / "validation_figures.py"
    spec = importlib.util.spec_from_file_location("validation_figures_release", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def deployment(tree: Path, vf, c: str) -> dict:
    data = tree / "Data"
    reg = read_yaml(data / c / "nodes.yaml")
    subset = set(read_yaml(data / c / "masks" / "mobile_assisted.yaml")["priors"]["subset"])
    nodes = [nd for nd in reg["nodes"] if nd["prior"]["type"] == "surveyed"]
    rows = []
    for nd in nodes:
        nid = str(nd["id"])
        x, y, z = (float(v) for v in nd["prior"]["xyz_local"])
        if "status" in nd:
            kind, role = "silent", "surveyed node that never ranges"
        elif nid in subset:
            kind, role = "prior", "anchor of the prior subset"
        else:
            kind, role = "anchor", "anchor"
        rows.append(dict(id=nid, kind=kind, role=role, x=x, y=y, z=z))
    cps = reg.get("control_points", [])
    for p in cps:
        name = str(p["name"])
        x, y, z = (float(v) for v in p["xyz_local"])
        if name == "WAND-0-0":
            rows.append(dict(id=name, kind="wand", role="origin of the Vicon frame", x=x, y=y, z=z))
        elif name.startswith("WAND") or p.get("conflict", False):
            continue  # WAND-001 and GCP-12 stay out, as in Fig. 2
        elif name[0] == "P" and name[1:].isdigit():
            rows.append(dict(id=name, kind="marker", role="marker of the roving tag", x=x, y=y, z=z,
                             session=f"s{name[1:]}"))
        else:
            rows.append(dict(id=name, kind="ref", role="control or reference point", x=x, y=y, z=z))
    nlos = vf.nlos_segments(data, c, nodes)

    poses = np.empty((0, 2))
    if c == "set_b":
        Transform = vf.transform_class(data)
        parts = []
        for s in vf.WALKS:
            meta = read_yaml(data / c / s / "session.yaml")
            xyz = pd.read_parquet(data / c / s / "groundtruth.parquet",
                                  columns=["x", "y", "z"]).to_numpy(float)
            parts.append(Transform.from_dict(meta["transform_vicon_to_local"]).apply(xyz)[:, :2])
        poses = np.vstack(parts)

    # the bends of Fig. 2: label_rad with the print scale of the article's panel
    pts = np.array([[r["x"], r["y"]] for r in rows] + list(poses), float)
    lo, hi = pts.min(axis=0) - vf.LAYOUT_PAD_M, pts.max(axis=0) + vf.LAYOUT_PAD_M
    pt_per_m = 72.0 * vf.LAYOUT_AXES_H / (hi[1] - lo[1])
    marks = np.array([[r["x"], r["y"]] for r in rows], float)
    arcs = []
    for ida, idb, a, b in nlos:
        rad = vf.label_rad(a, b, marks, pt_per_m)
        arcs.append((ida, idb, np.asarray(a, float), np.asarray(b, float), rad))

    counts = {k: sum(r["kind"] == k for r in rows) for k in ("anchor", "prior", "silent", "marker")}
    if c == "set_b":
        assert counts["anchor"] + counts["prior"] == 10, counts  # "10 anchors" (descriptor abstract)
        assert counts["silent"] == 1 and counts["marker"] == 0, counts
        assert len(poses) > 10000, len(poses)
    else:
        assert counts["anchor"] + counts["prior"] + counts["silent"] == 12, counts  # "12 nodes"
        assert sorted(r["id"] for r in rows if r["kind"] == "marker") == [f"P{i:02d}" for i in range(1, 21)]
    assert counts["prior"] == 3, counts
    print(f"{c}: {counts}, {len(nlos)} pairs labeled NLOS "
          f"({sum(1 for a in arcs if a[4])} as arcs), {len(poses)} logged poses")
    return dict(rows=rows, arcs=arcs, poses=poses, lo=lo, hi=hi)


# --------------------------------------------------------------------- SVG
def f(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def coords(r: dict) -> str:
    return f'x {r["x"]:.2f} m, y {r["y"]:.2f} m'


def build_svg(d: dict, c: str, key: str, label: str) -> str:
    lo, hi = d["lo"], d["hi"]
    w, h = hi[0] - lo[0], hi[1] - lo[1]
    u0, v0 = lo[0], -hi[1]
    k = max(w, h) / REF_PX           # metres per reference pixel
    r_an, r_hit = 6.0 * k, 11.0 * k
    band = 30 * k                    # strip below the data for the scale bar, so it covers no mark
    L = [f'<svg class="deploymap" viewBox="{f(u0)} {f(v0)} {f(w)} {f(h + band)}" role="img" '
         f'aria-labelledby="dm-{key}-title dm-{key}-desc" xmlns="http://www.w3.org/2000/svg">',
         f'<title id="dm-{key}-title">UWB-ASC, {label}, layout from the survey and the field labels</title>',
         f'<desc id="dm-{key}-desc">Surveyed nodes, control points and pairs labeled NLOS of the '
         f'{label} of UWB-ASC 1.0.0 in its own survey frame'
         + (", with the logged tag poses of the walks s01 and s02" if c == "set_b" else
            ", with the markers of the roving tag of the quasi-static sessions s01 to s20")
         + '. The node table beside the map lists the same positions.</desc>',
         f'<rect class="dm-bg" x="{f(u0)}" y="{f(v0)}" width="{f(w)}" height="{f(h + band)}"/>']
    # reference grid every GRID_M metres, in the survey frame
    g = ['<g class="dm-grid" aria-hidden="true">']
    for x in np.arange(np.ceil(lo[0] / GRID_M) * GRID_M, hi[0], GRID_M):
        g.append(f'<path d="M{f(x)} {f(v0)}V{f(v0 + h)}"/>')
    for y in np.arange(np.ceil(lo[1] / GRID_M) * GRID_M, hi[1], GRID_M):
        g.append(f'<path d="M{f(u0)} {f(-y)}H{f(u0 + w)}"/>')
    g.append("</g>")
    L += g

    if len(d["poses"]):
        pts = d["poses"][::POSE_STEP]
        dots = "".join(f"M{f(x)} {f(-y)}h0" for x, y in pts)
        tip = "Logged tag poses of the walks s01 and s02 (DD98, motion capture), every third pose"
        L.append(f'<g class="dm-layer dm-poses" data-tip="{esc(tip)}"><title>{esc(tip)}</title>'
                 f'<path d="{dots}"/></g>')

    L.append('<g class="dm-layer dm-nlos">')
    for ida, idb, a, b, rad in d["arcs"]:
        if rad:
            ctrl = (a + b) / 2 + rad * np.array([b[1] - a[1], a[0] - b[0]])
            dpath = f"M{f(a[0])} {f(-a[1])}Q{f(ctrl[0])} {f(-ctrl[1])} {f(b[0])} {f(-b[1])}"
        else:
            dpath = f"M{f(a[0])} {f(-a[1])}L{f(b[0])} {f(-b[1])}"
        tip = f"{ida}–{idb} · pair labeled NLOS"
        L.append(f'<g class="dm-pair" data-tip="{esc(tip)}"><title>{esc(tip)}</title>'
                 f'<path class="dm-hit" d="{dpath}"/><path d="{dpath}"/></g>')
    L.append("</g>")

    def node(r: dict, inner: str, cls: str) -> str:
        extra = ""
        if r["kind"] == "marker":
            extra = f' · session {r["session"]}'
        if c == "set_a" and r["id"] == "8B05":
            extra = " · roving tag of the sessions s01 to s20"
        tip = f'{r["id"]} · {r["role"]}{extra} · {coords(r)}'
        u, v = r["x"], -r["y"]
        return (f'<g class="{cls}" data-tip="{esc(tip)}"><title>{esc(tip)}</title>'
                f'<circle class="dm-hit" cx="{f(u)}" cy="{f(v)}" r="{f(r_hit)}"/>{inner}</g>')

    refs, markers, wand, an = [], [], [], []
    for r in d["rows"]:
        u, v = r["x"], -r["y"]
        if r["kind"] == "ref":
            s = 5.6 * k
            pts = f"{f(u)},{f(v - s)} {f(u + 0.95 * s)},{f(v + 0.65 * s)} {f(u - 0.95 * s)},{f(v + 0.65 * s)}"
            refs.append(node(r, f'<polygon points="{pts}"/>', "dm-ref"))
        elif r["kind"] == "marker":
            s = 4.6 * k
            markers.append(node(r, f'<rect x="{f(u - s)}" y="{f(v - s)}" width="{f(2 * s)}" '
                                   f'height="{f(2 * s)}"/>', "dm-marker"))
        elif r["kind"] == "wand":
            s = 4.4 * k
            wand.append(node(r, f'<path d="M{f(u - s)} {f(v - s)}L{f(u + s)} {f(v + s)}'
                                f'M{f(u - s)} {f(v + s)}L{f(u + s)} {f(v - s)}"/>', "dm-wand"))
        elif r["kind"] == "prior":
            s = 7.2 * k
            an.append(node(r, f'<polygon points="{f(u)},{f(v - s)} {f(u + s)},{f(v)} {f(u)},{f(v + s)} '
                              f'{f(u - s)},{f(v)}"/>', "dm-prior"))
        elif r["kind"] == "silent":
            an.append(node(r, f'<circle cx="{f(u)}" cy="{f(v)}" r="{f(r_an)}"/>', "dm-silent"))
        else:
            an.append(node(r, f'<circle cx="{f(u)}" cy="{f(v)}" r="{f(r_an)}"/>', "dm-anchor"))
    L.append('<g class="dm-layer dm-refs">' + "".join(refs + wand) + "</g>")
    L.append('<g class="dm-nodes">' + "".join(an) + "</g>")
    if markers:  # above the anchors, as in Fig. 2, since P01 lies next to the static 8B05
        L.append('<g class="dm-layer dm-markers">' + "".join(markers) + "</g>")

    # 5 m scale bar in the band below the data, bottom left
    sx, sy = u0 + 14 * k, v0 + h + band * 0.55
    L.append(f'<g class="dm-scale" aria-hidden="true"><path d="M{f(sx)} {f(sy)}h5"/>'
             f'<path d="M{f(sx)} {f(sy - 3 * k)}v{f(6 * k)}M{f(sx + 5)} {f(sy - 3 * k)}v{f(6 * k)}"/>'
             f'<text x="{f(sx + 5 + 6 * k)}" y="{f(sy + 4.5 * k)}" '
             f'style="font-size:{f(13 * k)}px">5 m</text></g>')
    L.append("</svg>")
    return "\n".join(L)


def build_panels(ds: dict) -> str:
    out = []
    for c, key, label in DEPLOYMENTS:
        out.append(f'<div class="map-wrap deploy-panel" id="panel-{key}" role="tabpanel" '
                   f'aria-labelledby="tab-{key}" data-set="{c}">')
        out.append(f'<p class="panel-title">{label} <span class="sub-id">{c}</span></p>')
        out.append(build_svg(ds[c], c, key, label))
        out.append('<div class="map-tip" role="status" hidden></div>')
        out.append("</div>")
    return "\n".join(out)


def build_table(ds: dict) -> str:
    out = []
    for c, key, label in DEPLOYMENTS:
        out.append('<div class="table-scroll">')
        out.append(f'<table class="nodes"><caption>{label} ({c}): surveyed positions from '
                   f'<code>Data/{c}/nodes.yaml</code> of UWB-ASC 1.0.0, in the survey frame of '
                   f'the deployment.</caption>')
        out.append('<thead><tr><th scope="col">Id</th><th scope="col">Shown as</th>'
                   '<th scope="col" class="num">x (m)</th><th scope="col" class="num">y (m)</th>'
                   '<th scope="col" class="num">z (m)</th></tr></thead><tbody>')
        order = {"prior": 0, "anchor": 1, "silent": 2, "marker": 3, "ref": 4, "wand": 5}
        for r in sorted(ds[c]["rows"], key=lambda r: (order[r["kind"]], r["id"])):
            out.append(f'<tr><th scope="row">{esc(r["id"])}</th><td>{esc(r["role"])}</td>'
                       f'<td class="num">{r["x"]:.3f}</td><td class="num">{r["y"]:.3f}</td>'
                       f'<td class="num">{r["z"]:.3f}</td></tr>')
        out.append("</tbody></table></div>")
    return "\n".join(out)


def inject(page: Path, marker: str, content: str) -> None:
    text = page.read_text(encoding="utf-8")
    pat = re.compile(rf"(<!-- {marker}:START -->)(.*?)(<!-- {marker}:END -->)", re.S)
    if not pat.search(text):
        raise SystemExit(f"markers {marker} not found in {page}")
    page.write_text(pat.sub(lambda m: m.group(1) + "\n" + content + "\n" + m.group(3), text),
                    encoding="utf-8", newline="\n")
    print(f"injected {marker} into {page.name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", type=Path, default=RELEASE)
    ap.add_argument("--tag", default=TAG)
    args = ap.parse_args()
    tree = extract(args.release, args.tag, ROOT / "_src")
    sys.dont_write_bytecode = True
    vf = load_vf(tree)
    ds = {c: deployment(tree, vf, c) for c, _, _ in DEPLOYMENTS}
    page = ROOT / "index.html"
    inject(page, "DEPLOYMENTS", build_panels(ds))
    inject(page, "DEPLOYMENT-TABLE", build_table(ds))


if __name__ == "__main__":
    main()
