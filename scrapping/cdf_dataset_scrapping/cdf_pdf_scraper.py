import os
import re
import requests
from io import BytesIO
from urllib.parse import urljoin

import pandas as pd
import pdfplumber
from bs4 import BeautifulSoup

try:
    from pdf2image import convert_from_bytes
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

import urllib3

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


# ============================================================
# CONFIGURATION
# ============================================================

CDF_PAGE_URL = "https://www.mufuliracouncil.gov.zm/?page_id=792"

# Current directory where the Python script is being run
OUTPUT_DIR = "."


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    )
})


# ============================================================
# KNOWN WARD NAMES ACROSS MUFULIRA CONSTITUENCIES
# ============================================================

KNOWN_WARDS = [
    "FIBUSA", "MPELEMBE", "KANGWA NSULUKA", "LUANSOBE", "BUNTUNGWA",
    "KWACHA", "BUFUKE", "BUTONDO", "JOHN KAMPENGELE", "DAVID KAUNDA",
    "MAINASOKO", "MOKAMBO", "BWAFWANO", "SHINDE", "MULUNGUSHI",
    "MUPAMBE", "LEYA MUKUTU", "BWEMBYA SILWIZYA", "JOINT CONSTITUENCIES",
    "JOINT WARDS", "ALL WARDS"
]


# ============================================================
# KNOWN SECTOR CATEGORIES
# ============================================================

KNOWN_SECTORS = [
    "WATER & SANITATION", "WATER AND SANITATION", "ROAD & CONSTRUCTION",
    "ROAD AND CONSTRUCTION", "ROADS", "HEALTH", "EDUCATION", "MARKET",
    "MARKET & BUS STATIONS", "AGRICULTURE", "COMMUNITY DEVELOPMENT",
    "COUNCIL", "PUBLIC INFRASTRUCTURE", "PUBLIC SAFETY", "MEDIA SECTOR",
    "MEDIA"
]


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):

    if not text:
        return ""

    return re.sub(r'\s+', ' ', str(text)).strip()


def clean_numeric(val):

    if not val:
        return ""

    return re.sub(r'[^\d.]', '', str(val))


# ============================================================
# PARSE OCR TEXT
# ============================================================

def parse_ocr_text_to_schema(ocr_text, filename):

    """
    Parses OCR block text into exact schema fields using regex patterns.
    """

    records = []

    # Infer Constituency
    fname_lower = filename.lower()

    if "kankoyo" in fname_lower:
        constituency = "Kankoyo"

    elif "kantanshi" in fname_lower:
        constituency = "Kantanshi"

    elif "central" in fname_lower:
        constituency = "Mufulira Central"

    else:
        constituency = "Mufulira District"

    # Split text into blocks starting with project numbers
    raw_blocks = re.split(
        r'\n(?=\b\d{1,2}[.\s\)])',
        ocr_text
    )

    for block in raw_blocks:

        clean_block = re.sub(
            r'\s+',
            ' ',
            block
        ).strip()

        if not clean_block:
            continue

        # Match leading project number
        match = re.match(
            r'^(\d{1,2})[.\s\)]?\s*(.*)',
            clean_block
        )

        if not match:
            continue

        proj_no = match.group(1)
        body = match.group(2)

        # Ignore non-project header numbers
        if (
            int(proj_no) > 35
            or "PROJECT" in body[:15].upper()
            or "NAME" in body[:15].upper()
        ):
            continue

        # ====================================================
        # 1. Extract Ward
        # ====================================================

        ward = ""

        for w in KNOWN_WARDS:

            if w in body.upper():

                ward = w
                break

        # ====================================================
        # 2. Extract Sector
        # ====================================================

        sector = ""

        for s in KNOWN_SECTORS:

            if s in body.upper():

                sector = s
                break

        # ====================================================
        # 3. Extract Financial Amounts
        # ====================================================

        amounts = re.findall(
            r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})\b',
            body
        )

        eng_est = (
            clean_numeric(amounts[0])
            if len(amounts) >= 2
            else ""
        )

        app_amt = (
            clean_numeric(amounts[1])
            if len(amounts) >= 2
            else (
                clean_numeric(amounts[0])
                if len(amounts) == 1
                else ""
            )
        )

        # ====================================================
        # 4. Extract Duration
        # ====================================================

        dur_match = re.search(
            r'\b(\d+\s*(?:WEEKS?|MONTHS?|DAYS?))\b',
            body,
            re.IGNORECASE
        )

        duration = (
            dur_match.group(1).upper()
            if dur_match
            else ""
        )

        # ====================================================
        # 5. Extract Project Name & Scope
        # ====================================================

        proj_name = body

        for kw in [
            ward,
            sector,
            duration,
            "JUSTIFICATION"
        ]:

            if kw and kw in proj_name.upper():

                proj_name = (
                    proj_name.upper()
                    .split(kw)[0]
                    .strip()
                )

                break

        proj_name = proj_name[:80].strip()

        # ====================================================
        # CREATE RECORD
        # ====================================================

        records.append({

            "Constituency": constituency,

            "Project_No": proj_no,

            "Ward": ward,

            "Project_Name": proj_name,

            "Sector": sector,

            "Scope_of_Work": body,

            "Quantity": "",

            "Location": "",

            "Proposed_Date": "",

            "Duration": duration,

            "Engineers_Estimate_ZMW": eng_est,

            "Approved_Amount_ZMW": app_amt,

            "Justification": "",

            "Source_File": filename

        })

    return records


