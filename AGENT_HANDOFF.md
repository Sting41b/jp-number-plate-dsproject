# Agent Handoff — jp-number-plate-dsproject

Working file for the next Claude Code session. Last updated 2026-04-28.

## TL;DR

The project shipped an MVP. Public repo, public dashboard on GitHub Pages,
working end-to-end data pipeline, README with findings. There are no open
bugs. Next work is feature additions and polish, not fixes.

## Status snapshot

| Surface | Where | State |
|---|---|---|
| Repo | https://github.com/Sting41b/jp-number-plate-dsproject | public, on `main` |
| Live dashboard | https://sting41b.github.io/jp-number-plate-dsproject/dashboard/ | served from `main` root via GitHub Pages |
| Data pipeline | `scripts/01_scrape_chimei.py` + `scripts/02_clean_and_merge.py` | runs cleanly on plain `python` (Windows + POSIX) |
| Clean data | `data/clean/*.json` | 138 chimei, 119 ご当地, 40+6 hiragana, 13 分類番号 entries |

## Recent commits (newest first)

```
f529366  Add README with findings, run instructions, and live demo link
3828301  Add static HTML/CSS/JS dashboard MVP
7b52334  Address known pipeline limitations: UTF-8 stdout, footnotes, dedup
33106da  Regenerate data: first chimei scrape + fixed gotochi output
71895c4  Fix pipeline: NaN tokens in JSON and duplicate columns on scrape
c906c8e  Initial commit: Japanese number-plate data pipeline
```

## User context

User identifies this as their first data-science project. They are comfortable
with the engineering side (git, Python, scripting); the gap is in DS
conventions specifically. Frame explanations pedagogically and avoid dropping
DS jargon naked. (See `~/.claude/projects/.../memory/user_role.md`.)

## Open follow-ups (priority order)

These are the suggestions on the table from the last session — none have been
started. Pick whichever the user prioritises.

1. **Mobile / responsive QA.** The CSS has a `@media (max-width: 640px)` block
   but it has not been verified on a real device. User was asked to spot-check.
   If they report issues, the suspect areas are: `.tabs` overflow, `.stats`
   grid, the `.hiragana-grid` cell sizing.
2. **Choropleth map of chimei-per-prefecture.** Currently the only spatial view
   is a table. A Japan-prefecture choropleth would show the geographic
   distribution clearly. Library options: D3 + a Japan TopoJSON, or
   Plotly choropleth with `locationmode="japan"`. Adds a 5th tab or replaces
   the chimei table's header area.
3. **EDA notebook.** `notebooks/01_explore.ipynb` would document the actual
   exploration that informed the README findings — currently those findings
   were derived from quick `python -c` scripts during the last session, with
   no traceable record. A notebook is where most DS work lives.
4. **Within-office duplicate analysis.** `長崎` appears 2× and `沖縄` appears
   3× under the *same* office (different `地名表示の 番号` rows in the source
   table). The pipeline currently doesn't distinguish them. Either de-dup with
   row-number disambiguation, or expose `地名表示の 番号` as a column.
5. **Dashboard "story" mode.** README has 3 findings; dashboard doesn't surface
   any of them. A landing pane summarising the headline findings (with links
   to the relevant tab) would close the gap between the README and the live
   product.

## Local dev quick-reference

```bash
# Pipeline (scrape live Wikipedia + regenerate clean JSON)
pip install -r requirements.txt
python scripts/01_scrape_chimei.py
python scripts/02_clean_and_merge.py

# Dashboard (serves from project root; dashboard fetches ../data/clean/*)
python -m http.server 8765
# then http://127.0.0.1:8765/dashboard/
```

## Gotchas / non-obvious things

- **`(chimei, office)` is the compound key** in `chimei.json`. `chimei` alone
  is not unique — 富士山 (山梨+静岡) and 知床 (釧路+北見) deliberately span
  two offices each. Don't reintroduce `drop_duplicates(subset="chimei")`.
- **Both scripts auto-reconfigure stdout to UTF-8** at import. On Windows you
  do *not* need `PYTHONUTF8=1`. If a future edit prints Japanese before the
  reconfigure block, it will crash with `cp1252` errors.
- **`json.dump` is called with `allow_nan=False`** in `save()` (in
  `02_clean_and_merge.py`). If a future change leaks `pandas` `NaN` into the
  JSON, the script will throw at write time instead of silently producing
  invalid JSON. Don't relax this without a reason.
- **Dashboard requires HTTP serving.** Opening `dashboard/index.html` via
  `file://` triggers a CORS error on `fetch('../data/clean/*.json')`. The
  loading-error UI prints a hint about this.
- **Pages serves from `main` root, not `gh-pages`.** Anything you commit to
  `main` ships to the live site after ~40s of build time. Verify with
  `gh api repos/Sting41b/jp-number-plate-dsproject/pages/builds/latest --jq .status`.
- **Trailing `*` and `[注 N]` footnote markers** in the Wikipedia table are
  stripped by `clean()` in `01_scrape_chimei.py`. New footnote shapes will
  silently survive — re-grep `data/clean/chimei.json` for `[*\[\]]` after
  re-scrapes.

## Background processes that may still be running

A `python -m http.server 8765` was started by the last session (bash ID
`bf2wex6ez`, bound to `127.0.0.1`). It serves the local copy of the
dashboard. Harmless if left running, but the user can `Ctrl+C` it or kill
the process if they want the port back.

## Files most likely to need editing

| For task | Edit |
|---|---|
| Mobile CSS tweaks | `dashboard/css/style.css` (specifically `@media (max-width: 640px)` and `.hiragana-grid`) |
| New dashboard panel / chart | `dashboard/index.html` (add a tab + section) and `dashboard/js/main.js` (add a `render…` function and call from `loadAll`) |
| New data column / source | `scripts/02_clean_and_merge.py` (add a `process_…` function, write to `data/clean/`, register in `summary.json`) |
| Pipeline schema changes | both scripts; remember to run them and commit the regenerated `data/clean/*.json` and `data/raw/chimei_raw.csv` together |
| Findings update | `README.md`, sections "## Findings" and (if relevant) "Notes" |
