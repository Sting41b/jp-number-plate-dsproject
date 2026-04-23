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

- Windows console encoding: the scraper script prints Japanese URLs/headers.
  It must be run with `PYTHONUTF8=1` (or equivalent) on Windows until a
  `sys.stdout.reconfigure(encoding='utf-8')` is added. Not fixed this session.
- A handful of `chimei` values carry a trailing `*` (footnote marker from
  Wikipedia) — e.g. `苫小牧*`, `知床*`. Left as-is; dashboard can strip.
- `process_chimei()` deduplicates by `chimei` name, so 5 rows were collapsed
  (of 138 scraped → 133 written). Those were genuine duplicates across 運輸支局
  rows, so the behaviour is acceptable for the current data model.
