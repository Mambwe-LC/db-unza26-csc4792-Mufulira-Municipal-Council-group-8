import os
import io
import re
import requests
import pdfplumber
import pandas as pd

import urllib3

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


# ============================================================
# CONFIGURATION
# ============================================================

PDF_DOCUMENTS = [
    {
        "year": 2023,
        "url": (
            "https://www.mufuliracouncil.gov.zm/"
            "wp-content/uploads/2025/12/"
            "Approved-Budget-2023.pdf"
        )
    },
    {
        "year": 2024,
        "url": (
            "https://www.mufuliracouncil.gov.zm/"
            "wp-content/uploads/2025/12/"
            "Approved-Budget-2024.pdf"
        )
    },
    {
        "year": 2025,
        "url": (
            "https://www.mufuliracouncil.gov.zm/"
            "wp-content/uploads/2025/03/"
            "Approved-2025-Budget.pdf"
        )
    },
    {
        "year": 2026,
        "url": (
            "https://www.mufuliracouncil.gov.zm/"
            "wp-content/uploads/2026/08/"
            "Mufulira-2026-OBB-Budget-17.12.2025.pdf"
        )
    }
]


# ============================================================
# OUTPUT FILES
# ============================================================

OUTPUT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

FINAL_CSV = os.path.join(
    OUTPUT_DIR,
    "db-unza26-csc4792_mufulira_budget_revenue_2023_2026.csv"
)

RAW_CSV = os.path.join(
    OUTPUT_DIR,
    "db-unza26-csc4792_mufulira_budget_raw_tables_2023_2026.csv"
)


SOURCE_TYPE = "Annual Budget"


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    )
})


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    value = str(value)

    value = value.replace("\n", " ")
    value = value.replace("\r", " ")

    value = re.sub(r"\s+", " ", value)

    return value.strip()


# ============================================================
# CLEAN AMOUNT
# ============================================================

def clean_amount(value):

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = value.replace(",", "")
    value = value.replace(" ", "")

    value = value.replace("ZMW", "")
    value = value.replace("K", "")

    value = re.sub(
        r"[^0-9.\-]",
        "",
        value
    )

    if not value:
        return None

    try:

        return float(value)

    except ValueError:

        return None


# ============================================================
# ROW TEXT
# ============================================================

def row_text(row):

    return " ".join(
        clean_text(value).lower()
        for value in row
        if clean_text(value)
    )


# ============================================================
# RELEVANT ROW
# ============================================================

def is_relevant_row(row):

    text = row_text(row)

    keywords = [

        "revenue",

        "revenue source",

        "local tax",

        "local taxes",

        "rates",

        "property rates",

        "residential rates",

        "industrial",

        "commercial",

        "mining",

        "market fees",

        "market",

        "parking fees",

        "parking",

        "bus station",

        "bus station fees",

        "levy",

        "levies",

        "fees and charges",

        "consent fees",

        "survey fees",

        "building inspection fees",

        "licence",

        "license",

        "licences",

        "licenses",

        "permits",

        "rent",

        "lease",

        "lgef",

        "local government equalisation fund",

        "equalisation fund",

        "expenditure",

        "expenditure estimate",

        "budget",

        "subitem total",

        "total revenue"

    ]

    return any(
        keyword in text
        for keyword in keywords
    )


# ============================================================
# BUDGET STATUS
# ============================================================

def detect_budget_status(row):

    text = row_text(row)

    if "revised" in text:

        return "Revised Budget"

    if "approved" in text:

        return "Approved Budget"

    if "estimate" in text:

        return "Budget Estimate"

    if "projection" in text:

        return "Budget Projection"

    if "actual" in text:

        return "Actual"

    return None


# ============================================================
# CATEGORY
# ============================================================

