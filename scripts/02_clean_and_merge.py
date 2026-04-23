"""
02_clean_and_merge.py
---------------------
Reads all raw data files and produces dashboard-ready JSON in data/clean/.

Input files (data/raw/):
    chimei_raw.csv          — from 01_scrape_chimei.py (run separately)
    bunrui_bangou.json      — hand-coded classification number reference
    hiragana.json           — hand-coded hiragana usage table
    gotochi.csv             — hand-coded ご当地ナンバー timeline

Output files (data/clean/):
    chimei.json             — list of all 地名 with metadata
    bunrui_bangou.json      — cleaned classification ranges
    hiragana.json           — hiragana with computed stats
    gotochi.json            — timeline with cumulative counts
    summary.json            — top-level stats for the dashboard header

Run:
    python scripts/02_clean_and_merge.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

# Windows console defaults to cp1252, which can't encode the Japanese section
# headers we print (=== 地名 ===, etc.). Force UTF-8 on stdout/stderr so the
# script runs on a plain `python scripts/02_clean_and_merge.py` invocation
# without needing PYTHONUTF8=1 set in the environment. No-op on POSIX where
# stdout is already UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

RAW = Path(__file__).parent.parent / "data" / "raw"
CLEAN = Path(__file__).parent.parent / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────
# 1. 地名 (chimei)
# ──────────────────────────────────────────────

def process_chimei() -> list[dict]:
    src = RAW / "chimei_raw.csv"
    if not src.exists():
        print(f"  [SKIP] {src} not found — run 01_scrape_chimei.py first")
        return []

    df = pd.read_csv(src, encoding="utf-8-sig")
    print(f"  chimei_raw: {len(df)} rows, cols={list(df.columns)}")

    # Ensure required column exists
    if "chimei" not in df.columns:
        # Try to auto-detect the 地名 column
        for col in df.columns:
            sample = df[col].dropna().head(5).tolist()
            if any(len(str(v)) <= 6 for v in sample):  # city names tend to be short
                df = df.rename(columns={col: "chimei"})
                print(f"  Auto-renamed '{col}' → 'chimei'")
                break

    # No dedup on chimei alone: some names (e.g. 知床) are legitimately
    # assigned to more than one 運輸支局 (釧路 and 北見), and collapsing those
    # loses real information. Consumers should treat (chimei, office) as the
    # compound key.

    # Normalise gotochi flag
    if "is_gotochi" not in df.columns:
        df["is_gotochi"] = False
    df["is_gotochi"] = df["is_gotochi"].fillna(False).astype(bool)

    # Ensure consistent columns
    for col in ["office", "prefecture", "notes"]:
        if col not in df.columns:
            df[col] = None

    records = df[["chimei", "office", "prefecture", "notes", "is_gotochi"]].to_dict(
        orient="records"
    )
    print(f"  → {len(records)} 地名 records")
    return records


# ──────────────────────────────────────────────
# 2. 分類番号 (bunrui_bangou)
# ──────────────────────────────────────────────

def process_bunrui() -> list[dict]:
    src = RAW / "bunrui_bangou.json"
    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    # Add a display label for the dashboard
    for entry in data:
        if entry["range_start"] is not None:
            entry["label"] = f"{entry['range_start']}–{entry['range_end']}"
            entry["first_digit_label"] = f"{entry['first_digit']}xx"
        else:
            entry["label"] = entry["vehicle_type_ja"]
            entry["first_digit_label"] = "special"

    print(f"  → {len(data)} 分類番号 entries")
    return data


# ──────────────────────────────────────────────
# 3. Hiragana
# ──────────────────────────────────────────────

def process_hiragana() -> dict:
    src = RAW / "hiragana.json"
    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    used = [h for h in data if h["status"] == "used"]
    excluded = [h for h in data if h["status"] == "excluded"]

    # Group exclusions by category
    by_category: dict[str, list] = {}
    for h in excluded:
        by_category.setdefault(h["category"], []).append(h["kana"])

    result = {
        "characters": data,
        "stats": {
            "total_gojuuon": total,
            "used_count": len(used),
            "excluded_count": len(excluded),
            "exclusion_rate": round(len(excluded) / total, 4),
            "exclusion_categories": {
                cat: {"count": len(chars), "examples": chars}
                for cat, chars in by_category.items()
            },
        },
    }
    print(f"  → {len(used)} used / {len(excluded)} excluded hiragana")
    return result


# ──────────────────────────────────────────────
# 4. ご当地ナンバー timeline
# ──────────────────────────────────────────────

def process_gotochi() -> dict:
    src = RAW / "gotochi.csv"
    df = pd.read_csv(src, encoding="utf-8-sig", parse_dates=["issue_date"])

    # Sort by date then name
    df = df.sort_values(["issue_date", "name"]).reset_index(drop=True)

    # Cumulative count by date
    df["cumulative"] = range(1, len(df) + 1)

    # Wave summary
    wave_summary = (
        df.groupby("wave")
        .agg(
            count=("name", "count"),
            issue_date=("issue_date", "first"),
            regions=("region", lambda s: sorted(s.unique().tolist())),
        )
        .reset_index()
        .to_dict(orient="records")
    )
    # Convert Timestamps for JSON serialisation
    for w in wave_summary:
        w["issue_date"] = w["issue_date"].strftime("%Y-%m-%d")

    # Per-region count
    region_counts = df.groupby("region")["name"].count().to_dict()

    records = df.copy()
    records["issue_date"] = records["issue_date"].dt.strftime("%Y-%m-%d")
    # Replace pandas NaN with None so json.dump emits `null`, not the bare
    # `NaN` token — which is not valid JSON and breaks browser JSON.parse.
    records = records.astype(object).where(pd.notna(records), None)
    records_list = records.to_dict(orient="records")

    result = {
        "plates": records_list,
        "wave_summary": wave_summary,
        "region_counts": region_counts,
        "total": len(df),
    }
    print(f"  → {len(df)} ご当地 plates across {len(wave_summary)} waves")
    return result


# ──────────────────────────────────────────────
# 5. Summary (dashboard header stats)
# ──────────────────────────────────────────────

def build_summary(chimei, hiragana, gotochi) -> dict:
    return {
        "total_chimei": len(chimei),
        "total_gotochi": gotochi.get("total", 0),
        "hiragana_used": hiragana["stats"]["used_count"],
        "hiragana_excluded": hiragana["stats"]["excluded_count"],
        "bunrui_ranges": 9,  # standard numbered ranges 1xx–9xx
        "data_sources": [
            {
                "name": "Wikipedia — 日本のナンバープレート一覧",
                "url": "https://ja.wikipedia.org/wiki/日本のナンバープレート一覧",
                "dataset": "chimei",
            },
            {
                "name": "大阪自家用自動車協会 — 分類番号解説",
                "url": "https://daijiren.or.jp/number/",
                "dataset": "bunrui_bangou",
            },
            {
                "name": "国土交通省 — ご当地ナンバープレス",
                "url": "https://www.mlit.go.jp/",
                "dataset": "gotochi",
            },
        ],
    }


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def save(path: Path, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        # allow_nan=False makes json.dump raise on NaN/Infinity instead of
        # silently writing non-standard tokens that break strict parsers.
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"  Saved → {path.name}")


def main():
    print("\n=== 地名 ===")
    chimei = process_chimei()
    if chimei:
        save(CLEAN / "chimei.json", chimei)

    print("\n=== 分類番号 ===")
    bunrui = process_bunrui()
    save(CLEAN / "bunrui_bangou.json", bunrui)

    print("\n=== ひらがな ===")
    hiragana = process_hiragana()
    save(CLEAN / "hiragana.json", hiragana)

    print("\n=== ご当地ナンバー ===")
    gotochi = process_gotochi()
    save(CLEAN / "gotochi.json", gotochi)

    print("\n=== Summary ===")
    summary = build_summary(chimei, hiragana, gotochi)
    save(CLEAN / "summary.json", summary)

    print("\nAll done. Output in data/clean/")


if __name__ == "__main__":
    main()
