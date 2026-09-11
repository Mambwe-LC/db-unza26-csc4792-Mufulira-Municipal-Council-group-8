import os
import re
from io import BytesIO
from urllib.parse import urlparse

import requests
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

PDF_URLS = [

    # --------------------------------------------------------
    # KANTANSHI
    # --------------------------------------------------------

    {
        "constituency": "Kantanshi",
        "url": (
            "https://www.mufuliracouncil.gov.zm/"
            "wp-content/uploads/2026/01/"
            "Final-Skills-2026-Approved-Applicants-Kantanshi.pdf"
        )
    },

    {
        "constituency": "Kantanshi",
        "url": (
            "https://www.mufuliracouncil.gov.zm/"
            "wp-content/uploads/2026/01/"
            "Kantanshi-2025-Approved-Skills-Replacements.pdf"
        )
    },

    {
        "constituency": "Kantanshi",
        "url": (
            "https://www.mufuliracouncil.gov.zm/"
            "wp-content/uploads/2025/03/"
            "Kantanshi-2025-APPROVED-SKILLS-DEVELOPEMENT.pdf"
        )
    },

    # --------------------------------------------------------
    # KANKOYO
    # --------------------------------------------------------

    {
        "constituency": "Kankoyo",
        "url": (
            "https://www.mufuliracouncil.gov.zm/"
            "wp-content/uploads/2025/02/"
            "kankoyo-CDF-2025-SKILL-DEVELOPMENT-APPROVED.pdf"
        )
    },

    {
        "constituency": "Kankoyo",
        "url": (
            "https://www.mufuliracouncil.gov.zm/"
            "wp-content/uploads/2026/01/"
            "Kankoyo-CDF-2026-Skills-Applicants.pdf"
        )
    },

    # --------------------------------------------------------
    # MUFULIRA CENTRAL
    # --------------------------------------------------------

    {
        "constituency": "Mufulira Central",
        "url": (
            "https://www.mufuliracouncil.gov.zm/"
            "wp-content/uploads/2026/01/"
            "Approved-CDF-2026-Mufulira-Central.pdf"
        )
    },

    {
        "constituency": "Mufulira Central",
        "url": (
            "https://www.mufuliracouncil.gov.zm/"
            "wp-content/uploads/2025/02/"
            "2025-Mufulira-Central-Skills-CDF-Approved.pdf"
        )
    }
]


# Current directory
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
# FINAL DATABASE SCHEMA
# ============================================================

SCHEMA_COLS = [

    "Constituency",

    "No",

    "Ward",

    "Zone",

    "Name_of_Pupil",

    "NRC",

    "Gender",

    "Date_of_Birth",

    "Type_of_Vulnerability",

    "Study_Programme",

    "Study_Type",

    "Course_Duration",

    "Name_of_Skills_Institution",

    "Total_TEVETA_Fees",

    "Approved",

    "Guardian_Parent_Name",

    "Guardian_Parent_Phone",

    "Source_File"

]


# ============================================================
# GENERAL TEXT CLEANING
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    value = str(value)

    value = value.replace("\n", " ")
    value = value.replace("\r", " ")
    value = value.replace("\t", " ")

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalize_header(value):

    value = clean_text(value).upper()

    value = value.replace("/", " ")
    value = value.replace("-", " ")
    value = value.replace("(", " ")
    value = value.replace(")", " ")
    value = value.replace(".", " ")

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def clean_nrc(value):

    value = clean_text(value)

    if not value:
        return ""

    value = re.sub(
        r"[^A-Za-z0-9/ -]",
        "",
        value
    )

    return value.strip()


def clean_gender(value):

    value = clean_text(value).upper()

    if value in ["M", "MALE"]:
        return "M"

    if value in ["F", "FEMALE"]:
        return "F"

    return value


def clean_amount(value):

    value = clean_text(value)

    if not value:
        return ""

    value = value.replace(
        "ZMW",
        ""
    )

    value = value.replace(
        "K",
        ""
    )

    value = value.replace(
        ",",
        ""
    )

    value = re.sub(
        r"[^\d.]",
        "",
        value
    )

    return value