def detect_category(
    row,
    previous_category
):

    text = row_text(row)

    if "fees and charges" in text:

        return "Fees and Charges"

    if (
        "local tax" in text
        or "local taxes" in text
    ):

        return "Local Taxes / Rates"

    if "rates" in text:

        return "Local Taxes / Rates"

    if (
        "lgef" in text
        or "equalisation fund" in text
    ):

        return "LGEF"

    if "expenditure" in text:

        return "Expenditure"

    if "capital" in text:

        return "Capital Expenditure"

    if "personal emoluments" in text:

        return "Personal Emoluments"

    if "goods and services" in text:

        return "Goods and Services"

    if "grant" in text:

        return "Grants"

    return previous_category


# ============================================================
# REVENUE SOURCE
# ============================================================

def detect_revenue_source(
    row,
    category
):

    values = [
        clean_text(value)
        for value in row
        if clean_text(value)
    ]

    if not values:

        return ""

    text = " ".join(values).lower()

    known_sources = [

        "residential rates",

        "industrial rates",

        "commercial rates",

        "industrial/commercial",

        "mining",

        "mining/plant",

        "market fees",

        "parking fees",

        "bus station fees",

        "consent fees",

        "survey fees",

        "building inspection fees",

        "licence fees",

        "license fees",

        "trading licence",

        "trading license",

        "levy",

        "levies",

        "rent",

        "property rates"

    ]

    for source in known_sources:

        if source in text:

            return source.title()

    # --------------------------------------------------------
    # Generic descriptive source
    # --------------------------------------------------------

    if (
        "total" not in text
        and "subtotal" not in text
    ):

        for value in values:

            if not re.fullmatch(
                r"[\d,.\-]+",
                value
            ):

                return value

    return ""


# ============================================================
# DOWNLOAD PDF INTO MEMORY
# ============================================================

def download_pdf(
    year,
    url
):

    print("\n" + "=" * 70)

    print(
        f"DOWNLOADING APPROVED BUDGET {year}"
    )

    print(url)

    response = session.get(
        url,
        timeout=180,
        verify=False
    )

    response.raise_for_status()

    print(
        f"Downloaded "
        f"{len(response.content):,} bytes"
    )

    return response.content


# ============================================================
# EXTRACT ALL TABLES
# ============================================================