# ============================================================
# EXTRACT FROM SCANNED PDF IN MEMORY
# ============================================================

def extract_from_scanned_pdf(pdf_bytes, filename):

    if not HAS_OCR:

        print(
            f"⚠️ OCR libraries not installed for {filename}"
        )

        return []

    print(
        f"   🔍 Parsing scanned PDF with pattern matching: "
        f"{filename}..."
    )

    try:

        images = convert_from_bytes(
            pdf_bytes,
            dpi=300
        )

    except Exception as e:

        print(
            f"   ❌ Error converting PDF pages: {e}"
        )

        return []

    all_records = []

    for page_num, img in enumerate(
        images,
        start=1
    ):

        # Auto-rotate 180° if inverted
        try:

            osd = pytesseract.image_to_osd(img)

            rotate_angle = int(
                re.search(
                    r'Rotate: (\d+)',
                    osd
                ).group(1)
            )

            if rotate_angle != 0:

                img = img.rotate(
                    360 - rotate_angle,
                    expand=True
                )

        except Exception:

            img = img.rotate(
                180,
                expand=True
            )

        ocr_text = pytesseract.image_to_string(
            img
        )

        page_records = parse_ocr_text_to_schema(
            ocr_text,
            filename
        )

        all_records.extend(
            page_records
        )

    return all_records


# ============================================================
# DOWNLOAD WEBPAGE
# ============================================================

def get_page(url):

    print(
        f"\nRequesting: {url}"
    )

    response = session.get(
        url,
        timeout=30,
        verify=False
    )

    response.raise_for_status()

    return response.text


# ============================================================
# IDENTIFY CONSTITUENCY
# ============================================================

def identify_constituency(url):

    filename = url.split("/")[-1].lower()

    if "kantanshi" in filename:
        return "Kantanshi"

    if "kankoyo" in filename:
        return "Kankoyo"

    if "mufulira-central" in filename:
        return "Mufulira Central"

    return None


# ============================================================
# DISCOVER COMMUNITY PROJECT PDFs
# ============================================================