def clean_phone(value):

    value = clean_text(value)

    if not value:
        return ""

    value = re.sub(
        r"[^\d+]",
        "",
        value
    )

    return value


# ============================================================
# FILENAME
# ============================================================

def get_filename(url):

    filename = os.path.basename(
        urlparse(url).path
    )

    filename = re.sub(
        r"[^A-Za-z0-9._-]",
        "_",
        filename
    )

    return filename


# ============================================================
# DOWNLOAD PDF INTO MEMORY
# ============================================================

def download_pdf(item):

    constituency = item["constituency"]
    url = item["url"]

    filename = get_filename(url)

    print(
        "\n" + "=" * 70
    )

    print(
        f"Downloading {constituency}"
    )

    print(
        f"URL: {url}"
    )

    print(
        "=" * 70
    )

    response = session.get(
        url,
        timeout=120,
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
# CHECK WHETHER PDF HAS TEXT
# ============================================================

def pdf_has_extractable_text(pdf_bytes):

    try:

        with pdfplumber.open(
            BytesIO(pdf_bytes)
        ) as pdf:

            for page in pdf.pages:

                text = page.extract_text()

                if text and len(
                    clean_text(text)
                ) > 50:

                    return True

    except Exception as error:

        print(
            f"Text detection error: {error}"
        )

    return False


# ============================================================
# HEADER ALIASES
# ============================================================

HEADER_ALIASES = {

    "No": [
        "NO",
        "NO.",
        "NUMBER",
        "S/N",
        "S NO"
    ],

    "Ward": [
        "WARD",
        "WARD NAME"
    ],

    "Zone": [
        "ZONE"
    ],

    "Name_of_Pupil": [
        "NAME OF PUPIL",
        "NAME OF STUDENT",
        "NAME OF APPLICANT",
        "PUPIL NAME",
        "STUDENT NAME",
        "APPLICANT NAME",
        "NAME"
    ],

    "NRC": [
        "NRC",
        "N R C",
        "NATIONAL REGISTRATION CARD"
    ],

    "Gender": [
        "GENDER",
        "GENDER M F",
        "SEX",
        "M F"
    ],

    "Date_of_Birth": [
        "DATE OF BIRTH",
        "DOB",
        "DATE BORN"
    ],

    "Type_of_Vulnerability": [
        "TYPE OF VULNERABILITY",
        "VULNERABILITY",
        "VULNERABILITY TYPE"
    ],

    "Study_Programme": [
        "STUDY PROGRAMME",
        "STUDY PROGRAM",
        "PROGRAMME",
        "PROGRAM",
        "COURSE"
    ],

    "Study_Type": [
        "STUDY TYPE",
        "TYPE OF STUDY"
    ],

    "Course_Duration": [
        "COURSE DURATION",
        "DURATION",
        "DURATION OF COURSE"
    ],

    "Name_of_Skills_Institution": [
        "NAME OF SKILLS INSTITUTION",
        "SKILLS INSTITUTION",
        "TRAINING INSTITUTION",
        "INSTITUTION",
        "NAME OF INSTITUTION"
    ],

    "Total_TEVETA_Fees": [
        "TOTAL TEVETA FEES",
        "TOTAL",
        "TOTAL FEES",
        "TEVETA FEES",
        "AMOUNT",
        "TOTAL AMOUNT",
        "COST"
    ],

    "Approved": [
        "APPROVED",
        "APPROVAL"
    ],

    "Guardian_Parent_Name": [
        "GUARDIAN/PARENT",
        "GUARDIAN PARENT",
        "GUARDIAN/PARENT NAME",
        "GUARDIAN PARENT NAME",
        "PARENT NAME",
        "GUARDIAN NAME"
    ],

    "Guardian_Parent_Phone": [
        "MOBILE NO",
        "MOBILE",
        "PHONE",
        "PHONE NUMBER",
        "MOBILE NUMBER"
    ]
}


# ============================================================
# IDENTIFY HEADER COLUMNS
# ============================================================

def identify_header_columns(header_row):

    mapping = {}

    normalized_headers = [
        normalize_header(x)
        for x in header_row
    ]

    for index, header in enumerate(
        normalized_headers
    ):

        if not header:
            continue

        for schema_field, aliases in HEADER_ALIASES.items():

            for alias in aliases:

                normalized_alias = normalize_header(
                    alias
                )

                if (
                    header == normalized_alias
                    or normalized_alias in header
                ):

                    mapping[schema_field] = index

                    break

            if schema_field in mapping:
                break

    return mapping


# ============================================================
# PARSE GUARDIAN / PARENT PHONE
# ============================================================

def split_guardian_phone(value):

    value = clean_text(value)

    if not value:
        return "", ""

    phone_pattern = (
        r"(?<!\d)"
        r"(?:\+?260[\s-]?)?"
        r"(?:0?[79]\d{8})"
        r"(?!\d)"
    )

    matches = re.findall(
        phone_pattern,
        value
    )

    if not matches:

        return value, ""

    phone = matches[-1]

    phone = clean_phone(
        phone
    )

    guardian_name = re.sub(
        phone_pattern,
        "",
        value
    )

    guardian_name = clean_text(
        guardian_name
    )

    return guardian_name, phone


# ============================================================
# PARSE PDF TABLE
# ============================================================

def parse_table(
    table,
    constituency,
    filename
):

    if not table:
        return []

    # --------------------------------------------------------
    # Find header row
    # --------------------------------------------------------

    header_index = None
    column_mapping = {}

    for i, row in enumerate(table):

        if not row:
            continue

        mapping = identify_header_columns(
            row
        )

        if len(mapping) >= 4:

            header_index = i

            column_mapping = mapping

            break

    if header_index is None:

        return []

    records = []

    # --------------------------------------------------------
    # Process rows after header
    # --------------------------------------------------------

    for row in table[
        header_index + 1:
    ]:

        if not row:
            continue

        row = [
            clean_text(x)
            for x in row
        ]

        if not any(row):
            continue

        record = {
            col: ""
            for col in SCHEMA_COLS
        }

        record["Constituency"] = constituency

        record["Source_File"] = filename

        # ----------------------------------------------------
        # Map every recognized column
        # ----------------------------------------------------

        for field, index in column_mapping.items():

            if index >= len(row):
                continue

            value = row[index]

            if field == "NRC":

                value = clean_nrc(
                    value
                )

            elif field == "Gender":

                value = clean_gender(
                    value
                )

            elif field == "Total_TEVETA_Fees":

                value = clean_amount(
                    value
                )

            elif field == "Guardian_Parent_Name":

                guardian_name, phone = (
                    split_guardian_phone(
                        value
                    )
                )

                record[
                    "Guardian_Parent_Name"
                ] = guardian_name

                if not record[
                    "Guardian_Parent_Phone"
                ]:

                    record[
                        "Guardian_Parent_Phone"
                    ] = phone

                continue

            elif field == "Guardian_Parent_Phone":

                value = clean_phone(
                    value
                )

            record[field] = value

        # ----------------------------------------------------
        # Applicant row check
        # ----------------------------------------------------

        if is_applicant_record(
            record
        ):

            records.append(
                record
            )

    return records


# ============================================================
# IDENTIFY APPLICANT ROW
# ============================================================

def is_applicant_record(record):

    number = clean_text(
        record.get("No", "")
    )

    name = clean_text(
        record.get("Name_of_Pupil", "")
    )

    nrc = clean_text(
        record.get("NRC", "")
    )

    if (
        number
        and re.search(
            r"\d{1,3}",
            number
        )
    ):

        return True

    if (
        name
        and len(name) >= 3
    ):

        return True

    if (
        nrc
        and len(nrc) >= 5
    ):

        return True

    return False


# ============================================================
# EXTRACT NORMAL PDF
# ============================================================

def extract_normal_pdf(
    pdf_bytes,
    constituency,
    filename
):

    print(
        f"   📄 Trying normal PDF extraction: "
        f"{filename}"
    )

    records = []

    try:

        with pdfplumber.open(
            BytesIO(pdf_bytes)
        ) as pdf:

            for page_number, page in enumerate(
                pdf.pages,
                start=1
            ):

                print(
                    f"      Page {page_number}..."
                )

                tables = page.extract_tables()

                if tables:

                    print(
                        f"         Tables found: "
                        f"{len(tables)}"
                    )

                    for table in tables:

                        if not table:
                            continue

                        page_records = parse_table(
                            table,
                            constituency,
                            filename
                        )

                        records.extend(
                            page_records
                        )

                # ------------------------------------------------
                # Text fallback for this page
                # ------------------------------------------------

                if not tables:

                    text = page.extract_text()

                    if text:

                        page_records = parse_text_rows(
                            text,
                            constituency,
                            filename
                        )

                        records.extend(
                            page_records
                        )

    except Exception as error:

        print(
            f"   ❌ Normal PDF extraction failed: "
            f"{error}"
        )

        return []

    print(
        f"   ✓ Normal PDF extraction produced "
        f"{len(records)} applicant rows"
    )

    return records


# ============================================================
# PARSE TEXT-BASED PDF ROWS
# ============================================================

def parse_text_rows(
    text,
    constituency,
    filename
):

    records = []

    lines = [
        clean_text(line)
        for line in text.splitlines()
    ]

    lines = [
        line
        for line in lines
        if line
    ]

    # --------------------------------------------------------
    # Find header
    # --------------------------------------------------------

    header_line_index = None

    for i, line in enumerate(lines):

        upper = normalize_header(
            line
        )

        score = 0

        for aliases in HEADER_ALIASES.values():

            for alias in aliases:

                if normalize_header(alias) in upper:

                    score += 1

                    break

        if score >= 4:

            header_line_index = i

            break

    if header_line_index is None:

        return []

    # --------------------------------------------------------
    # Process subsequent lines
    # --------------------------------------------------------

    data_lines = lines[
        header_line_index + 1:
    ]

    current_rows = []

    for line in data_lines:

        upper = line.upper()

        if (
            "APPROVED SKILL DEVELOPMENT" in upper
            or "APPLICANTS" in upper
            or "STUDENTS LISTED BELOW" in upper
        ):

            continue

        if re.match(
            r"^\s*\d{1,3}\b",
            line
        ):

            current_rows.append(
                line
            )

        elif current_rows:

            current_rows[-1] += (
                " " + line
            )

    # --------------------------------------------------------
    # Parse reconstructed rows
    # --------------------------------------------------------

    for line in current_rows:

        record = parse_text_applicant_line(
            line,
            constituency,
            filename
        )

        if record:

            records.append(
                record
            )

    return records


# ============================================================
# PARSE ONE TEXT APPLICANT ROW
# ============================================================

def parse_text_applicant_line(
    line,
    constituency,
    filename
):

    line = clean_text(
        line
    )

    number_match = re.match(
        r"^(\d{1,3})\s+(.*)$",
        line
    )

    if not number_match:

        return None

    number = number_match.group(1)

    body = number_match.group(2)

    nrc = ""

    nrc_match = re.search(
        r"\b\d{6}/\d{2}/\d\b",
        body
    )

    if nrc_match:

        nrc = nrc_match.group(0)

    gender = ""

    gender_match = re.search(
        r"\b([MF])\b",
        body,
        re.IGNORECASE
    )

    if gender_match:

        gender = gender_match.group(1).upper()

    dob = ""

    dob_match = re.search(
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        body
    )

    if dob_match:

        dob = dob_match.group(0)

    record = {
        "Constituency": constituency,
        "No": number,
        "Ward": "",
        "Zone": "",
        "Name_of_Pupil": "",
        "NRC": nrc,
        "Gender": gender,
        "Date_of_Birth": dob,
        "Type_of_Vulnerability": "",
        "Study_Programme": "",
        "Study_Type": "",
        "Course_Duration": "",
        "Name_of_Skills_Institution": "",
        "Total_TEVETA_Fees": "",
        "Approved": "",
        "Guardian_Parent_Name": "",
        "Guardian_Parent_Phone": "",
        "Source_File": filename
    }

    name = body

    if nrc:

        name = name.replace(
            nrc,
            " "
        )

    if gender:

        name = re.sub(
            rf"\b{gender}\b",
            " ",
            name,
            count=1,
            flags=re.IGNORECASE
        )

    if dob:

        name = name.replace(
            dob,
            " "
        )

    name = clean_text(
        name
    )

    record["Name_of_Pupil"] = name

    return record


# ============================================================
# OCR PDF EXTRACTION
# ============================================================

def extract_ocr_pdf(
    pdf_bytes,
    constituency,
    filename
):

    if not HAS_OCR:

        print(
            "   ⚠️ OCR libraries are not installed."
        )

        print(
            "   Install with:"
        )

        print(
            "   pip install pdf2image pytesseract"
        )

        return []

    print(
        f"   🔍 PDF appears scanned. "
        f"Using OCR: {filename}"
    )

    try:

        images = convert_from_bytes(
            pdf_bytes,
            dpi=300
        )

    except Exception as error:

        print(
            f"   ❌ Error converting PDF pages: "
            f"{error}"
        )

        return []

    all_records = []

    for page_number, image in enumerate(
        images,
        start=1
    ):

        print(
            f"      OCR page {page_number}..."
        )

        # ----------------------------------------------------
        # Orientation detection
        # ----------------------------------------------------

        try:

            osd = pytesseract.image_to_osd(
                image
            )

            rotate_match = re.search(
                r"Rotate:\s*(\d+)",
                osd
            )

            if rotate_match:

                rotate_angle = int(
                    rotate_match.group(1)
                )

                if rotate_angle != 0:

                    image = image.rotate(
                        360 - rotate_angle,
                        expand=True
                    )

        except Exception:

            pass

        # ----------------------------------------------------
        # OCR
        # ----------------------------------------------------

        ocr_text = pytesseract.image_to_string(
            image,
            config="--psm 6"
        )

        # ----------------------------------------------------
        # Parse OCR rows
        # ----------------------------------------------------

        page_records = parse_ocr_applicant_rows(
            ocr_text,
            constituency,
            filename
        )

        all_records.extend(
            page_records
        )

    print(
        f"   ✓ OCR produced "
        f"{len(all_records)} applicant rows"
    )

    return all_records


# ============================================================
# OCR APPLICANT ROW PARSER
# ============================================================

def parse_ocr_applicant_rows(
    ocr_text,
    constituency,
    filename
):

    records = []

    lines = [
        clean_text(line)
        for line in ocr_text.splitlines()
    ]

    lines = [
        line
        for line in lines
        if line
    ]

    current_row = ""

    rows = []

    for line in lines:

        starts_with_number = re.match(
            r"^\s*\d{1,3}(?:[.)])?\s+",
            line
        )

        if starts_with_number:

            if current_row:

                rows.append(
                    current_row
                )

            current_row = line

        else:

            if current_row:

                current_row += (
                    " " + line
                )

    if current_row:

        rows.append(
            current_row
        )

    for row in rows:

        record = parse_ocr_row(
            row,
            constituency,
            filename
        )

        if record:

            records.append(
                record
            )

    return records


# ============================================================
# PARSE OCR ROW
# ============================================================

def parse_ocr_row(
    row,
    constituency,
    filename
):

    row = clean_text(
        row
    )

    number_match = re.match(
        r"^\s*(\d{1,3})(?:[.)])?\s+(.*)$",
        row
    )

    if not number_match:

        return None

    number = number_match.group(1)

    body = number_match.group(2)

    if any(
        keyword in body.upper()
        for keyword in [
            "WARD NAME",
            "NAME OF PUPIL",
            "NRC GENDER",
            "STUDY PROGRAMME",
            "APPROVED",
            "APPLICANTS"
        ]
    ):

        return None

    nrc = ""

    nrc_match = re.search(
        r"\b\d{6}[/\\-]\d{2}[/\\-]\d\b",
        body
    )

    if nrc_match:

        nrc = nrc_match.group(0)

    nrc = nrc.replace(
        "-",
        "/"
    )

    gender = ""

    gender_match = re.search(
        r"\b([MF])\b",
        body,
        re.IGNORECASE
    )

    if gender_match:

        gender = gender_match.group(1).upper()

    dob = ""

    dob_match = re.search(
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        body
    )

    if dob_match:

        dob = dob_match.group(0)

    record = {
        "Constituency": constituency,
        "No": number,
        "Ward": "",
        "Zone": "",
        "Name_of_Pupil": "",
        "NRC": nrc,
        "Gender": gender,
        "Date_of_Birth": dob,
        "Type_of_Vulnerability": "",
        "Study_Programme": "",
        "Study_Type": "",
        "Course_Duration": "",
        "Name_of_Skills_Institution": "",
        "Total_TEVETA_Fees": "",
        "Approved": "",
        "Guardian_Parent_Name": "",
        "Guardian_Parent_Phone": "",
        "Source_File": filename
    }

    # --------------------------------------------------------
    # Extract known wards
    # --------------------------------------------------------

    known_wards = [
        "FIBUSA",
        "MPELEMBE",
        "KANGWA NSULUKA",
        "LUANSOBE",
        "BUNTUNGWA",
        "KWACHA",
        "BUFUKE",
        "BUTONDO",
        "JOHN KAMPENGELE",
        "DAVID KAUNDA",
        "MAINASOKO",
        "MOKAMBO",
        "BWAFWANO",
        "SHINDE",
        "MULUNGUSHI",
        "MUPAMBE",
        "LEYA MUKUTU",
        "BWEMBYA SILWIZYA"
    ]

    upper_body = body.upper()

    for ward in known_wards:

        if ward in upper_body:

            record["Ward"] = ward

            break

    # --------------------------------------------------------
    # Extract name
    # --------------------------------------------------------

    name = body

    if nrc:

        name = name.replace(
            nrc,
            " "
        )

    if dob:

        name = name.replace(
            dob,
            " "
        )

    if gender:

        name = re.sub(
            rf"\b{gender}\b",
            " ",
            name,
            count=1,
            flags=re.IGNORECASE
        )

    if record["Ward"]:

        name = re.sub(
            re.escape(record["Ward"]),
            " ",
            name,
            count=1,
            flags=re.IGNORECASE
        )

    name = clean_text(
        name
    )

    record["Name_of_Pupil"] = name

    return record


# ============================================================
# REMOVE DUPLICATE APPLICANTS
# ============================================================

def remove_duplicate_records(df):

    if df.empty:

        return df

    dedupe_cols = [
        "Constituency",
        "No",
        "Name_of_Pupil",
        "NRC",
        "Source_File"
    ]

    existing = [
        col
        for col in dedupe_cols
        if col in df.columns
    ]

    df = df.drop_duplicates(
        subset=existing,
        keep="first"
    )

    return df


# ============================================================
# PROCESS ONE PDF
# ============================================================

def process_pdf(item):

    constituency = item["constituency"]

    pdf_bytes, filename = download_pdf(
        item
    )

    # --------------------------------------------------------
    # Determine PDF type
    # --------------------------------------------------------

    has_text = pdf_has_extractable_text(
        pdf_bytes
    )

    print(
        f"   Extractable text detected: "
        f"{has_text}"
    )

    records = []

    # --------------------------------------------------------
    # NORMAL PDF
    # --------------------------------------------------------

    if has_text:

        records = extract_normal_pdf(
            pdf_bytes,
            constituency,
            filename
        )

        # ----------------------------------------------------
        # OCR fallback
        # ----------------------------------------------------

        if not records:

            print(
                "   ⚠️ Normal extraction produced "
                "no applicant records."
            )

            print(
                "   Falling back to OCR..."
            )

            records = extract_ocr_pdf(
                pdf_bytes,
                constituency,
                filename
            )

    # --------------------------------------------------------
    # SCANNED PDF
    # --------------------------------------------------------

    else:

        records = extract_ocr_pdf(
            pdf_bytes,
            constituency,
            filename
        )

    return records


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
        "CDF SKILLS DEVELOPMENT APPLICANT EXTRACTOR"
    )

    print(
        "=" * 70
    )

    master_records = []

    # --------------------------------------------------------
    # PROCESS ALL PDFs IN THE LIST
    # --------------------------------------------------------

    for number, item in enumerate(
        PDF_URLS,
        start=1
    ):

        print(
            "\n" + "=" * 70
        )

        print(
            f"PROCESSING PDF "
            f"{number}/{len(PDF_URLS)}"
        )

        print(
            "=" * 70
        )

        try:

            records = process_pdf(
                item
            )

            print(
                f"\n✓ {item['constituency']}: "
                f"{len(records)} applicant rows"
            )

            master_records.extend(
                records
            )

        except Exception as error:

            print(
                "\n❌ ERROR processing:"
            )

            print(
                item["url"]
            )

            print(
                error
            )

    # --------------------------------------------------------
    # No data
    # --------------------------------------------------------

    if not master_records:

        print(
            "\n❌ No applicant data extracted."
        )

        return

    # --------------------------------------------------------
    # DataFrame
    # --------------------------------------------------------

    df = pd.DataFrame(
        master_records
    )

    # --------------------------------------------------------
    # Guarantee schema
    # --------------------------------------------------------

    for col in SCHEMA_COLS:

        if col not in df.columns:

            df[col] = ""

    df = df[
        SCHEMA_COLS
    ]

    # --------------------------------------------------------
    # Clean all text columns
    # --------------------------------------------------------

    for col in df.columns:

        df[col] = df[col].apply(
            clean_text
        )

    # --------------------------------------------------------
    # Specific cleaning
    # --------------------------------------------------------

    df["NRC"] = df["NRC"].apply(
        clean_nrc
    )

    df["Gender"] = df["Gender"].apply(
        clean_gender
    )

    df["Total_TEVETA_Fees"] = (
        df["Total_TEVETA_Fees"].apply(
            clean_amount
        )
    )

    df["Guardian_Parent_Phone"] = (
        df["Guardian_Parent_Phone"].apply(
            clean_phone
        )
    )

    # --------------------------------------------------------
    # Remove obviously empty rows
    # --------------------------------------------------------

    df = df[
        (
            df["Name_of_Pupil"].str.len() > 0
        )
        |
        (
            df["NRC"].str.len() > 0
        )
    ].copy()

    # --------------------------------------------------------
    # Remove exact duplicate records
    # --------------------------------------------------------

    before = len(df)

    df = remove_duplicate_records(
        df
    )

    after = len(df)

    print(
        f"\nDuplicate exact rows removed: "
        f"{before - after}"
    )

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    output_filename = (
        "db-unza26-csc4792-mufulira_"
        "cdf_skills_applicants.csv"
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
    # SUMMARY
    # --------------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "🎉 SUCCESS"
    )

    print(
        "CDF Skills Development applicants extracted."
    )

    print(
        f"Output File: "
        f"{os.path.abspath(output_path)}"
    )

    print(
        f"Total Applicant Rows: "
        f"{len(df)}"
    )

    print(
        "\nApplicants by Constituency:"
    )

    print(
        df["Constituency"].value_counts()
    )

    print(
        "\nApplicants by Source File:"
    )

    print(
        df["Source_File"].value_counts()
    )

    print(
        "\nFinal Columns:"
    )

    for column in df.columns:

        print(
            f"  - {column}"
        )

    print(
        "=" * 70
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()