def extract_tables(
    pdf_bytes,
    year,
    pdf_url
):

    print("\n" + "-" * 70)

    print(
        f"EXTRACTING TABLES FROM {year}"
    )

    raw_records = []

    final_records = []

    table_number = 0

    record_number = 1

    current_category = ""

    current_status = None

    with pdfplumber.open(
        io.BytesIO(pdf_bytes)
    ) as pdf:

        total_pages = len(pdf.pages)

        print(
            f"Pages found: {total_pages}"
        )

        for page_number, page in enumerate(
            pdf.pages,
            start=1
        ):

            print(
                f"Processing page "
                f"{page_number}/{total_pages}..."
            )

            try:

                tables = page.extract_tables()

            except Exception as error:

                print(
                    f"  Could not extract tables:"
                    f" {error}"
                )

                continue

            if not tables:

                continue

            print(
                f"  Tables found: "
                f"{len(tables)}"
            )

            for table in tables:

                table_number += 1

                for row_number, row in enumerate(
                    table,
                    start=1
                ):

                    if not row:

                        continue

                    # ------------------------------------------------
                    # Clean individual cells
                    # ------------------------------------------------

                    cleaned_row = [
                        clean_text(value)
                        for value in row
                    ]

                    if not any(cleaned_row):

                        continue

                    # ------------------------------------------------
                    # RAW TABLE RECORD
                    #
                    # Every table cell gets its own column.
                    # ------------------------------------------------

                    raw_record = {
                        "year": year,
                        "page": page_number,
                        "table_number": table_number,
                        "row_number": row_number,
                        "source_title": (
                            f"Approved Budget {year}"
                        ),
                        "source_url": pdf_url
                    }

                    for column_number, value in enumerate(
                        cleaned_row,
                        start=1
                    ):

                        raw_record[
                            f"table_column_{column_number}"
                        ] = value

                    raw_records.append(
                        raw_record
                    )

                    # ------------------------------------------------
                    # UPDATE CATEGORY
                    # ------------------------------------------------

                    detected_category = (
                        detect_category(
                            cleaned_row,
                            current_category
                        )
                    )

                    if detected_category:

                        current_category = (
                            detected_category
                        )

                    # ------------------------------------------------
                    # UPDATE STATUS
                    # ------------------------------------------------

                    detected_status = (
                        detect_budget_status(
                            cleaned_row
                        )
                    )

                    if detected_status:

                        current_status = (
                            detected_status
                        )

                    # ------------------------------------------------
                    # CHECK RELEVANCE
                    # ------------------------------------------------

                    if not is_relevant_row(
                        cleaned_row
                    ):

                        continue

                    # ------------------------------------------------
                    # FIND AMOUNTS
                    # ------------------------------------------------

                    amounts = []

                    for value in cleaned_row:

                        amount = clean_amount(
                            value
                        )

                        if amount is not None:

                            amounts.append(
                                amount
                            )

                    if not amounts:

                        continue

                    # ------------------------------------------------
                    # LAST NUMERICAL VALUE
                    # ------------------------------------------------

                    budget_amount = (
                        amounts[-1]
                    )

                    # ------------------------------------------------
                    # DATA TYPE
                    # ------------------------------------------------

                    if (
                        "revenue" in row_text(
                            cleaned_row
                        )
                        or current_category in [
                            "Fees and Charges",
                            "Local Taxes / Rates",
                            "LGEF"
                        ]
                    ):

                        data_type = "Revenue"

                    elif (
                        "expenditure" in row_text(
                            cleaned_row
                        )
                    ):

                        data_type = "Expenditure"

                    elif (
                        "budget" in row_text(
                            cleaned_row
                        )
                    ):

                        data_type = "Budget"

                    else:

                        data_type = "Revenue"

                    # ------------------------------------------------
                    # REVENUE SOURCE
                    # ------------------------------------------------

                    revenue_source = (
                        detect_revenue_source(
                            cleaned_row,
                            current_category
                        )
                    )

                    # ------------------------------------------------
                    # DESCRIPTION
                    #
                    # Cells are joined with | for the final dataset.
                    # The raw CSV still keeps every cell separately.
                    # ------------------------------------------------

                    description = " | ".join(
                        value
                        for value in cleaned_row
                        if value
                    )

                    # ------------------------------------------------
                    # FINAL RECORD
                    # ------------------------------------------------

                    final_records.append({

                        "record_id": (
                            f"BR{year}_{record_number:04d}"
                        ),

                        "year": year,

                        "data_type": data_type,

                        "category": (
                            current_category
                        ),

                        "revenue_source": (
                            revenue_source
                        ),

                        "budget_amount": (
                            budget_amount
                        ),

                        "budget_status": (
                            current_status
                        ),

                        "description": (
                            description
                        ),

                        "source_title": (
                            f"Approved Budget {year}"
                        ),

                        "source_url": (
                            pdf_url
                        ),

                        "source_type": (
                            SOURCE_TYPE
                        )
                    })

                    record_number += 1

    print(
        f"\nRaw rows extracted from "
        f"{year}: {len(raw_records):,}"
    )

    print(
        f"Relevant records extracted from "
        f"{year}: {len(final_records):,}"
    )

    return raw_records, final_records


# ============================================================
# CLEAN FINAL DATASET
# ============================================================

def clean_dataset(dataframe):

    if dataframe.empty:

        return dataframe

    # --------------------------------------------------------
    # Remove exact duplicate records
    # --------------------------------------------------------

    dataframe = dataframe.drop_duplicates(
        subset=[
            "year",
            "data_type",
            "category",
            "revenue_source",
            "budget_amount",
            "budget_status",
            "description"
        ]
    )

    dataframe = dataframe.reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Recreate IDs
    # --------------------------------------------------------

    record_ids = []

    counters = {}

    for year in dataframe["year"]:

        if year not in counters:

            counters[year] = 1

        record_ids.append(
            f"BR{year}_{counters[year]:04d}"
        )

        counters[year] += 1

    dataframe["record_id"] = record_ids

    # --------------------------------------------------------
    # Put record_id first
    # --------------------------------------------------------

    columns = [
        "record_id",
        "year",
        "data_type",
        "category",
        "revenue_source",
        "budget_amount",
        "budget_status",
        "description",
        "source_title",
        "source_url",
        "source_type"
    ]

    dataframe = dataframe[
        columns
    ]

    return dataframe


