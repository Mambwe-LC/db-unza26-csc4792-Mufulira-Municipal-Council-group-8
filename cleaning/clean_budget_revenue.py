"""
clean_budget_revenue.py

Cleans:  data/raw/db-unza26-csc4792_mufulira_budget_revenue_2023_2026.csv
Writes:  data/clean/db-unza26-csc4792-mufulira_budget_revenue_2023_2026.csv

NOTE the filename fix: the raw extraction used an underscore
("csc4792_mufulira") instead of the assignment's required hyphen
("csc4792-mufulira"). We keep the raw file's name exactly as extracted
(for traceability) but correct it in the clean/output version, since that
is the one that must match the naming convention for submission.

Source-specific issues handled:
- 16 rows are leftover PDF table-header text that got misparsed as data
  rows (revenue_source == "CODE", description literally contains the
  column headers). These are detected and dropped.
- budget_amount converted to numeric and mean-imputed only where genuinely
  missing.
- revenue_source is null for most non-"Revenue" data_type rows - that is
  structurally expected (an expenditure line doesn't have a revenue
  source), so it is NOT mode-filled, which would fabricate a value that
  doesn't apply to that row.
"""

import os
import pandas as pd
from cleaning_utils import (
    normalize_missing_sentinels, strip_and_collapse_whitespace, to_numeric,
    impute_numeric_mean, impute_categorical_mode, drop_rows_matching,
    drop_exact_duplicates, missing_value_report, save_clean,
)

RAW_PATH = os.path.join("data", "raw", "db-unza26-csc4792_mufulira_budget_revenue_2023_2026.csv")
CLEAN_PATH = os.path.join("data", "clean", "db-unza26-csc4792-mufulira_budget_revenue_2023_2026.csv")


def main():
    print("=" * 70)
    print("CLEANING: budget_revenue_2023_2026")
    print("=" * 70)

    df = pd.read_csv(RAW_PATH, sep="|", dtype=str, encoding="utf-8-sig")
    print(f"Loaded raw: {df.shape[0]} rows x {df.shape[1]} columns")

    df = normalize_missing_sentinels(df)
    df = strip_and_collapse_whitespace(df)

    # --- Drop leftover table-header rows misparsed as data ---
    header_mask = (df["revenue_source"] == "CODE") | (
        df["description"].str.contains("REVENUE DESCRIPTION", case=False, na=False)
    )
    df = drop_rows_matching(
        df, header_mask,
        reason="row is a leftover PDF table header row (e.g. revenue_source=='CODE'), "
               "not an actual budget line item"
    )

    df["budget_amount"] = to_numeric(df["budget_amount"])
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    print("\nNumeric imputation (mean):")
    df = impute_numeric_mean(df, ["budget_amount"])

    print("\nCategorical imputation (mode) - only for structurally-expected fields:")
    df = impute_categorical_mode(df, ["category", "budget_status"])
    print(
        "  [NOTE] 'revenue_source' is intentionally NOT mode-imputed: it is "
        "genuinely absent (not missing) for non-Revenue rows such as "
        "Expenditure/Budget line items, and filling it would misrepresent "
        "those rows as having a revenue source."
    )

    print("\nDeduplication:")
    df = drop_exact_duplicates(df, label="budget_revenue_2023_2026")

    missing_value_report(df, "budget_revenue_2023_2026")
    save_clean(df, CLEAN_PATH)


if __name__ == "__main__":
    main()
