# Mufulira Municipal Council Data Extraction — README

This project scrapes and extracts data from the **Mufulira Municipal Council** website into structured, pipe-delimited CSV files for data mining. It covers two datasets:

1. **CDF Community Projects** (Kankoyo, Kantanshi, Mufulira Central): extracted via OCR from scanned PDFs.
2. **Budgets & Revenue Streams** (2023–2026) — extracted via table parsing from digital PDFs.
3. **Skills Development Bursary Applicants (2025–2026)**:— extracted from digital and scanned PDFs using table parsing and OCR.
4. **Mufulira IDP Governance Datasets (2023–2032)**: extracted from the Mufulira Municipal Council Integrated Development Plan PDF using digital PDF table parsing.

---

## 1. Prerequisites

Before you begin, you must install **two external tools**. They are **not** Python packages — they are standalone programs that Python calls behind the scenes. Without them, the CDF OCR step will fail.

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

Used by `pdf2image` to convert OCR images into Digital PDFs.

- **Download:** <https://github.com/oschwartz10612/poppler-windows/releases/>
- Grab the latest `Release-xx.xx.x-0.zip`.
- Extract it, for example to: `C:\poppler\`
- The folder you need is the one containing `pdftoppm.exe`, typically:
  ```
  C:\poppler\Library\bin\
  ```

- **Add this `bin` folder to your system PATH** (see section 3).
- **Verify** in a new terminal:
  ```bat
  pdftoppm -v
  ```
  You should see `pdftoppm version ...`.

---

## 2. Set Up the Project (Windows, venv)

Open **Command Prompt** or **PowerShell** and navigate to the project folder:

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

If you did **not** tick "Add to PATH" during the Tesseract install, do this manually so Python can find both tools:

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

## 5. Running the Scraper

From inside the project folder, with the virtual environment activated:

```bat
python scrap.py
```
    ```

All output files use `|` (pipe) as the delimiter and are saved in the project folder.

---

## 7. Expected Output

| File | Description |
|------|-------------|
| `db-unza26-csc4792-mufulira_cdf_projects.csv` | Cleaned CDF community projects |
| `db-unza26-csc4792-mufulira_cdf_skills_applicants.csv` | Skills Development Bursary applicants extracted from CDF approved applicants PDFs for 2025–2026 |
| `db-unza26-csc4792-mufulira_budget_raw_tables_2023_2026.csv` | Raw tables from the four budget PDFs |
| `db-unza26-csc4792-mufulira_budget_revenue_2023_2026.csv` | Cleaned budget and revenue records |
| `db-unza26-csc4792-mufulira_administrative_wards_demographics.csv` | Raw administrative ward and demographic data extracted from the Mufulira IDP |
| `db-unza26-csc4792-mufulira_health_facilities.csv` | Raw health facility data extracted from the Mufulira IDP |
| `db-unza26-csc4792-mufulira_ward_public_consultation_issues.csv` | Raw ward public consultation issues extracted from the Mufulira IDP |
| `db-unza26-csc4792-mufulira_master_capital_investment_framework.csv` | Raw master capital investment framework data extracted from the Mufulira IDP |
---

## 8. Deactivating the Environment

When you're done:

```bat
deactivate
```

To reactivate later, just re-run `venv\Scripts\activate` from the project folder.