# ============================================================
# SAVE RAW TABLES
# ============================================================

def save_raw_tables(
    raw_records
):

    if not raw_records:

        print(
            "\nNo raw table records found."
        )

        return

    dataframe = pd.DataFrame(
        raw_records
    )

    # --------------------------------------------------------
    # Determine highest table column
    # --------------------------------------------------------

    table_columns = [
        column
        for column in dataframe.columns
        if column.startswith(
            "table_column_"
        )
    ]

    table_columns.sort(
        key=lambda column:
        int(
            column.split("_")[-1]
        )
    )

    base_columns = [
        "year",
        "page",
        "table_number",
        "row_number",
        "source_title",
        "source_url"
    ]

    dataframe = dataframe[
        base_columns + table_columns
    ]

    dataframe.to_csv(
        RAW_CSV,
        sep="|",
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"\nRAW TABLE DATASET SAVED:"
    )

    print(
        os.path.abspath(RAW_CSV)
    )

    print(
        f"Raw rows: {len(dataframe):,}"
    )


# ============================================================
# SAVE FINAL DATASET
# ============================================================

def save_final_dataset(
    final_records
):

    if not final_records:

        print(
            "\nNo final records found."
        )

        return

    dataframe = pd.DataFrame(
        final_records
    )

    dataframe = clean_dataset(
        dataframe
    )

    dataframe.to_csv(
        FINAL_CSV,
        sep="|",
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"\nFINAL DATASET SAVED:"
    )

    print(
        os.path.abspath(FINAL_CSV)
    )

    print(
        f"Final records: "
        f"{len(dataframe):,}"
    )

    return dataframe


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "MUFULIRA MUNICIPAL COUNCIL"
    )

    print(
        "BUDGET & REVENUE SCRAPER"
    )

    print(
        "2023 - 2026"
    )

    print("=" * 70)

    print(
        "\nPDFs to process:"
    )

    for document in PDF_DOCUMENTS:

        print(
            f"  {document['year']}: "
            f"{document['url']}"
        )

    all_raw_records = []

    all_final_records = []

    # --------------------------------------------------------
    # PROCESS EVERY YEAR
    # --------------------------------------------------------

    for document in PDF_DOCUMENTS:

        year = document["year"]

        url = document["url"]

        try:

            # Download into memory.
            # Nothing is saved to disk.

            pdf_bytes = download_pdf(
                year,
                url
            )

            raw_records, final_records = (
                extract_tables(
                    pdf_bytes,
                    year,
                    url
                )
            )

            all_raw_records.extend(
                raw_records
            )

            all_final_records.extend(
                final_records
            )

        except Exception as error:

            print(
                "\nERROR PROCESSING "
                f"{year}:"
            )

            print(error)

    # --------------------------------------------------------
    # SAVE RAW TABLE DATA
    # --------------------------------------------------------

    save_raw_tables(
        all_raw_records
    )

    # --------------------------------------------------------
    # SAVE FINAL DATASET
    # --------------------------------------------------------

    dataframe = save_final_dataset(
        all_final_records
    )

    if dataframe is None:

        return

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 70)

    print(
        "SCRAPING COMPLETE"
    )

    print("=" * 70)

    print(
        "\nRecords by year:"
    )

    for year in sorted(
        dataframe["year"].unique()
    ):

        count = len(
            dataframe[
                dataframe["year"] == year
            ]
        )

        print(
            f"  {year}: {count:,}"
        )

    print(
        "\nFinal dataset:"
    )

    print(
        os.path.abspath(FINAL_CSV)
    )

    print(
        "\nRaw tables:"
    )

    print(
        os.path.abspath(RAW_CSV)
    )

    print(
        "\nFinal columns:"
    )

    for column in dataframe.columns:

        print(
            f"  - {column}"
        )

    print(
        "\nFirst 20 final records:"
    )

    print(
        dataframe.head(20).to_string(
            index=False
        )
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()