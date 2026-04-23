"""
01_scrape_chimei.py
-------------------
Scrape the 地名 (regional office name) list from the Japanese Wikipedia article
「日本のナンバープレート一覧」and save a clean CSV.

Run this locally (requires internet access):
    pip install requests pandas lxml
    python scripts/01_scrape_chimei.py

Output: data/raw/chimei_raw.csv
"""

import re
import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

# Windows console defaults to cp1252, which can't encode the Japanese URL /
# table headers we print. Force UTF-8 on stdout/stderr so the script runs on
# a plain `python scripts/01_scrape_chimei.py` invocation without needing
# PYTHONUTF8=1 set in the environment. No-op on POSIX where stdout is already
# UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

URL = "https://ja.wikipedia.org/wiki/日本のナンバープレート一覧"
OUT = Path(__file__).parent.parent / "data" / "raw" / "chimei_raw.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en;q=0.9",
}


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def extract_chimei(html: str) -> pd.DataFrame:
    """
    Wikipedia's 一覧 article contains several tables.
    We want the table(s) listing:
        地名  |  運輸支局 / 自動車検査登録事務所  |  都道府県  |  備考
    Strategy: read ALL tables, keep those whose columns contain '地名' or
    have ≥3 columns where the first contains Japanese city/prefecture names.
    """
    tables = pd.read_html(StringIO(html), flavor="lxml")
    print(f"  Found {len(tables)} tables on page.")

    frames = []
    for i, df in enumerate(tables):
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [" ".join(str(c) for c in col).strip() for col in df.columns]

        col_str = " ".join(str(c) for c in df.columns)
        # Heuristic: table mentions 地名 or 運輸支局 in headers
        if "地名" in col_str or "運輸支局" in col_str or "検査登録" in col_str:
            print(f"  → Table {i}: shape={df.shape}, cols={list(df.columns)}")
            df["_source_table"] = i
            frames.append(df)

    if not frames:
        print("WARNING: No matching tables found — dumping first 5 table shapes for inspection:")
        for i, df in enumerate(tables[:5]):
            print(f"  Table {i}: shape={df.shape}, cols={list(df.columns)[:4]}")
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True)
    return combined


def clean(df: pd.DataFrame) -> pd.DataFrame:
    # The 一覧 table has multiple columns that partially match simple keyword
    # heuristics (e.g. 地名表示, 地名表示の番号, 所在地名 all contain "地名").
    # Pick the most specific column for each target and keep only the first
    # match so we never produce duplicate column names after rename.
    rename_map = {}
    used_targets: set[str] = set()

    def assign(col, target):
        if target not in used_targets:
            rename_map[col] = target
            used_targets.add(target)

    for col in df.columns:
        c = str(col).strip()
        # chimei: prefer 地名表示 (display label) over 地名表示の番号 / 所在地名.
        if "地名表示" in c and "番号" not in c:
            assign(col, "chimei")
        elif c == "地名":
            assign(col, "chimei")
        elif c == "都道府県名" or c == "都道府県":
            assign(col, "prefecture")
        elif "備考" in c or "備注" in c or c.lower() == "note" or c.lower() == "notes":
            assign(col, "notes")

    # Office column is special: the Wikipedia 一覧 table has three columns
    # under the merged "陸事分野の運輸支局 自動車検査登録事務所名" header.
    # pandas disambiguates them as name, name.1, name.2. The FIRST column is
    # the regional 運輸局 (same for every row in a prefecture — useless as a
    # distinguishing field). The SECOND column is the actual 運輸支局 /
    # 自動車検査登録事務所 that issues the plate. Prefer that one.
    office_cols = [
        c for c in df.columns
        if "運輸支局" in str(c) or "検査登録事務所" in str(c)
    ]
    if len(office_cols) >= 2:
        rename_map[office_cols[1]] = "office"
        used_targets.add("office")
    elif office_cols:
        rename_map[office_cols[0]] = "office"
        used_targets.add("office")

    df = df.rename(columns=rename_map)

    # Drop rows where chimei is NaN or repeats the header text
    if "chimei" in df.columns:
        df = df[df["chimei"].notna()]
        df = df[df["chimei"] != "地名"]
        # Wikipedia footnote markers show up in three shapes in this column:
        #   - trailing "*":           苫小牧*, 知床*
        #   - "*" + bracketed ref:    柏* [注 2]
        #   - plain bracketed ref:    いわき[注 1], 尾張小牧[注 3]
        # Strip them all so chimei is just the display string.
        df["chimei"] = (
            df["chimei"].astype(str)
            .str.replace(r"\s*\*.*$", "", regex=True)        # * and everything after
            .str.replace(r"\s*\[[^\]]*\]", "", regex=True)   # [注 N] and similar
            .str.strip()
        )

    # Strip whitespace from all string columns
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda s: s.str.strip() if hasattr(s, "str") else s)

    # Add a flag for ご当地ナンバー if notes column mentions it
    if "notes" in df.columns:
        df["is_gotochi"] = df["notes"].str.contains("ご当地|地方版", na=False)
    else:
        df["is_gotochi"] = False

    return df.reset_index(drop=True)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print(f"Fetching: {URL}")
    html = fetch_html(URL)
    print(f"  Downloaded {len(html):,} chars")

    raw = extract_chimei(html)
    cleaned = clean(raw)

    cleaned.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"\nSaved {len(cleaned)} rows → {OUT}")
    print(cleaned.head(10).to_string())


if __name__ == "__main__":
    main()
