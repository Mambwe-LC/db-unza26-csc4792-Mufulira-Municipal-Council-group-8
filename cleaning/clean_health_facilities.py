"""
clean_health_facilities.py

Cleans:  data/raw/db-unza26-csc4792-mufulira_health_facilities.csv
Writes:  data/clean/db-unza26-csc4792-mufulira_health_facilities.csv

Source-specific issues handled:
- Constituency is "Unspecified" for every row in this extraction, even
  though Ward is known - we backfill Constituency from a Ward->Constituency
  lookup built from the (already-cleaned) wards_demographics dataset,
  rather than inventing a value.
- Catchment_Population is 100% empty - left as NaN and flagged.
"""

import os
import pandas as pd
from cleaning_utils import (
    normalize_missing_sentinels, strip_and_collapse_whitespace,
    impute_numeric_mean, drop_exact_duplicates, missing_value_report,
    save_clean,
)

RAW_PATH = os.path.join("data", "raw", "db-unza26-csc4792-mufulira_health_facilities.csv")
CLEAN_WARDS_PATH = os.path.join("data", "clean", "db-unza26-csc4792-mufulira_administrative_wards_demographics.csv")
CLEAN_PATH = os.path.join("data", "clean", "db-unza26-csc4792-mufulira_health_facilities.csv")


def build_ward_to_constituency_lookup():
    """Reuses the already-cleaned wards dataset (run
    clean_administrative_wards_demographics.py first) to map a Ward name
    back to its Constituency, instead of guessing."""
    if not os.path.exists(CLEAN_WARDS_PATH):
        print("  [WARN] Clean wards_demographics file not found - run that "
              "script first for Constituency backfill to work. Skipping backfill.")
        return {}
    wards_df = pd.read_csv(CLEAN_WARDS_PATH, sep="|", dtype=str)
    wards_df = wards_df[wards_df["Level"] == "Ward"]
    return dict(zip(wards_df["Ward_Name"], wards_df["Constituency"]))


def main():
    print("=" * 70)
    print("CLEANING: health_facilities")
    print("=" * 70)

    df = pd.read_csv(RAW_PATH, sep="|", dtype=str, encoding="utf-8-sig")
    print(f"Loaded raw: {df.shape[0]} rows x {df.shape[1]} columns")

    df = normalize_missing_sentinels(df)
    df = strip_and_collapse_whitespace(df)

    lookup = build_ward_to_constituency_lookup()
    n_backfilled = 0
    if lookup:
        def backfill(row):
            nonlocal n_backfilled
            if pd.isna(row["Constituency"]) and row["Ward"] in lookup:
                n_backfilled += 1
                return lookup[row["Ward"]]
            return row["Constituency"]
        df["Constituency"] = df.apply(backfill, axis=1)
        print(f"  [OK] Backfilled Constituency from Ward for {n_backfilled} row(s).")

    df["Catchment_Population"] = pd.to_numeric(df["Catchment_Population"], errors="coerce")
    print("\nNumeric imputation (mean):")
    df = impute_numeric_mean(df, ["Catchment_Population"])

    print("\nDeduplication:")
    df = drop_exact_duplicates(df, label="health_facilities")

    missing_value_report(df, "health_facilities")
    save_clean(df, CLEAN_PATH)


if __name__ == "__main__":
    main()
