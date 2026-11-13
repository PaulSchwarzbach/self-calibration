# Infrastructure self-calibration: project page

Source of the project page for Paul Schwarzbach's work on infrastructure self-calibration for
radio-based indoor positioning: the tutorial and its code release radiocal, the UWB-ASC dataset,
the IEEE Access terminology review, the IEEE JISPIN paper on grid-based uncertainty propagation
and the IPIN 2022 paper. The page is a single static HTML file served by GitHub Pages. There is no
build step on GitHub. The scripts in `tools/` and `brand/` regenerate figures, the deployment map
and the logo locally. The page is built on the HYMN project page
(`hymn-localization/Landing Page/`, https://paulschwarzbach.github.io/hymn/).

Live page: `https://paulschwarzbach.github.io/self-calibration/`

## Layout

```
index.html                   the page (logo, deployment map and node table injected between markers)
assets/css/style.css         all styles, light and dark
assets/js/main.js            copy buttons, folding cards, tabs, map tooltips and layer toggles, decision-guide stepper
assets/fonts/                Inter and Source Serif 4, latin subsets, SIL OFL 1.1 (copied from HYMN)
assets/fig/                  paper figures converted to SVG or WebP
assets/img/                  favicon, touch icon, Open Graph image
brand/make_logo.py           logo generator, the canonical source of the logo
brand/logo/                  logo SVGs and PDFs (pdf/), all generated
tools/build_assets.py        paper figures from their original sources
tools/make_deployment_map.py interactive form of descriptor Fig. 2 from UWB-ASC 1.0.0
tools/make_og.py             Open Graph image (headless Edge or Chrome)
tools/stamp_assets.py        ?v= stamps on the stylesheet and script links, from their file hashes
tools/no_runts.py            no-break spaces before the last words of every text block (no runts)
tools/serve.py               local preview without browser caching
tools/check_page.py          checks before a deploy (placeholders, prose, links, guide, stamps, numbers)
```

Local-only folders (gitignored): `_src/` caches extracted sources, the release files of UWB-ASC
and the logo drafts, `brand/logo/png/` holds control renderings.

## Rebuild

Requires Python 3.11+, `numpy`, `pandas`, `pyarrow`, `PyYAML`, `Pillow`, `PyMuPDF`, `fontTools`,
Poppler's `pdftocairo` and a TeX installation with Source Serif 4 (found via `kpsewhich`). The
sources are read relative to this folder, which sits inside the RadioCalibration repository, and
from the home folder (see `tools/build_assets.py`).

```bash
python brand/make_logo.py --png              # logo, favicon, touch icon, inline mark into index.html
python brand/make_logo.py --drafts           # contact sheet of the mark at its sizes (_src/drafts/)
python tools/build_assets.py                 # paper figures
python tools/make_deployment_map.py          # deployment map and node table -> index.html
python tools/no_runts.py                     # after every text edit of index.html
python tools/stamp_assets.py                 # after every edit of style.css or main.js
python tools/serve.py                        # preview at http://127.0.0.1:8765/, never cached
python tools/make_og.py                      # needs the server above
python tools/check_page.py                   # must pass before every deploy
```

`make_logo.py` writes the logo for `CONCEPT` and carries it into the page: favicon, touch icon,
the inline mark in the topbar and the title, and a new `?v=` on both icon links, so browsers drop
a cached icon. Change the logo only in `make_logo.py`, never in the SVGs.

## Updating

| Event | Change |
|---|---|
| Tutorial on arXiv | Done on 2026-11-13 with arXiv:2611.15503 (button, card link, JSON-LD with `datePublished` and the DOI, BibTeX). `check_page.py` still fails on any `PENDING` token. |
| Tutorial accepted or published | Follow IEEE's posting rules for the arXiv version, then change the badge, the status line and the BibTeX to the journal entry with its DOI. |
| Descriptor accepted (IEEE Data Descriptions) | Change the descriptor's note and BibTeX to the article DOI. |
| New version of radiocal or UWB-ASC | Change the version and its DOI in the artifacts table and the BibTeX. The concept DOIs stay. |
| New version of UWB-ASC data | Rerun `make_deployment_map.py --tag <tag>`. |
| Photos cleared by the hall owner and the photographers | Add them with EXIF (incl. GPS) stripped and people unrecognisable, as on the HYMN page. |
| Any edit | Update the "Last updated" date in the footer, run `no_runts.py` after text edits and `stamp_assets.py` after edits of `style.css` or `main.js`, and run `check_page.py`. |

## Deploy (first time)

1. Paul creates the empty public repository `PaulSchwarzbach/self-calibration` in the web UI.
2. The repository-local identity is set (`git config user.email`
   `36500607+PaulSchwarzbach@users.noreply.github.com`), so commits are attributed to the private
   account.
3. `git remote add origin https://PaulSchwarzbach@github.com/PaulSchwarzbach/self-calibration.git`,
   commit, `git push -u origin main`.
4. Pages from `main` / root: `gh api -X POST repos/PaulSchwarzbach/self-calibration/pages -f
   "source[branch]=main" -f "source[path]=/"` (gh by its full path on Windows), or Settings, Pages.
5. About box: homepage URL, description and topics (`gh repo edit`).

## Provenance

Every figure, number and venue string on the page comes from one of the sources below. Paths are
relative to the RadioCalibration repository (`RC`) or to the home folder (`~`). Tutorial sources
are read at the tag `submission/comst-2026-11-11` (06c0cb6), the submitted 24-pp version, which
arXiv posts as 2611.15503v1 with the same words. UWB-ASC files are read at the tag `v1.0.0` (caf8a25) of its release repository
`RC/Data Descriptor/Published_repo`.

### Assets

| Asset | Source | Publication |
|---|---|---|
| `assets/fig/tutorial-fig1-overview.svg` | `RC/Paper/tex/figures/fig_graphical_abstract.pdf` | tutorial Fig. 1 |
| `assets/fig/tutorial-fig3{a,b,c,d}-*.svg`, `tutorial-fig3-legend.svg` | `fig_topo_{a_fully_meshed,b_multi_hop,c_mobile_assisted,d_mobile_only,legend}.pdf` | tutorial Fig. 3 |
| `assets/fig/tutorial-fig8{a-los,b-nlos}.svg` | `fig_error_propagation_{a_set_b,b_set_a}.pdf` | tutorial Fig. 8 |
| `assets/fig/tutorial-fig12-decision-tree.svg` | `fig_decision_tree.pdf` | tutorial Fig. 12 |
| `assets/fig/tutorial-fig13-release.svg` | `fig_release_structure.pdf` | tutorial Fig. 13 |
| `assets/fig/review-fig4-term-frequency.svg` | `~/Nextcloud/my-brain/Habilitation/Collaborative_Self_Calibration/tex/figures/term_frequency.pdf` (`access.tex:526`), compared with p. 9 of the published PDF | IEEE Access 2026 Fig. 4, CC BY 4.0 |
| `assets/fig/jispin-fig1-grid-propagation.webp` | `~/Documents/Code/autopositioning_torgau/Paper/figures/Graphical_abstract.pdf` (`main_rr3.tex:78-82`), rendered at 1400 px | IEEE JISPIN 2026 Fig. 1, CC BY 4.0 (Crossref licence of 10.1109/JISPIN.2026.3687458) |
| `assets/fig/ipin2022-fig5{a-stationary,b-non-stationary}.webp` | `~/Nextcloud/Veröffentlichungen/IPIN 2022/grid_variance_{range,propagation}.pdf`, clipped to the embedded heat map | IPIN 2022 Fig. 5, © 2022 IEEE. The copyright went to IEEE at publication (Paul, 2026-11-12), and Crossref names IEEE's policy. The authors' copy prints "© 2022 European Union" |
| deployment map and node table in `index.html` | `Data/set_{a,b}/nodes.yaml`, `los_nlos_field_labels.csv`, `masks/mobile_assisted.yaml`, `set_b/s0{1,2}/groundtruth.parquet` and `session.yaml` of UWB-ASC 1.0.0, arcs by `Code/descriptor/validation_figures.py` of the same tag | descriptor Fig. 2 |
| logo, favicon, touch icon, topbar and title mark | `brand/make_logo.py`, colours from `RC/Paper/tex/figures/figure_common.tex` | none |
| `assets/img/og-image.png` | `tools/make_og.py` from the logo and tutorial Fig. 1 | none |

### Facts and numbers

| On the page | Source |
|---|---|
| Abstract: anchors, access points, base stations, or reconfigurable intelligent surfaces, at least four communities, the five names ("(SLAM)" added), one factor graph whose factors the measurement topology sets and whose priors carry the reference information | tutorial abstract, `main.tex:127-135` |
| Five works, from a Bayesian grid filter in 2022 to the tutorial with reference implementations and an open UWB dataset in 2026 | the five works on this page (IPIN 2022 to the tutorial preprint of 2026) |
| Fig. 1 caption (shortened: unknown anchors marked ?, a mobile tag, one factor graph, the calibrated anchors and the path of the tag) | tutorial Fig. 1 and its caption, `main.tex:187-196` |
| One operation, twenty names: 20 title terms across 36 papers, most of them used by a single paper (14 of 20), no term has prevailed (no convergence) | IEEE Access 2026 abstract (`access.tex:67-75`) and Section IV-A-1 (`access.tex:518-548`) |
| The operation: estimating the positions of static reference points from range measurements, without manual surveying | IEEE Access 2026 conclusion (`access.tex:895`) |
| 20 title terms, 36 reviewed papers, 70% singleton rate, 137 unique variants, UWB 31 of 36, 100% (2015–2017) to 22% (2022–2026), 461 deduplicated records, four databases 2015 to 2025, the recommendation | IEEE Access 2026 abstract (p. 1, `access.tex:67-75`) and RQ1, RQ5 (`access.tex:111-118`) |
| Four topologies: the lead sentence and the four definitions, shortened and without math | tutorial Fig. 3, Section II-B (`t02:66-73` lead, `t02:77-108` definitions) |
| Two deployments, one with LOS and one rich in NLOS propagation, one industrial hall, UWB two-way ranging | descriptor abstract (`Data Descriptor/Paper/tex/main.tex:74-95`) |
| Three lessons, each with its effect on the anchor error | tutorial `t01:229-231` |
| Lesson titles and sentences (shortened) | titles from the subsection headings `t06:113`, `t06:177`, `t06:221`, sentences from `t06:142-144`, `t06:182-183`, `t06:225-226` |
| 3.94 → 0.79, 4.03 → 0.24, 0.23 → 0.13, 1.88 → 0.36, 0.43 → 0.71 m and the table note | tutorial Table VI (`sections/tab_lessons_effect.tex:9-37`), the last row rises as printed. In the lesson cards, "quadratic loss" stands for the Gaussian kernel (`t06:145`), "randomly thinned meshes that stay globally rigid" for the globally rigid random views of s03, and "the survey as start" for the oracle start |
| Card summaries | tutorial abstract `main.tex:133-141` and `t01:233` (released code recomputes the result tables), JISPIN abstract `main_rr3.tex:68` (graceful degradation against the collapse of closed-form methods), IEEE Access abstract `access.tex:67-75`, IPIN 2022 abstract |
| κ is the thinning level | tutorial Fig. 9 caption (`t06:125-140`) |
| Scope note | tutorial `t06:77-83` |
| Aim of the tutorial | tutorial `t01:107-122` |
| Running example: static session s03, NLOS deployment and the TWR-CLOUD-Bern evaluation scan as contrasts, two dimensions | tutorial `t02:342-362` |
| Tutorial findings list | tutorial contributions `t01:209-234` and abstract `main.tex:134-138` |
| Decision guide, every string | tutorial Fig. 12 (`figures/fig_decision_tree.tex:174-254`), checked by `check_page.py`. The root box ("primitive (Table IV): add its nuisance states") is told in the tree's introduction instead of the stepper |
| Guide lead (the decision tree combines the lessons with the theory) and the tree's introduction (questions about the deployment only, answerable before any algorithm choice) | tutorial `t07:28-35`, Table IV caption `t04:374-375` |
| Fig. 1, 3, 8, 12 and 13 captions | tutorial `main.tex:187-196`, `t03:80-89`, `t06:31-42`, Fig. 12 caption, `main.tex:306-313` |
| JISPIN: vol. 4, pp. 161–170, 2026, CC BY 4.0, title, authors | Crossref record of 10.1109/JISPIN.2026.3687458 |
| JISPIN: equal contribution | `main_rr3.tex:62` |
| JISPIN: question | `main_rr3.tex:139-142` and contribution 4 (`:157`) |
| JISPIN: 12 UWB nodes, fully meshed, industrial hall, total station | `main_rr3.tex:473, 513, 529` |
| JISPIN: the static sessions of the NLOS deployment served this study | descriptor `sections/01_background.tex:139-141` |
| JISPIN: extends the IPIN 2022 formulation | `main_rr3.tex:150-153` (contribution 2) |
| JISPIN: 0.34–0.68 m, 66–92% below 1 m | `main_rr3.tex:631` |
| JISPIN: 0.62–0.99 m against 1.48–2.43 m, outliers beyond 30 m | abstract (`main_rr3.tex:68`), `:319`, conclusion `:652` |
| JISPIN: full availability of PGP, nodes of CF lose availability | `main_rr3.tex:573-575` |
| JISPIN Table III: 0.68, 2.00, 66.1, 0.47, 7.59, 77.2, 0.34, 1.12, 91.6, 0.40, 1.84, 79.4, 0.62, 2.05, 73.3, 2.43, 7.18, 29.9, 0.99, 2.54, 50.3, 1.48, 30.35, 45.2 (median, p95, below 1 m) | `main_rr3.tex:592-614`, columns p75 and mean left out |
| JISPIN: Conf. 1 and 2 from LOS triangles, 3 and 4 with two NLOS links of three | Fig. 7 caption, `main_rr3.tex:477-508` |
| JISPIN: PGP and CF | `main_rr3.tex:541` |
| JISPIN Fig. 1 caption | `main_rr3.tex:78-82` |
| JISPIN: arXiv:2511.10526 (v2 of 2026-04-20 with the final author order) | arXiv API |
| Access: vol. 14, pp. 51603–51619, 2026, CC BY 4.0, published 2 April 2026 | published PDF p. 1, Crossref record of 10.1109/ACCESS.2026.3680224 |
| Access Fig. 4 caption | `access.tex:524-530` |
| IPIN 2022: 12th conference, 5–7 September 2022, Beijing | running header of the paper, Crossref container title |
| IPIN 2022: question, CGP, CF | abstract, p. 3 (CF), p. 4 (CGP) |
| IPIN 2022: 13 nodes, 1,000 epochs per scenario, three scenarios | p. 6, Sec. IV-B (printed "1.000") |
| IPIN 2022: at least 58%, over scenarios from Gaussian LOS noise to multipath errors, outliers and failures | abstract. Table I puts the smallest gain in scenario I (0.41 against 0.17 m) |
| IPIN 2022: RMSE 0.41 against 0.17 m (scenario I), 6.99 against 0.93 m (scenario III) | p. 6 and Table I |
| IPIN 2022: arXiv:2207.08503, BMWK support | arXiv API, acknowledgment p. 8 |
| IPIN 2022 BibTeX | IEEE Xplore BibTeX export (`Collaborative_Self_Calibration/Paper Screening/00_original_downloads/IEEE Xplore Citation BibTeX Download 2026.2.9.22.49.36.bib:241-253`) |
| UWB-ASC: lead sentences, 10 anchors, 12 nodes, 20 quasi-static sessions, a total station surveyed every fixed node, the three parts, 81 frozen draws in 5 conditions, formats | descriptor abstract (`main.tex:74-95`) |
| UWB-ASC: Torgau, Germany | descriptor front matter (`main.tex:101`) |
| UWB-ASC: the HYMN dataset comes from the same hall | descriptor `sections/01_background.tex:113-119` |
| UWB-ASC: Qorvo MDEK1001, DW1000, settings not recorded | descriptor `sections/02_collection_methods.tex:235-244` |
| UWB-ASC: close to planar | descriptor `02_collection_methods.tex:252-258` |
| UWB-ASC: scope and limits | descriptor `sections/05_insights_notes.tex:51-56` |
| UWB-ASC: recording months, March 2025 (NLOS) and October 2025 (LOS) | release README of UWB-ASC 1.0.0, lines 6-7 (2025-03-13, 2025-10-22), not printed in the descriptor |
| UWB-ASC: Python 3.10 or newer, no GPU, install, smoke test, the session example | release README (`main`), lines 52-58, 73, 77, 106. The `git clone` and `cd` lines are added |
| UWB-ASC: version 1.0.0, 10.5281/zenodo.24055896, concept 10.5281/zenodo.24055895, arXiv:2611.11579, submitted to IEEE Data Descriptions, data CC BY 4.0, code MIT | release `CITATION.cff:11-18`, README:16-17 and 390-440, descriptor `04_records_storage.tex:28-29` |
| UWB-ASC: acknowledgement, no grant | descriptor `sections/07_acknowledgements.tex:35-45` |
| radiocal: version 1.0.0, 10.5281/zenodo.24134343, concept 10.5281/zenodo.24134342, code MIT, data and result tables CC BY 4.0 | radiocal `CITATION.cff`, README:546-568 and 644-658, tutorial `main.tex:259-302` |
| radiocal: Python 3.10 or newer, no GPU, install and quick start | radiocal README:122-123, 134-136, 157-164 |
| radiocal: contents | tutorial Data and Code Availability, `main.tex:262-266` |
| Timeline: Sep 2022, Mar 2025, Oct 2025, Apr 2026 (Access, 2 April 2026; JISPIN, Crossref record created 2026-04-24), Nov 2026 (UWB-ASC 1.0.0 on 2026-11-08, tutorial preprint and radiocal 1.0.0 on 2026-11-11) | the rows above, the Zenodo records and the arXiv submissions |
| ORCID iDs: 0000-0002-1091-782X, 0000-0003-1019-6134, 0000-0002-8599-5304 | tutorial `main.tex:97-100`, `main_rr3.tex:59`, HYMN page |
| TUD Dresden University of Technology | the affiliations of all five works (IPIN 2022, JISPIN and Access print the Institute of Traffic Telematics, the tutorial and the descriptor the Chair of Transport Systems Information Technology) |
| Tutorial: arXiv:2611.15503, v1 submitted on 2026-11-11 (`datePublished`), eess.SP, DOI 10.48550/arXiv.2611.15503 | arXiv abstract page, API and OAI-PMH record, read on 2026-11-13 |
| Tutorial BibTeX: arXiv entry, primaryClass eess.SP, note Under review, no venue | `RC/Paper/submission/arxiv_sheet.md:24, 36` (venue-free preprint, category of the upload) |
| The HYMN project page shows photos of the hall | `hymn-localization/Landing Page/index.html`, the photos next to its site map |
| Last updated 13 November 2026 | the date of the edit |

The page deliberately avoids:
- comparing numbers across papers, because their setups and metrics differ,
- any number the papers do not print (no value read off a figure),
- the hall size, since the papers of the hall print different extents,
- JISPIN's ranging numbers 0.28, 3.78 and 1.11 m, which the paper calls mean in some places and
  RMSE in others, and its Table I parameters,
- the success rates and the failure share of IPIN 2022 Table I, whose "(%)" rows hold fractions,
- the review's unused graphical abstract, whose counts differ from the paper,
- photos of the campaigns, until the hall owner and the photographers have agreed.

## Licence

Page text CC BY 4.0, page code MIT (see `LICENSE`). Figures belong to their publications and are
credited in place: those of the IEEE Access and JISPIN papers are CC BY 4.0, those of the tutorial
are the author's, and the IPIN 2022 figure is © 2022 IEEE. Fonts are
under the SIL Open Font License 1.1 (`assets/fonts/OFL-*.txt`). `brand/make_logo.py` is MIT. The
logo may be used unmodified to refer to this work.
