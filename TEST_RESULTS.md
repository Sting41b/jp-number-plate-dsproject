# Test Results

## 2026-04-23 — Initial data pipeline verification

### What was verified
End-to-end data pipeline from raw sources to dashboard-ready JSON.

### Commands run
```
python scripts/01_scrape_chimei.py        # live Wikipedia scrape
python scripts/02_clean_and_merge.py      # clean + merge all sources
python -c "import json; ..."              # strict-parse every data/clean/*.json
```

### Results

| Check | Result |
|---|---|
| Dependencies install from `requirements.txt` | PASS |
| `01_scrape_chimei.py` fetches Wikipedia and writes `data/raw/chimei_raw.csv` | PASS — 138 rows |
| `02_clean_and_merge.py` completes without errors | PASS |
| `data/clean/bunrui_bangou.json` strict-parses | PASS — 13 entries |
| `data/clean/chimei.json` strict-parses | PASS — 133 records |
| `data/clean/gotochi.json` strict-parses (previously broken — contained `NaN`) | PASS — 119 plates |
| `data/clean/hiragana.json` strict-parses | PASS — 40 used / 6 excluded |
| `data/clean/summary.json` strict-parses | PASS — `total_chimei` = 133 |
| No `NaN` tokens in any `data/clean/*.json` | PASS |
| `chimei.office` column has distinguishing values (per-運輸支局, not per-運輸局) | PASS — e.g. 札幌運輸支局, 函館運輸支局 |

### Fixes applied this session

1. **`scripts/02_clean_and_merge.py`** — `process_gotochi()` now replaces pandas `NaN`
   with `None` before `to_dict`, so `json.dump` emits `null` instead of the bare
   `NaN` token (which is invalid JSON). `save()` now passes `allow_nan=False` so
   any future NaN leak fails loud.
2. **`scripts/01_scrape_chimei.py`** — `clean()` column mapping rewritten to avoid
   the duplicate-column crash on the real Wikipedia table. Prefers the specific
   sub-column "地名表示" for `chimei`, "都道府県名" for `prefecture`, and the
   second "運輸支局" sub-column (the actual 支局 level, not the regional 運輸局)
   for `office`.

### Known limitations (not blockers)

- `process_chimei()` deduplicates by `chimei` name, so 5 rows were collapsed
  (of 138 scraped → 133 written). Those were genuine duplicates across 運輸支局
  rows, so the behaviour is acceptable for the current data model.
  → **Resolved in follow-up session below.**

---

## 2026-04-23 — Follow-up: known-limitations cleanup

### What was verified
Applied the three known limitations from the previous session. Re-ran the
full pipeline on a plain `python` invocation (no `PYTHONUTF8=1`) and
re-verified every clean JSON.

### Fixes applied

1. **`scripts/01_scrape_chimei.py`** — added `sys.stdout.reconfigure(encoding='utf-8')`
   so the script runs on plain Windows `python` without needing `PYTHONUTF8=1`.
2. **`scripts/02_clean_and_merge.py`** — same UTF-8 stdout reconfigure.
3. **`scripts/01_scrape_chimei.py`** — `clean()` now strips Wikipedia footnote
   markers from chimei values. Covers three shapes: trailing `*` (苫小牧*,
   知床*), `*` + bracketed ref (柏* [注 2]), and plain bracketed ref
   (いわき[注 1], 尾張小牧[注 3]).
4. **`scripts/02_clean_and_merge.py`** — `process_chimei()` no longer dedups
   by `chimei` alone. Dashboards should treat `(chimei, office)` as the
   compound key.

### Results

| Check | Result |
|---|---|
| `python scripts/01_scrape_chimei.py` runs without `PYTHONUTF8=1` | PASS |
| `python scripts/02_clean_and_merge.py` runs without `PYTHONUTF8=1` | PASS |
| `data/clean/chimei.json` strict-parses | PASS — 138 records (up from 133) |
| No chimei value contains `*`, `[`, or `]` | PASS — 0 matches |
| Multi-office chimei entries preserved | PASS — 知床×2 (釧路, 北見), 富士山×2 (山梨, 静岡), 長崎×2, 沖縄×3 |
| All other `data/clean/*.json` still strict-parse | PASS |
| `summary.total_chimei` reflects new count | PASS — 138 |

---

## 2026-04-23 — Dashboard MVP

