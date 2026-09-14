"""
clean_budget_raw_tables.py

Cleans:  data/raw/db-unza26-csc4792_mufulira_budget_raw_tables_2023_2026.csv
Writes:  data/clean/db-unza26-csc4792-mufulira_budget_raw_tables_2023_2026.csv

This file exists purely for traceability/audit - it's the raw table cells
as pulled out of each budget PDF, before they were interpreted into the
structured budget_revenue dataset. It intentionally gets LIGHT cleaning
only (whitespace, dtypes, duplicates) - the individual table_column_*
cells are left as-is, since "cleaning" them further would defeat their
purpose as a raw reference copy.

Same filename fix as clean_budget_revenue.py (underscore -> hyphen after
csc4792) applied to the clean output.
"""

import os
import pandas as pd
from cleaning_utils import (
    normalize_missing_sentinels, strip_and_collapse_whitespace,
    drop_exact_duplicates, missing_value_report, save_clean,
)

RAW_PATH = os.path.join("data", "raw", "db-unza26-csc4792_mufulira_budget_raw_tables_2023_2026.csv")
CLEAN_PATH = os.path.join("data", "clean", "db-unza26-csc4792-mufulira_budget_raw_tables_2023_2026.csv")


def main():
    print("=" * 70)
    print("CLEANING: budget_raw_tables_2023_2026")
    print("=" * 70)

    df = pd.read_csv(RAW_PATH, sep="|", dtype=str, encoding="utf-8-sig")
    print(f"Loaded raw: {df.shape[0]} rows x {df.shape[1]} columns")

    df = normalize_missing_sentinels(df)
    df = strip_and_collapse_whitespace(df)

    for col in ["year", "page", "table_number", "row_number"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    print("\nDeduplication:")
    df = drop_exact_duplicates(df, label="budget_raw_tables_2023_2026")

    missing_value_report(df, "budget_raw_tables_2023_2026")
    save_clean(df, CLEAN_PATH)


if __name__ == "__main__":
    main()
