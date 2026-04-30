"""
Sanity checks on data/clean/*.json — the pipeline output consumed by the
dashboard and the EDA notebook.

Goal: catch silent regressions where the scrape or merge changes the
shape of the data without anyone noticing. A failing test here usually
means scripts/01_scrape_chimei.py or scripts/02_clean_and_merge.py
needs attention, not the test.
"""

from collections import Counter
from datetime import date

import pytest


# ──────────────────────────────────────────────
# chimei.json — the scraped Wikipedia table
# ──────────────────────────────────────────────

CHIMEI_KEYS = {"chimei", "office", "prefecture", "notes", "is_gotochi"}


def test_chimei_is_list_of_dicts(chimei):
    assert isinstance(chimei, list)
    assert all(isinstance(r, dict) for r in chimei)


def test_chimei_row_count(chimei):
    # Exact pin: catches both "Wikipedia changed" and "scraper regressed".
    # Update intentionally if the source table genuinely changes.
    assert len(chimei) == 138


def test_chimei_schema(chimei):
    for r in chimei:
        assert set(r.keys()) == CHIMEI_KEYS, f"Unexpected keys: {set(r.keys())}"


def test_chimei_cross_office_invariant(chimei):
    """富士山 and 知床 each span two offices — see AGENT_HANDOFF.md.

    A `drop_duplicates(subset='chimei')` regression in the pipeline would
    silently collapse these. Pin the office sets explicitly.
    """
    by_chimei: dict[str, set[str]] = {}
    for r in chimei:
        by_chimei.setdefault(r["chimei"], set()).add(r["office"])

    assert by_chimei.get("富士山") == {"山梨運輸支局", "静岡運輸支局"}
    assert by_chimei.get("知床") == {"釧路運輸支局", "北見運輸支局"}


def test_chimei_within_office_known_dupes(chimei):
    """沖縄 (×3) and 長崎 (×2) appear multiple times under a single office.

    The Wikipedia source table disambiguates them via 地名表示の番号, which
    the current pipeline does not carry through. This test pins the
    current behaviour so a silent dedup change fails loudly. If the
    pipeline is later updated to carry the disambiguator, update this
    test in the same PR.
    """
    pair_counts = Counter((r["chimei"], r["office"]) for r in chimei)
    assert pair_counts[("沖縄", "沖縄総合事務局運輸部")] == 3
    assert pair_counts[("長崎", "長崎運輸支局")] == 2


def test_chimei_no_footnote_markers(chimei):
    """Wikipedia footnote markers (* and [注 N]) should be stripped.

    See clean() in 01_scrape_chimei.py. New footnote shapes will silently
    survive — this test catches that.
    """
    bad = [r["chimei"] for r in chimei if any(c in (r["chimei"] or "") for c in "*[]")]
    assert bad == [], f"Footnote markers survived in: {bad}"


# ──────────────────────────────────────────────
# bunrui_bangou.json — vehicle classification ranges
# ──────────────────────────────────────────────

BUNRUI_REQUIRED_KEYS = {
    "first_digit",
    "first_digit_label",
    "label",
    "notes",
    "plate_color",
    "plate_color_en",
    "range_end",
    "range_start",
    "vehicle_type_en",
    "vehicle_type_ja",
}


def test_bunrui_count(bunrui):
    # 13 entries: 9 numbered ranges (1xx–9xx) plus 4 special-purpose rows.
    # See AGENT_HANDOFF.md.
    assert len(bunrui) == 13


def test_bunrui_schema(bunrui):
    for entry in bunrui:
        assert BUNRUI_REQUIRED_KEYS.issubset(entry.keys())
        assert entry["label"]
        assert entry["first_digit_label"]


# ──────────────────────────────────────────────
# hiragana.json — gojūon usage table
# ──────────────────────────────────────────────

VALID_EXCLUSION_CATEGORIES = {"visual", "semantic", "phonetic"}


def test_hiragana_gojuuon_complete(hiragana):
    assert len(hiragana["characters"]) == 46


def test_hiragana_excluded_count(hiragana):
    excluded = [c for c in hiragana["characters"] if c["status"] == "excluded"]
    assert len(excluded) == 6


def test_hiragana_excluded_set(hiragana):
    """The 6 excluded characters are well-documented and shouldn't drift."""
    excluded = {c["kana"] for c in hiragana["characters"] if c["status"] == "excluded"}
    assert excluded == {"お", "と", "の", "へ", "を", "ん"}


def test_hiragana_exclusion_categories(hiragana):
    cats = {c["category"] for c in hiragana["characters"] if c["status"] == "excluded"}
    assert cats <= VALID_EXCLUSION_CATEGORIES, f"Unexpected categories: {cats}"


def test_hiragana_used_have_no_reason(hiragana):
    for c in hiragana["characters"]:
        if c["status"] == "used":
            assert c["exclusion_reason"] is None


# ──────────────────────────────────────────────
# gotochi.json — regional plate timeline
# ──────────────────────────────────────────────

EARLIEST_GOTOCHI = date(2006, 1, 1)


def test_gotochi_count_consistent(gotochi):
    assert gotochi["total"] == len(gotochi["plates"])


def test_gotochi_dates_parse_and_in_range(gotochi):
    today = date.today()
    for p in gotochi["plates"]:
        d = date.fromisoformat(p["issue_date"])
        assert EARLIEST_GOTOCHI <= d <= today, f"Out-of-range date: {p}"


def test_gotochi_three_waves(gotochi):
    """The scheme has had exactly 3 issuance waves so far (2006, 2014, 2019)."""
    assert len(gotochi["wave_summary"]) == 3
    # Wave numbers are 1, 2, 3 in order
    waves = sorted(w["wave"] for w in gotochi["wave_summary"])
    assert waves == [1, 2, 3]


# ──────────────────────────────────────────────
# summary.json — header stats consistency
# ──────────────────────────────────────────────

def test_summary_chimei_matches(summary, chimei):
    assert summary["total_chimei"] == len(chimei)


def test_summary_gotochi_matches(summary, gotochi):
    assert summary["total_gotochi"] == gotochi["total"]


def test_summary_hiragana_sums_to_gojuuon(summary):
    assert summary["hiragana_used"] + summary["hiragana_excluded"] == 46