### What was built
A static vanilla HTML/CSS/JS dashboard that reads the five `data/clean/*.json`
files and renders four tabs: 地名 (searchable table), 分類番号 (reference
table with plate-color swatches), ひらがな (grid of 46 cells with hover
tooltips explaining each exclusion), ご当地 (Chart.js cumulative line chart
+ wave summary). Uses Chart.js v4.4.1 from jsDelivr; no other dependencies.

### Files

- `dashboard/index.html`
- `dashboard/css/style.css`
- `dashboard/js/main.js`

Data is fetched from `../data/clean/` — the dashboard **must be served over
HTTP** from the project root (e.g. `python -m http.server 8765`), not opened
via `file://`.

### HTTP accessibility check

Run from repo root: `python -m http.server 8765`, then:

| URL | Status |
|---|---|
| `/dashboard/index.html` | 200, 3.6 KB |
| `/dashboard/css/style.css` | 200, 5.5 KB |
| `/dashboard/js/main.js` | 200, 6.9 KB |
| `/data/clean/chimei.json` | 200, 20.9 KB |
| `/data/clean/bunrui_bangou.json` | 200, 6.1 KB |
| `/data/clean/hiragana.json` | 200, 7.8 KB |
| `/data/clean/gotochi.json` | 200, 32.4 KB |
| `/data/clean/summary.json` | 200, 0.7 KB |

### Not verified

Visual correctness of rendering (layout, chart, Japanese glyph rendering,
tooltip positioning) was **not** verified — no browser was opened during
this session. The user should eyeball the page and report back if anything
looks off.

---

## 2026-04-30 — Tier-A portfolio polish

### What was built

Three portfolio-readiness deliverables landed on a feature branch
(`portfolio-polish-tier-a`):

1. **A1 — EDA notebook** (`notebooks/01_explore.ipynb`). Re-derives all three
   README findings in pandas with markdown narration and two matplotlib
   charts (hiragana exclusion bar chart, cumulative ご当地 staircase). Adds
   an explicit honesty footnote about the `沖縄`/`長崎` within-office dupes
   and the absent `地名表示の番号` disambiguator. Executed end-to-end and
   committed with outputs.
2. **A2 — Dashboard findings section.** New `<section id="findings">` between
   the header and the tabs nav, with three keyboard-accessible cards. Each
   card states one finding, shows a small inline visual (horizontal-bar SVG
   for hiragana categories, stepped mini-histogram for ご当地 waves, list
   for cross-office chimei), and clicks into the relevant tab via a new
   `activateTab()` helper. Stack vertically below 960px.
3. **A3 — pytest suite** (`tests/`). 19 assertions across schema, shape,
   invariants, and cleanliness. Crucially, no `(chimei, office)` uniqueness
   assertion — the plan flagged this as false on current data, so the
   replacement assertions pin the known dupes (`沖縄 @ 沖縄総合事務局運輸部
   = 3`, `長崎 @ 長崎運輸支局 = 2`) so a silent dedup change fails loudly.

### Results

| Check | Result |
|---|---|
| `pip install -r requirements-dev.txt` succeeds | PASS |
| `pytest tests/ -v` | PASS — 19/19 in 0.10s |
| `jupyter nbconvert --execute --inplace notebooks/01_explore.ipynb` | PASS — 9/9 code cells, 2 PNGs embedded, 75 KB output |
| `node --check dashboard/js/main.js` | PASS — no syntax errors |
| Re-run `scripts/02_clean_and_merge.py` then re-run pytest | PASS — pipeline output stable, 19/19 still pass |
| `python -m http.server 8765`, then HEAD requests on dashboard assets | 200 across `index.html`, `js/main.js`, `css/style.css`, `data/clean/summary.json` |
| Card data simulation against `data/clean/*.json` | PASS — Card 1: visual=3 / semantic=2 / phonetic=1; Card 2: 8.1y + 4.5y wave gaps; Card 3: 知床, 富士山 |

### Not verified

Visual correctness of the new findings section (layout shift between
desktop/mobile breakpoints, hover/focus states on cards, tap targets on
real mobile) was **not** verified in a browser. User should spot-check.

### Out of scope (deferred follow-ups)

- Choropleth of chimei-per-prefecture (Tier B).
- Analytical chapter (stats test on wave inter-arrivals, or clustering — Tier B).
- `地名表示の番号` disambiguation in the pipeline (Tier C; would update
  `test_chimei_within_office_known_dupes` in the same PR).
- GitHub Actions CI for pytest (deferred — judged as not worth the 15
  minutes vs. other portfolio work).
- A second portfolio project covering ML / inference content (the bigger
  strategic gap — see plan).
