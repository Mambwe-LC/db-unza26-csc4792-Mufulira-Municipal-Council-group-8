"""
clean_ward_public_consultation_issues.py

Cleans:  data/raw/db-unza26-csc4792-mufulira_ward_public_consultation_issues.csv
Writes:  data/clean/db-unza26-csc4792-mufulira_ward_public_consultation_issues.csv

Source-specific issues handled:
- OCR letter-spacing artifacts (e.g. "R e h a b i litation" -> "Rehabilitation")
  and stray bullet-font glyphs (e.g. U+F0B7) prefixed on Challenges/Solutions.
- Sector is missing for every row - mode-imputed since it's a small,
  low-cardinality categorical column (documented, not silently filled).
"""

import os
import pandas as pd
from cleaning_utils import (
    normalize_missing_sentinels, strip_and_collapse_whitespace,
    fix_ocr_letter_spacing, impute_categorical_mode, drop_exact_duplicates,
    missing_value_report, save_clean,
)

RAW_PATH = os.path.join("data", "raw", "db-unza26-csc4792-mufulira_ward_public_consultation_issues.csv")
CLEAN_PATH = os.path.join("data", "clean", "db-unza26-csc4792-mufulira_ward_public_consultation_issues.csv")


def main():
    print("=" * 70)
    print("CLEANING: ward_public_consultation_issues")
    print("=" * 70)

    df = pd.read_csv(RAW_PATH, sep="|", dtype=str, encoding="utf-8-sig")
    print(f"Loaded raw: {df.shape[0]} rows x {df.shape[1]} columns")

    df = normalize_missing_sentinels(df)
    df = strip_and_collapse_whitespace(df)
    df = fix_ocr_letter_spacing(df, ["Ward_Name", "Challenges", "Solutions"])

    print("\nCategorical imputation (mode):")
    df = impute_categorical_mode(df, ["Sector"])

    print("\nDeduplication:")
    df = drop_exact_duplicates(df, label="ward_public_consultation_issues")

    missing_value_report(df, "ward_public_consultation_issues")
    save_clean(df, CLEAN_PATH)


if __name__ == "__main__":
    main()
