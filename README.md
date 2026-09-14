# Mufulira Municipal Council Data Extraction & Cleaning — README

This project scrapes, extracts, cleans, and preprocesses data from the **Mufulira Municipal
Council** website into structured, pipe-delimited CSV files for data mining. It produces
**8 datasets** across four source areas:

1. **CDF Community Projects** (Kankoyo, Kantanshi, Mufulira Central): extracted via OCR from
   scanned PDFs.
2. **Budgets & Revenue Streams** (2023–2026): extracted via table parsing from digital PDFs
   (produces both a raw table dump and a cleaned revenue/spending dataset).
3. **Skills Development Bursary Applicants** (2025–2026): extracted from digital and scanned
   PDFs using table parsing and OCR.
4. **Mufulira IDP Governance Datasets**: extracted from the Mufulira Municipal Council
   Integrated Development Plan PDF (wards & demographics, health facilities, ward public
   consultation issues, master capital investment framework).

Every dataset then goes through a **separate cleaning and preprocessing stage** (see
Section 6) before being considered final.

---

## Project Structure

```
.
├── scrap.py                     # Runs all 4 extraction scripts, in order
├── clean.py                     # Runs all 8 cleaning scripts, in order
├── scrapping/                   # Extraction scripts (one subfolder per source)
│   ├── idp_scraping/
│   ├── cdf_dataset_scrapping/
│   └── budget_scraper/
├── cleaning/                    # Cleaning & preprocessing scripts (one per dataset)
│   ├── cleaning_utils.py        # Shared helper functions used by every clean_*.py script
│   ├── clean_administrative_wards_demographics.py
│   ├── clean_cdf_projects.py
│   ├── clean_cdf_skills_applicants.py
│   ├── clean_health_facilities.py
│   ├── clean_master_capital_investment_framework.py
│   ├── clean_ward_public_consultation_issues.py
│   ├── clean_budget_revenue.py
│   └── clean_budget_raw_tables.py
├── data/
│   ├── raw/                     # Freshly-scraped CSVs land here (input to clean.py)
│   └── clean/                   # Final, cleaned CSVs land here (submission-ready)
├── db_unza26_csc4792_Mufulira_Municipal_Council.ipynb   # Colab notebook: orchestrates the above + EDA
├── steps_involved_in_creation_of_datasets.ipynb          # Methodology write-up
├── requirements.txt
└── README.md
```

---

## 1. Prerequisites

Before you begin, you must install **two external tools**. They are **not** Python packages —
they are standalone programs that Python calls behind the scenes. Without them, the CDF OCR
step will fail.

### 1.1 Tesseract OCR

Used to read text from the scanned CDF PDF images.

- **Download:** <https://github.com/UB-Mannheim/tesseract/wiki>
- Grab the latest installer, e.g. `tesseract-ocr-w64-setup-5.x.x.exe`.
- **Install to the default location:** `C:\Program Files\Tesseract-OCR\`
- During installation:
  - Tick **"Add to PATH"** if the option is offered.
  - Ensure **English language data** is selected (it is by default).
- **Verify** in a new terminal:
  ```bat
  tesseract --version
  ```
  You should see something like `tesseract v5.x.x`.

### 1.2 Poppler for Windows

Used by `pdf2image` to convert scanned PDF pages into images for OCR.

- **Download:** <https://github.com/oschwartz10612/poppler-windows/releases/>
- Grab the latest `Release-xx.xx.x-0.zip`.
- Extract it, for example to: `C:\poppler\`
- The folder you need is the one containing `pdftoppm.exe`, typically:
  ```
  C:\poppler\Library\bin\
  ```
- **Add this `bin` folder to your system PATH** (see Section 3).
- **Verify** in a new terminal:
  ```bat
  pdftoppm -v
  ```
  You should see `pdftoppm version ...`.

---

## 2. Set Up the Project (Windows, venv)

Open **Command Prompt** or **PowerShell** and navigate to the project folder.

### 2.1 Create a virtual environment

```bat
python -m venv venv
```

### 2.2 Activate the virtual environment

**Command Prompt:**
```bat
venv\Scripts\activate
```

**PowerShell:**
```bat
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks the script, run this once and try again:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

You should now see `(venv)` at the start of your prompt.

### 2.3 Install Python dependencies

```bat
pip install -r requirements.txt
```

---

## 3. Add Poppler and Tesseract to PATH (Recommended)

If you did **not** tick "Add to PATH" during the Tesseract install, do this manually so Python
can find both tools:

1. Press `Win`, type **"Edit the system environment variables"**, and open it.
2. Click **Environment Variables…**
3. Under **User variables** select **Path** → **Edit…** → **New**.
4. Add both:
   ```
   C:\Program Files\Tesseract-OCR
   C:\poppler\Library\bin
   ```
   (Adjust the Poppler path to wherever you extracted it.)
5. Click **OK** on all dialogs.
6. **Close and reopen** your terminal (and VS Code / IDE) so the new PATH takes effect.

---

## 4. Verify the Setup

Run each of these in a fresh terminal (with `(venv)` active):

```bat
tesseract --version
pdftoppm -v
python -c "import pytesseract, pdf2image, pdfplumber, pandas, requests, bs4; print('All good')"
```

If all three commands succeed, you're ready to run the scraper.

---

## 5. Running the Scraper (Extraction)

From inside the project folder, with the virtual environment activated:

```bat
python scrap.py
```

