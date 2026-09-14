"""
clean_master_capital_investment_framework.py

Cleans:  data/raw/db-unza26-csc4792-mufulira_master_capital_investment_framework.csv
Writes:  data/clean/db-unza26-csc4792-mufulira_master_capital_investment_framework.csv

This is the cleanest of the 8 raw sources - mostly whitespace/sentinel
normalization and numeric conversion, with mean imputation available for
the rare missing Cost_ZMW value (none in the current extraction, but the
step is kept so future re-scrapes are handled automatically).
"""

import os
import pandas as pd
from cleaning_utils import (
    normalize_missing_sentinels, strip_and_collapse_whitespace, to_numeric,
    impute_numeric_mean, impute_categorical_mode, drop_exact_duplicates,
    missing_value_report, save_clean,
)

RAW_PATH = os.path.join("data", "raw", "db-unza26-csc4792-mufulira_master_capital_investment_framework.csv")
CLEAN_PATH = os.path.join("data", "clean", "db-unza26-csc4792-mufulira_master_capital_investment_framework.csv")


def main():
    print("=" * 70)
    print("CLEANING: master_capital_investment_framework")
    print("=" * 70)

    df = pd.read_csv(RAW_PATH, sep="|", dtype=str, encoding="utf-8-sig")
    print(f"Loaded raw: {df.shape[0]} rows x {df.shape[1]} columns")

    df = normalize_missing_sentinels(df)
    df = strip_and_collapse_whitespace(df)

    df["Sector"] = df["Sector"].str.title()
    df["Cost_ZMW"] = to_numeric(df["Cost_ZMW"])

    print("\nNumeric imputation (mean):")
    df = impute_numeric_mean(df, ["Cost_ZMW"])

    print("\nCategorical imputation (mode):")
    df = impute_categorical_mode(df, ["Sector", "Proposed_Source_of_Funds", "Responsible_Agency"])

    print("\nDeduplication:")
    df = drop_exact_duplicates(df, label="master_capital_investment_framework")

    missing_value_report(df, "master_capital_investment_framework")
    save_clean(df, CLEAN_PATH)


if __name__ == "__main__":
    main()