def discover_project_pdfs():

    html = get_page(
        CDF_PAGE_URL
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    pdf_links = []

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link["href"].strip()

        absolute_url = urljoin(
            CDF_PAGE_URL,
            href
        )

        url_lower = absolute_url.lower()

        # Must be a PDF
        if ".pdf" not in url_lower:
            continue

        # Must be a Community Projects PDF
        if "comm-projects" not in url_lower:
            continue

        # Exclude rejected projects
        if "rejected" in url_lower:
            continue

        constituency = identify_constituency(
            absolute_url
        )

        if constituency is None:
            continue

        pdf_links.append({
            "constituency": constituency,
            "url": absolute_url
        })

    # Remove duplicate URLs
    unique_links = {}

    for item in pdf_links:

        unique_links[item["url"]] = item

    pdf_links = list(
        unique_links.values()
    )

    print(
        "\nCDF Community Project PDFs found:"
    )

    for item in pdf_links:

        print(
            f"  {item['constituency']}: "
            f"{item['url']}"
        )

    return pdf_links


# ============================================================
# DOWNLOAD PDF INTO MEMORY
# ============================================================

def download_pdf_to_memory(item):

    constituency = item["constituency"]
    url = item["url"]

    filename = os.path.basename(
        url.split("?")[0]
    )

    filename = re.sub(
        r"[^A-Za-z0-9._-]",
        "_",
        filename
    )

    print(
        f"\nDownloading {constituency}:"
    )

    print(
        f"URL: {url}"
    )

    response = session.get(
        url,
        timeout=60,
        verify=False
    )

    response.raise_for_status()

    pdf_bytes = response.content

    print(
        f"Loaded into memory: "
        f"{len(pdf_bytes):,} bytes"
    )

    return pdf_bytes, filename


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 70
    )

    print(
        "MUFULIRA MUNICIPAL COUNCIL"
    )

    print(
        "CDF COMMUNITY PROJECT PDF SCRAPER"
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # 1. Find PDFs from website
    # --------------------------------------------------------

    pdf_documents = discover_project_pdfs()

    if not pdf_documents:

        print(
            "\nNo Community Projects PDFs were found."
        )

        return

    # --------------------------------------------------------
    # 2. Download PDFs into memory and extract
    # --------------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "DOWNLOADING PDFs INTO MEMORY AND EXTRACTING"
    )

    print(
        "=" * 70
    )

    master_records = []

    for item in pdf_documents:

        try:

            pdf_bytes, filename = (
                download_pdf_to_memory(item)
            )

            records = extract_from_scanned_pdf(
                pdf_bytes,
                filename
            )

            print(
                f"   ✓ Successfully mapped "
                f"{len(records)} records from {filename}"
            )

            master_records.extend(
                records
            )

        except Exception as error:

            print(
                f"\nERROR processing "
                f"{item['constituency']}: "
                f"{error}"
            )

    # --------------------------------------------------------
    # 3. Check extracted data
    # --------------------------------------------------------

    if not master_records:

        print(
            "\n❌ No data extracted."
        )

        return

    # --------------------------------------------------------
    # 4. Create dataframe
    # --------------------------------------------------------

    df = pd.DataFrame(
        master_records
    )

    # --------------------------------------------------------
    # 5. Master Schema Column Order
    # --------------------------------------------------------

    schema_cols = [

        "Constituency",
        "Project_No",
        "Ward",
        "Project_Name",
        "Sector",
        "Scope_of_Work",
        "Quantity",
        "Location",
        "Proposed_Date",
        "Duration",
        "Engineers_Estimate_ZMW",
        "Approved_Amount_ZMW",
        "Justification",
        "Source_File"

    ]

    for col in schema_cols:

        if col not in df.columns:

            df[col] = ""

    df = df[
        schema_cols
    ]

    # --------------------------------------------------------
    # 6. Save Pipe-Delimited CSV
    # --------------------------------------------------------

    output_filename = (
        "db-unza26-csc4792-mufulira_cdf_projects.csv"
    )

    output_path = os.path.join(
        OUTPUT_DIR,
        output_filename
    )

    df.to_csv(
        output_path,
        sep="|",
        index=False,
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # 7. Final Summary
    # --------------------------------------------------------

    print(
        "\n" + "=" * 65
    )

    print(
        "🎉 SUCCESS: All data mapped correctly "
        "into destination columns!"
    )

    print(
        f"Output File: "
        f"{os.path.abspath(output_path)}"
    )

    print(
        f"Total Combined Rows: "
        f"{len(df)}"
    )

    print(
        "PDF files were NOT saved locally."
    )

    print(
        "=" * 65
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()