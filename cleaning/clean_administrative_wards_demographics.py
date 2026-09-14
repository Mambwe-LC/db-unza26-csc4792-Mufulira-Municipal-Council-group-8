"""
clean_administrative_wards_demographics.py

Cleans:  data/raw/db-unza26-csc4792-mufulira_administrative_wards_demographics.csv
Writes:  data/clean/db-unza26-csc4792-mufulira_administrative_wards_demographics.csv

Source-specific issues handled:
- 3 rows are District/Constituency-level rollups mixed in among ward rows
  (e.g. "Mufulira District", "Kankoyo Constituency"), with Constituency left
  blank on those rows. We add a `Level` column instead of dropping them, and
  backfill Constituency from the Ward_Name text itself where possible.
- Male_Population, Female_Population, Poverty_Level_Status are 100% missing
  in this extraction - no mean/mode exists for them, so they are left as
  NaN and flagged rather than invented.
"""

import os
import pandas as pd
from cleaning_utils import (
    normalize_missing_sentinels, strip_and_collapse_whitespace,
    impute_numeric_mean, impute_categorical_mode, drop_exact_duplicates,
    missing_value_report, save_clean,
)

RAW_PATH = os.path.join("data", "raw", "db-unza26-csc4792-mufulira_administrative_wards_demographics.csv")
CLEAN_PATH = os.path.join("data", "clean", "db-unza26-csc4792-mufulira_administrative_wards_demographics.csv")


def derive_level_and_constituency(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    def level_of(ward_name):
        if isinstance(ward_name, str) and "district" in ward_name.lower():
            return "District"
        if isinstance(ward_name, str) and "constituency" in ward_name.lower():
            return "Constituency"
        return "Ward"

    df["Level"] = df["Ward_Name"].apply(level_of)

    def fix_constituency(row):
        if pd.notna(row["Constituency"]):
            return row["Constituency"]
        if row["Level"] == "Constituency":
            return row["Ward_Name"].replace("Constituency", "").strip()
        if row["Level"] == "District":
            return "Mufulira"  # district-wide total, not a specific constituency
        return row["Constituency"]

    df["Constituency"] = df.apply(fix_constituency, axis=1)
    return df


def main():
    print("=" * 70)
    print("CLEANING: administrative_wards_demographics")
    print("=" * 70)

    df = pd.read_csv(RAW_PATH, sep="|", dtype=str, encoding="utf-8-sig")
    print(f"Loaded raw: {df.shape[0]} rows x {df.shape[1]} columns")

    df = normalize_missing_sentinels(df)
    df = strip_and_collapse_whitespace(df)
    df = derive_level_and_constituency(df)

    for col in ["Number_of_Households", "Total_Population", "Male_Population", "Female_Population"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print("\nNumeric imputation (mean):")
    df = impute_numeric_mean(df, ["Number_of_Households", "Total_Population",
                                   "Male_Population", "Female_Population"])

    print("\nCategorical imputation (mode):")
    df = impute_categorical_mode(df, ["Poverty_Level_Status"])

    print("\nDeduplication:")
    df = drop_exact_duplicates(df, label="administrative_wards_demographics")

    column_order = ["Level", "Constituency", "Ward_Name", "Number_of_Households",
                     "Total_Population", "Male_Population", "Female_Population",
                     "Poverty_Level_Status"]
    df = df[column_order]

    missing_value_report(df, "administrative_wards_demographics")
    save_clean(df, CLEAN_PATH)


if __name__ == "__main__":
    main()
