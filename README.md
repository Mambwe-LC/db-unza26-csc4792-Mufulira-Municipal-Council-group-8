# Mufulira Municipal Council Data Extraction & Cleaning

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

---

## Data Extraction Steps

- [steps during data extraction](steps_involved_in_creation_of_datasets.ipynb)

---

## Team Roles and Responsibilities

The following team members were responsible for different components of this data mining project:

| Team Member | Computer Number | Role | Responsibilities |
|-------------|-----------------|------|------------------|
| **Moses Kaluba** | `2021387283` | Team Lead / Data Extraction & Mining | Led the team and coordinated the overall data mining activities. Responsible for extracting data from the identified sources and carrying out the data mining processes. |
| **Kalebalika Chileshe** | `2021452344` | EDA & Data Cleaning | Responsible for Exploratory Data Analysis (EDA) and cleaning of the extracted datasets. |
| **Mambwe Luke Chilebela** | `2021480348` | EDA & Data Cleaning | Responsible for Exploratory Data Analysis (EDA) and cleaning of the extracted datasets. |
| **Kasonkomona Mulenga** | `2021519929` | Data Brief Documentation | Responsible for writing and documenting the data brief description paper. |
| **Ephetred Ndhlovu** | `2021463681`| Data Brief Documentation | Responsible for writing and documenting the data brief description paper. |

### Team Contribution Summary

- **Team Leadership:** Moses Kaluba coordinated the team and oversaw the completion of the project activities and performed Data Extraction and Mining
- **Data Cleaning and EDA:** Kalebalika Chileshe and Mambwe Luke Chilebela were responsible for preparing the extracted datasets through data cleaning and conducting Exploratory Data Analysis.
- **Data Brief Description:** Kasonkomona Mulenga and Ephetred Ndhlovu were responsible for preparing the written data brief description paper documenting the datasets and their characteristics.

## 1. Prerequisites for running the data extraction scripts

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


## 8. Deactivating the Environment

When you're done:

```bat
deactivate
```

To reactivate later, just re-run `venv\Scripts\activate` from the project folder.
