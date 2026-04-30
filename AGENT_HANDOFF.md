# Agent Handoff — jp-number-plate-dsproject

Working file for the next Claude Code session. Last updated 2026-04-30.

## TL;DR

Tier-A portfolio polish landed on `portfolio-polish-tier-a` (not yet
merged). Three deliverables: an EDA notebook, a findings section on the
dashboard, and a 19-assertion pytest suite. Pipeline regenerates cleanly,
tests pass, notebook executes end-to-end. Next session: visually
spot-check the dashboard in a browser, then merge to `main` and push.

## Status snapshot

| Surface | Where | State |
|---|---|---|
| Repo | https://github.com/Sting41b/jp-number-plate-dsproject | public; Tier-A work on `portfolio-polish-tier-a` |
| Live dashboard | https://sting41b.github.io/jp-number-plate-dsproject/dashboard/ | still serving the pre-Tier-A version (deploys when branch is merged to `main`) |
| Data pipeline | `scripts/01_scrape_chimei.py` + `scripts/02_clean_and_merge.py` | runs cleanly on plain `python` (Windows + POSIX) |
| Clean data | `data/clean/*.json` | 138 chimei, 119 ご当地, 40+6 hiragana, 13 分類番号 entries |
| EDA notebook | `notebooks/01_explore.ipynb` | 9 code cells, 2 charts, executes end-to-end via `jupyter nbconvert --execute` |
| Test suite | `tests/test_clean_data.py` + `conftest.py` | 19 assertions, `pytest tests/ -v` runs in ~0.1s |

## Recent commits (newest first)

The Tier-A work (notebook, findings section, pytest) is on
`portfolio-polish-tier-a` and not yet committed at the time of this
handoff — see `git status` on the branch for the staged set.

```
51a51b9  Add AGENT_HANDOFF.md for next-session continuity
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

## Done in this session (Tier-A polish, on `portfolio-polish-tier-a`)

- ✅ **EDA notebook** at `notebooks/01_explore.ipynb`. Includes a deliberate
  honesty footnote on the within-office dupes so a reader doesn't trip over
  the inconsistency between "138 rows" and `value_counts()`.
- ✅ **Dashboard findings section** between header and tabs. Three
  keyboard-accessible cards with inline visuals; click navigates to the
  relevant tab via the new `activateTab()` helper in `dashboard/js/main.js`.
- ✅ **pytest suite** at `tests/`. 19 assertions, ~0.1s. No
  `(chimei, office)` uniqueness assertion (verified false on current data
  because of `沖縄`×3 / `長崎`×2 within-office dupes); pinned the dupe counts
  instead so silent dedup changes fail loudly.

## Open follow-ups (priority order)

1. **Browser spot-check of the new findings section.** No agent opened a
   real browser. Confirm: (a) cards render in 3 columns on desktop, 1 column
   below 960px and 640px breakpoints; (b) hover/focus rings show; (c)
   clicking a card scrolls and switches tabs; (d) Card 1's inline bar chart
   renders with kana characters legible. If anything looks off, the
   suspects are `dashboard/css/style.css` (`.findings-grid`,
   `.finding-card`, breakpoint blocks) and the `renderFindings()` function
   in `dashboard/js/main.js`.
2. **Merge `portfolio-polish-tier-a` to `main` and push.** Trigger GitHub
   Pages rebuild. Verify with
   `gh api repos/Sting41b/jp-number-plate-dsproject/pages/builds/latest --jq .status`.
3. **Choropleth map of chimei-per-prefecture.** Currently the only spatial
   view is a table. A Japan-prefecture choropleth would show the geographic
   distribution clearly. Library options: D3 + a Japan TopoJSON, or
   Plotly choropleth with `locationmode="japan"`. Adds a 5th tab or replaces
   the chimei table's header area.
4. **Within-office duplicate analysis.** `長崎`×2 and `沖縄`×3 are now pinned
   in `tests/test_clean_data.py`. To actually disambiguate them, surface
   `地名表示の番号` as a column in `01_scrape_chimei.py` and carry it through
   `02_clean_and_merge.py`. When that lands, update
   `test_chimei_within_office_known_dupes` in the same PR.
5. **Project #2 — modeling-flavoured DS project.** The Tier-A polish made
   this project look more like a DS portfolio piece, but it's still small
   and groupby-heavy. The bigger strategic gap is a project with real
   inferential or modelling content (10k+ row dataset, baseline + model,
   measurable improvement). See plan at
   `~/.claude/plans/lets-talk-about-his-curried-wolf.md`.

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

- **`chimei.json` has *no* field-level unique key.** Two distinct sources
  of non-uniqueness:
  - *Cross-office* (geographic): 富士山 (山梨+静岡) and 知床 (釧路+北見)
    deliberately span two offices each. Don't reintroduce
    `drop_duplicates(subset="chimei")`.
  - *Within-office* (administrative): 沖縄 appears 3× under
    `沖縄総合事務局運輸部`; 長崎 appears 2× under `長崎運輸支局`. The source
    table disambiguates with `地名表示の番号`, which the pipeline does not
    yet carry through. Both invariants are pinned in
    `tests/test_clean_data.py`.
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

None. The `python -m http.server 8765` started during the Tier-A
verification was killed at the end of the session (PID 21864 terminated
via `taskkill`).

## Files most likely to need editing

| For task | Edit |
|---|---|
| Mobile CSS tweaks | `dashboard/css/style.css` (`@media` blocks at the bottom; new `.findings-grid` rules for the findings section) |
| New dashboard panel / chart | `dashboard/index.html` (add a tab + section) and `dashboard/js/main.js` (add a `render…` function and call from `loadAll`) |
| Findings card edits | `renderFindings()` in `dashboard/js/main.js`, `.finding-card` and friends in `dashboard/css/style.css` |
| New data column / source | `scripts/02_clean_and_merge.py` (add a `process_…` function, write to `data/clean/`, register in `summary.json`) |
| Pipeline schema changes | both scripts; remember to run them and commit the regenerated `data/clean/*.json` and `data/raw/chimei_raw.csv` together — and re-run `pytest tests/` |
| Findings update | `README.md`, sections "## Findings" and (if relevant) "Notes"; mirror the change in `notebooks/01_explore.ipynb` and re-execute |
| New test | `tests/test_clean_data.py`; fixtures in `tests/conftest.py` already load each clean JSON once per session |
