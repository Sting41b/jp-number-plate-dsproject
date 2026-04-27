# 日本のナンバープレート — Japanese number-plate explorer

A small data exploration of how Japanese vehicle license plates encode meaning:
which place names appear, which hiragana are forbidden and why, and how the
optional "regional" plate scheme has rolled out since 2006.

**Live demo:** https://sting41b.github.io/jp-number-plate-dsproject/dashboard/

The dashboard is static HTML/CSS/JS reading JSON produced by a small Python
pipeline. No build step, no server-side anything.

---

## Findings

### 1. Six hiragana are excluded — for three distinct reasons

Of the 46 hiragana in the gojūon, only **40** appear on plates. The 6 exclusions
fall into three categories that map cleanly to types of design failure:

| Category | Excluded | Why |
|---|---|---|
| **Visual** (字形) | お, と, へ | Confusable with another character — お↔あ, と↔う, へ↔katakana へ |
| **Semantic** (語義) | の, を | Read as grammatical particles — "〜の" (possessive), "〜を" (object marker) — would make the plate parse as a phrase |
| **Phonetic** (音韻) | ん | No standalone syllable; sound depends on what follows |

That's a lot of design work hiding in a 6-character exclusion list.

### 2. Regional plates roll out in policy bursts, not gradually

The ご当地ナンバー (regional plate) scheme was introduced in 2006. Looking at the
issue dates of all 119 regional plates:

| Wave | Date | Count |
|---|---|---|
| 1 | 2006-10-10 | 29 |
| 2 | 2014-11-17 | 53 |
| 3 | 2019-05-13 | 37 |

Eight years between Wave 1 and Wave 2, then five years to Wave 3. MLIT only
opens applications periodically — the dashboard's stepped cumulative chart
makes that pattern visible at a glance.

### 3. A few chimei cross prefecture lines

Most place names map 1-to-1 to a single 運輸支局 (transport branch office), but a
handful are shared:

- **富士山** — issued by both **山梨運輸支局** and **静岡運輸支局**. Mt. Fuji
  straddles both prefectures, and the plate name follows the mountain rather
  than the administrative line.
- **知床** — issued by both **釧路運輸支局** and **北見運輸支局**. The Shiretoko
  UNESCO site sits at the edge of both Hokkaidō sub-regions.

This is why `chimei.json` uses `(chimei, office)` as the compound key — `chimei`
alone isn't unique.

---

## Project structure

```
.
├── data/
│   ├── raw/              hand-coded sources + scraped CSV
│   │   ├── bunrui_bangou.json   classification-number reference (hand-coded)
│   │   ├── hiragana.json        46-char gojūon with usage status (hand-coded)
│   │   ├── gotochi.csv          regional-plate timeline (hand-coded)
│   │   └── chimei_raw.csv       scraped from Wikipedia
│   └── clean/            dashboard-ready JSON (pipeline output)
│       ├── chimei.json
│       ├── bunrui_bangou.json
│       ├── hiragana.json
│       ├── gotochi.json
│       └── summary.json
├── scripts/
│   ├── 01_scrape_chimei.py      fetch & parse the 一覧 Wikipedia table
│   └── 02_clean_and_merge.py    normalise all sources → data/clean/
├── dashboard/
│   ├── index.html
│   ├── css/style.css
│   └── js/main.js
├── requirements.txt
└── TEST_RESULTS.md       session-by-session verification log
```

---

## How to run it locally

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the data pipeline

```bash
python scripts/01_scrape_chimei.py     # writes data/raw/chimei_raw.csv
python scripts/02_clean_and_merge.py   # writes data/clean/*.json
```

The scraper fetches `https://ja.wikipedia.org/wiki/日本のナンバープレート一覧`
and is idempotent — re-running it overwrites the CSV with a fresh pull. Both
scripts auto-configure UTF-8 stdout, so they work on plain `python` on Windows
(no `PYTHONUTF8=1` needed).

### 3. Serve the dashboard

```bash
python -m http.server 8765
```

Then open http://127.0.0.1:8765/dashboard/.

The dashboard fetches `../data/clean/*.json`, so it must be served over HTTP
from the project root — opening `dashboard/index.html` via `file://` will fail
silently with a CORS error.

---

## Data sources

| Dataset | Source |
|---|---|
| chimei (regional offices) | [Wikipedia: 日本のナンバープレート一覧](https://ja.wikipedia.org/wiki/日本のナンバープレート一覧) |
| 分類番号 (vehicle classes) | [大阪自家用自動車協会](https://daijiren.or.jp/number/) — hand-transcribed |
| ご当地ナンバー (regional plates) | [国土交通省](https://www.mlit.go.jp/) — hand-transcribed |
| ひらがな usage rules | Multiple references — hand-curated with citations in `data/raw/hiragana.json` |

---

## Tech

- **Pipeline:** Python 3, `pandas`, `requests`, `beautifulsoup4`, `lxml`,
  `html5lib`.
- **Dashboard:** Vanilla HTML/CSS/JS + [Chart.js 4.4.1](https://www.chartjs.org/)
  from jsDelivr. No build step, no framework.
- **Hosting:** GitHub Pages (static serve from `main` branch root).

---

## Notes

This is a learning project — my first data-science project, in fact. The
pipeline and dashboard are both intentionally small and transparent: every
transformation is traceable from raw to clean to rendered.

If you spot a mistake in the data or the explanations, an issue or PR is
welcome.
