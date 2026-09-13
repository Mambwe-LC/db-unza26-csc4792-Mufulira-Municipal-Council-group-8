"""
clean_cdf_projects.py

Cleans:  data/raw/db-unza26-csc4792-mufulira_cdf_projects.csv
Writes:  data/clean/db-unza26-csc4792-mufulira_cdf_projects.csv

Source-specific issues handled:
- Duration is inconsistently formatted ("8 WEEKS", "8WEEKS", "24WEEKS") -
  parsed into a clean numeric Duration_Weeks column.
- Engineers_Estimate_ZMW / Approved_Amount_ZMW converted to numeric and
  mean-imputed where missing.
- Quantity, Location, Proposed_Date, Justification are 100% empty in this
  extraction - left as NaN and flagged, not invented.
"""

import os
import re
import pandas as pd
from cleaning_utils import (
    normalize_missing_sentinels, strip_and_collapse_whitespace, to_numeric,
    impute_numeric_mean, impute_categorical_mode, drop_exact_duplicates,
    missing_value_report, save_clean,
)

RAW_PATH = os.path.join("data", "raw", "db-unza26-csc4792-mufulira_cdf_projects.csv")
CLEAN_PATH = os.path.join("data", "clean", "db-unza26-csc4792-mufulira_cdf_projects.csv")


def parse_duration_weeks(value):
    if not isinstance(value, str):
        return pd.NA
    match = re.search(r"(\d+)", value)
    return int(match.group(1)) if match else pd.NA


def main():
    print("=" * 70)
    print("CLEANING: cdf_projects")
    print("=" * 70)

    df = pd.read_csv(RAW_PATH, sep="|", dtype=str, encoding="utf-8-sig")
    print(f"Loaded raw: {df.shape[0]} rows x {df.shape[1]} columns")

    df = normalize_missing_sentinels(df)
    df = strip_and_collapse_whitespace(df)

    # Standardize categorical text
    df["Constituency"] = df["Constituency"].str.title()
    df["Sector"] = df["Sector"].str.upper()

    # Duration -> numeric weeks
    df["Duration_Weeks"] = df["Duration"].apply(parse_duration_weeks)
    df["Duration_Weeks"] = pd.to_numeric(df["Duration_Weeks"], errors="coerce")
    df = df.drop(columns=["Duration"])

    # Money columns -> numeric
    df["Engineers_Estimate_ZMW"] = to_numeric(df["Engineers_Estimate_ZMW"])
    df["Approved_Amount_ZMW"] = to_numeric(df["Approved_Amount_ZMW"])

    print("\nNumeric imputation (mean):")
    df = impute_numeric_mean(df, ["Engineers_Estimate_ZMW", "Approved_Amount_ZMW", "Duration_Weeks"])

    print("\nCategorical imputation (mode):")
    df = impute_categorical_mode(df, ["Sector", "Ward"])

    print("\nDeduplication:")
    df = drop_exact_duplicates(df, label="cdf_projects")

    missing_value_report(df, "cdf_projects")
    save_clean(df, CLEAN_PATH)


if __name__ == "__main__":
    main()
