"""
clean_cdf_skills_applicants.py

Cleans:  data/raw/db-unza26-csc4792-mufulira_cdf_skills_applicants.csv
Writes:  data/clean/db-unza26-csc4792-mufulira_cdf_skills_applicants.csv

Source-specific issues handled:
- This is the messiest raw source in the project. A subset of the source
  PDFs used a table layout the extraction script did not fully parse into
  separate columns, so entire multi-applicant table blocks ended up dumped
  into a single Name_of_Pupil cell for some rows.
- We detect and drop those clearly-corrupted "multi-record blob" rows
  (heuristic: more than one NRC-shaped pattern found inside the text, or
  the text is implausibly long for a single name).
- IMPORTANT / LIMITATION: this is a data-cleaning fix, not an extraction
  fix. Rows that survive this filter may still have Name_of_Pupil holding
  more than just a bare name (e.g. programme/institution text mixed in),
  because the underlying extraction script did not split that source PDF
  layout into separate fields. That is flagged here explicitly rather than
  silently left for someone to discover later - it belongs in the Data
  Description Paper's limitations section.
"""

import os
import re
import pandas as pd
from cleaning_utils import (
    normalize_missing_sentinels, strip_and_collapse_whitespace,
    drop_rows_matching, drop_exact_duplicates, missing_value_report,
    save_clean,
)

RAW_PATH = os.path.join("data", "raw", "db-unza26-csc4792-mufulira_cdf_skills_applicants.csv")
CLEAN_PATH = os.path.join("data", "clean", "db-unza26-csc4792-mufulira_cdf_skills_applicants.csv")

NRC_PATTERN = re.compile(r"\d{5,7}\s*/\s*\d{2}\s*/\s*\d")
MAX_PLAUSIBLE_NAME_LENGTH = 400


def main():
    print("=" * 70)
    print("CLEANING: cdf_skills_applicants")
    print("=" * 70)

    df = pd.read_csv(RAW_PATH, sep="|", dtype=str, encoding="utf-8-sig")
    print(f"Loaded raw: {df.shape[0]} rows x {df.shape[1]} columns")

    df = normalize_missing_sentinels(df)
    df = strip_and_collapse_whitespace(df)

    # --- Drop corrupted multi-record blob rows ---
    name_col = df["Name_of_Pupil"].fillna("")
    nrc_hits = name_col.apply(lambda s: len(NRC_PATTERN.findall(s)))
    too_long = name_col.str.len() > MAX_PLAUSIBLE_NAME_LENGTH
    blob_mask = (nrc_hits > 1) | too_long
    df = drop_rows_matching(
        df, blob_mask,
        reason="Name_of_Pupil contained more than one NRC-shaped pattern "
               "or was implausibly long - almost certainly a multi-applicant "
               "table block that the extraction step failed to split apart"
    )

    print(
        "\n  [NOTE] Remaining rows are NOT guaranteed to have a clean, "
        "single Name_of_Pupil value - some source PDFs were not fully "
        "parsed into separate fields by the extraction script. This is "
        "documented as a known limitation rather than papered over."
    )

    # Standardize what IS reliably structured
    df["Constituency"] = df["Constituency"].str.title()
    df["Gender"] = df["Gender"].str.upper().str[:1]  # normalize Female/F/female -> "F"
    df["Gender"] = df["Gender"].where(df["Gender"].isin(["M", "F"]), pd.NA)

    print("\nDeduplication:")
    df = drop_exact_duplicates(df, label="cdf_skills_applicants")

    missing_value_report(df, "cdf_skills_applicants")
    save_clean(df, CLEAN_PATH)


if __name__ == "__main__":
    main()