This runs, in order:
`idp_scraper.py` → `cdf_comm_projects_scraper.py` → `cdf_skill_dev_applicants_scraper.py` →
`budget_scraper.py`.

All output files use `|` (pipe) as the delimiter.

> **Note:** raw output should end up in `data/raw/`. If you find the CSVs land in the project
> root folder instead, move them into `data/raw/` before moving on to Section 6 — the cleaning
> scripts read their input from there.

### Raw Output Files (`data/raw/`)

| File | Description |
|------|-------------|
| `db-unza26-csc4792-mufulira_cdf_projects.csv` | Raw CDF community projects |
| `db-unza26-csc4792-mufulira_cdf_skills_applicants.csv` | Raw Skills Development Bursary applicants (2025–2026) |
| `db-unza26-csc4792_mufulira_budget_raw_tables_2023_2026.csv` | Raw tables extracted from the four budget PDFs |
| `db-unza26-csc4792_mufulira_budget_revenue_2023_2026.csv` | Raw budget and revenue records |
| `db-unza26-csc4792-mufulira_administrative_wards_demographics.csv` | Raw administrative ward and demographic data from the IDP |
| `db-unza26-csc4792-mufulira_health_facilities.csv` | Raw health facility data from the IDP |
| `db-unza26-csc4792-mufulira_ward_public_consultation_issues.csv` | Raw ward public consultation issues from the IDP |
| `db-unza26-csc4792-mufulira_master_capital_investment_framework.csv` | Raw master capital investment framework data from the IDP |

---

## 6. Running the Cleaning & Preprocessing Scripts

Once `data/raw/` contains all 8 raw CSVs, run:

```bat
python clean.py
```

This runs the 8 scripts in `cleaning/`, **in a fixed order** (`clean_administrative_wards_
demographics.py` must run before `clean_health_facilities.py`, since the latter backfills its
`Constituency` column from the former's cleaned output). Each script prints a report as it
runs — rows dropped and why, which columns were imputed (and with what value), and which
columns were left null because there was nothing to compute a mean/mode from. Keep this output;
it's useful evidence for the Data Description Paper's methodology section.

What the cleaning stage does, beyond generic "drop duplicates / fill nulls":

- Replaces placeholder text (`"Unspecified"`, `"N/A"`, empty strings, ...) with real `NaN`
  before any missing-value handling happens.
- Converts currency/number-like text columns to proper numeric dtypes.
- **Numeric columns:** missing values filled with the column mean — except where a column is
  100% missing, in which case there's no mean to compute, so it's left `NaN` and flagged in
  the printed output rather than invented.
- **Categorical columns:** missing values filled with the column mode (most frequent value),
  applied only where a value is genuinely missing rather than structurally absent (e.g.
  `revenue_source` is intentionally left blank for non-revenue budget lines, not mode-filled).
- Drops exact duplicate rows.
- Fixes source-specific issues: OCR letter-spacing artifacts, leftover PDF table-header rows
  that leaked in as fake data rows, and corrupted multi-record blob rows in the skills
  applicants source (see comments at the top of each `clean_*.py` script for the specifics).
- Corrects the two budget files' output naming to match the assignment's required convention
  (`csc4792_mufulira` → `csc4792-mufulira`).

### Clean Output Files (`data/clean/`)

| File | Description |
|------|-------------|
| `db-unza26-csc4792-mufulira_administrative_wards_demographics.csv` | Cleaned ward/constituency demographics, with a derived `Level` column |
| `db-unza26-csc4792-mufulira_health_facilities.csv` | Cleaned health facility records |
| `db-unza26-csc4792-mufulira_ward_public_consultation_issues.csv` | Cleaned ward public consultation issues |
| `db-unza26-csc4792-mufulira_master_capital_investment_framework.csv` | Cleaned capital investment framework |
| `db-unza26-csc4792-mufulira_cdf_projects.csv` | Cleaned CDF community projects |
| `db-unza26-csc4792-mufulira_cdf_skills_applicants.csv` | Cleaned skills development applicants |
| `db-unza26-csc4792-mufulira_budget_revenue_2023_2026.csv` | Cleaned budget and revenue records |
| `db-unza26-csc4792-mufulira_budget_raw_tables_2023_2026.csv` | Lightly-cleaned raw table dump (traceability copy) |

These are the files that should be uploaded to Kaggle and referenced in the Data Description
Paper — **not** the files in `data/raw/`.

---

## 7. Using the Notebook

`db_unza26_csc4792_Mufulira_Municipal_Council.ipynb` is a Google Colab notebook that
orchestrates the full pipeline rather than duplicating the scripts' logic:

1. Mounts Google Drive and clones this repo fresh.
2. By default (`REGENERATE_DATASETS = False`), it just loads the CSVs already committed in
   `data/raw/` and `data/clean/` — fast, no scraping needed.
3. If you set `REGENERATE_DATASETS = True`, it instead calls the real extraction and cleaning
   scripts directly (`scrapping/` and `cleaning/`) — useful for demonstrating the pipeline
   end-to-end, but slow (real network scraping + OCR).
4. Documents the raw → clean transformation (row counts, missing-value rates, categorical
   standardization) as evidence the data was actually cleaned, not just scraped.
5. Runs EDA on the final cleaned datasets.

Open it directly in Colab via the badge at the top of the notebook, or upload it manually.

---

## 8. Deactivating the Environment

When you're done:

```bat
deactivate
```

To reactivate later, just re-run `venv\Scripts\activate` from the project folder.
