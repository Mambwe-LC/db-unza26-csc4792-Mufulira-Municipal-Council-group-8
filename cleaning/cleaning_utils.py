"""
cleaning_utils.py

Shared helper functions used by every dataset-specific cleaning script in
this folder. Nothing in here is dataset-specific — column names, business
rules, etc. all live in the individual clean_*.py scripts.
"""

import re
import numpy as np
import pandas as pd

# Sentinel strings the extraction scripts used in place of a real value.
# These are NOT real data - they must become actual NaN before any
# missing-value handling (imputation, mean/mode, etc.) makes sense.
MISSING_SENTINELS = {"unspecified", "n/a", "na", "none", "null", "-", ""}


def normalize_missing_sentinels(df: pd.DataFrame) -> pd.DataFrame:
    """Replace placeholder strings like 'Unspecified' / '' with real NaN
    across all object (string) columns, so pandas' own null-handling
    (isna, fillna, dropna, mean, mode...) actually sees them as missing."""
    df = df.copy()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].apply(
            lambda v: np.nan
            if isinstance(v, str) and v.strip().lower() in MISSING_SENTINELS
            else v
        )
    return df


def strip_and_collapse_whitespace(df: pd.DataFrame, columns=None) -> pd.DataFrame:
    """Trim leading/trailing whitespace and collapse repeated internal
    whitespace (common OCR artifact) on the given text columns (or all
    object columns if none given)."""
    df = df.copy()
    cols = columns if columns is not None else df.select_dtypes(include="object").columns
    for col in cols:
        df[col] = df[col].apply(
            lambda v: re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else v
        )
    return df


def fix_ocr_letter_spacing(df: pd.DataFrame, columns) -> pd.DataFrame:
    """Fix two common OCR artifacts seen in the scanned PDF sources:
      1. Stray glyphs from bullet/wingding fonts (private-use Unicode
         block, e.g. U+F0B7) that get extracted as garbage characters.
      2. Words broken into individually-spaced letters, e.g.
         'R e h a b i litation' -> collapse the spaced-letter run.
    This is a best-effort text fix, not a full OCR re-run — some rows may
    retain minor residual artifacts, which is expected and documented
    rather than hidden."""
    df = df.copy()

    def _fix(text):
        if not isinstance(text, str):
            return text
        # Strip stray private-use-area glyphs (bullet/symbol font artifacts)
        text = re.sub(r"[\uf000-\uf8ff]", "", text)
        # Collapse runs of 3+ single-character tokens separated by spaces
        text = re.sub(r"\b(?:[A-Za-z]\s){2,}[A-Za-z]\b",
                       lambda m: m.group(0).replace(" ", ""), text)
        # Join a leading single capital letter mistakenly split from the
        # word that follows it (e.g. 'B wananyina' -> 'Bwananyina')
        text = re.sub(r"^([A-Z])\s(?=[a-z]{2,})", r"\1", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    for col in columns:
        if col in df.columns:
            df[col] = df[col].apply(_fix)
    return df


def to_numeric(series: pd.Series) -> pd.Series:
    """Strip currency symbols, thousands separators, and whitespace from a
    text column and coerce it to numeric. Non-numeric leftovers become
    NaN rather than raising - later imputation deals with them."""
    cleaned = series.astype(str).str.replace(r"[^0-9.\-]", "", regex=True)
    cleaned = cleaned.replace("", np.nan)
    return pd.to_numeric(cleaned, errors="coerce")


def impute_numeric_mean(df: pd.DataFrame, columns) -> pd.DataFrame:
    """Fill missing values in numeric columns with that column's mean.
    A column that is 100% missing has no mean to compute - in that case
    we leave it as NaN and print a warning rather than inventing a value
    (e.g. filling with 0), since that would misrepresent the data."""
    df = df.copy()
    for col in columns:
        if col not in df.columns:
            continue
        n_missing_before = df[col].isna().sum()
        if n_missing_before == 0:
            continue
        col_mean = df[col].mean()
        if pd.isna(col_mean):
            print(f"  [WARN] '{col}' is 100% missing — no mean available, "
                  f"left as NaN ({n_missing_before} rows).")
            continue
        df[col] = df[col].fillna(round(col_mean, 2))
        print(f"  [OK] '{col}': filled {n_missing_before} missing value(s) "
              f"with column mean {round(col_mean, 2)}.")
    return df


def impute_categorical_mode(df: pd.DataFrame, columns) -> pd.DataFrame:
    """Fill missing values in categorical/text columns with that column's
    most frequent value (mode) - the categorical equivalent of mean
    imputation. Columns that are 100% missing are left as NaN and flagged,
    same reasoning as impute_numeric_mean."""
    df = df.copy()
    for col in columns:
        if col not in df.columns:
            continue
        n_missing_before = df[col].isna().sum()
        if n_missing_before == 0:
            continue
        mode_vals = df[col].mode(dropna=True)
        if mode_vals.empty:
            print(f"  [WARN] '{col}' is 100% missing — no mode available, "
                  f"left as NaN ({n_missing_before} rows).")
            continue
        fill_val = mode_vals.iloc[0]
        df[col] = df[col].fillna(fill_val)
        print(f"  [OK] '{col}': filled {n_missing_before} missing value(s) "
              f"with column mode '{fill_val}'.")
    return df


def drop_exact_duplicates(df: pd.DataFrame, label="dataset") -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    removed = before - len(df)
    print(f"  [OK] Duplicate rows removed from {label}: {removed} "
          f"({before} -> {len(df)} rows).")
    return df


def drop_rows_matching(df: pd.DataFrame, mask, reason: str) -> pd.DataFrame:
    """Drop rows where `mask` is True, printing how many and why. Used for
    things like leftover table-header rows or corrupted multi-record
    blobs that slipped through extraction as if they were real records."""
    n_drop = int(mask.sum())
    if n_drop:
        print(f"  [OK] Dropped {n_drop} row(s): {reason}.")
    return df.loc[~mask].reset_index(drop=True)


def missing_value_report(df: pd.DataFrame, label: str):
    pct = (df.isna().mean() * 100).round(1)
    print(f"\n  Missing values in '{label}' after cleaning:")
    print(pct[pct > 0].to_string() if (pct > 0).any() else "    (none)")


def save_clean(df: pd.DataFrame, path: str):
    df.to_csv(path, sep="|", index=False, encoding="utf-8-sig")
    print(f"\n  Saved: {path}  ({df.shape[0]} rows x {df.shape[1]} columns)")
