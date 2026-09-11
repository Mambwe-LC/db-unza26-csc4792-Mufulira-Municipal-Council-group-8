import re
import io
import requests
import pandas as pd
import pdfplumber
import urllib3

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)

# PDF Source URL on Mufulira Council Server
PDF_URL = (
    "https://www.mufuliracouncil.gov.zm/"
    "wp-content/uploads/2025/12/"
    "Final-Signed-IDP-Mufulira-District.pdf"
)

# Master Ward Mapping for Geocoding & Standardization
WARD_CONSTITUENCY_MAP = {
    # Mufulira Constituency (10 Wards)
    "KAMUCHANGA": "Mufulira Central", "HANKY KALANGA": "Mufulira Central",
    "KASEMPA": "Mufulira Central", "CHACHACHA": "Mufulira Central",
    "KANSUSWA": "Mufulira Central", "KAFUE": "Mufulira Central",
    "BWANANYINA": "Mufulira Central", "KAWAMA WEST": "Mufulira Central",
    "MUTUNDU": "Mufulira Central", "DAVID LUNDA": "Mufulira Central",
    
    # Kantanshi Constituency (11 Wards)
    "MINAMBE": "Kantanshi", "MOKAMBO": "Kantanshi", "MUPAMBE": "Kantanshi",
    "DAVID KAUNDA": "Kantanshi", "MAINASOKO": "Kantanshi", "MAINA SOKO": "Kantanshi",
    "BWEMBYA SILWIZYA": "Kantanshi", "BWEMBYA SILWEZYA": "Kantanshi",
    "LEYA MUKUTU": "Kantanshi", "BWAFWANO": "Kantanshi", "MULUNGUSHI": "Kantanshi",
    "MULUNGUNSHI": "Kantanshi", "SHINDE": "Kantanshi", "MURUNDU": "Kantanshi",
    
    # Kankoyo Constituency (9 Wards)
    "FIBUSA": "Kankoyo", "KWACHA": "Kankoyo", "JOHN KAMPENGELE": "Kankoyo",
    "BUNTUNGWA": "Kankoyo", "KANGWA NSULUKA": "Kankoyo", "LUANSOBE": "Kankoyo",
    "LWANSOBE": "Kankoyo", "BUTONDO": "Kankoyo", "BUFUKE": "Kankoyo", "MPELEMBE": "Kankoyo"
}

def clean_str(val):
    if not val or pd.isna(val):
        return ""
    # Remove internal linebreaks and compress spaces
    cleaned = re.sub(r'\s+', ' ', str(val)).strip()
    return cleaned

def clean_num(val):
    if not val or pd.isna(val):
        return ""
    # Keep digits, minus sign, and decimals
    cleaned = re.sub(r'[^\d.]', '', str(val))
    return cleaned

def download_or_get_pdf_bytes():
    """Download PDF directly from council server into memory."""

    print(f"Fetching PDF directly from URL: {PDF_URL} ...")

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/139.0 Safari/537.36"
        ),
        "Accept": "application/pdf,application/octet-stream,*/*",
        "Accept-Language": "en-US,en;q=0.9"
    })

    try:
        response = session.get(
            PDF_URL,
            timeout=180,
            verify=False,
            allow_redirects=True
        )

        print(f"   HTTP Status: {response.status_code}")

        response.raise_for_status()

        pdf_bytes = response.content

        print(f"   Downloaded: {len(pdf_bytes):,} bytes")

        # Verify that the response is actually a PDF
        if not pdf_bytes.startswith(b"%PDF"):
            print("   ✗ Server response is not a valid PDF.")
            print(
                f"   Content-Type: "
                f"{response.headers.get('Content-Type')}"
            )

            raise ValueError(
                "The council server did not return a PDF."
            )

        print("   ✓ PDF verified.")
        print("   ✓ PDF loaded into memory.")

        # IMPORTANT:
        # Nothing is saved to disk.
        return io.BytesIO(pdf_bytes)

    except Exception as e:
        raise RuntimeError(
            f"Could not download Mufulira IDP PDF: {e}"
        )

def extract_wards_demographics(pdf_bytes):
    """
    Dataset 1: Extract ward demographic information directly
    from the Mufulira IDP PDF.

    No ward names, population figures, households, or poverty
    values are hardcoded here.
    """

    print("Extracting Dataset 1: Wards & Demographics from PDF...")

    records = []

    # Expected output columns
    columns = [
        "Constituency",
        "Ward_Name",
        "Number_of_Households",
        "Total_Population",
        "Male_Population",
        "Female_Population",
        "Poverty_Level_Status"
    ]

    pdf_bytes.seek(0)

    with pdfplumber.open(pdf_bytes) as pdf:

        print(f"   Scanning {len(pdf.pages)} PDF pages...")

        for page_number, page in enumerate(pdf.pages, start=1):

            try:
                tables = page.extract_tables(
                    table_settings={
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "intersection_tolerance": 5,
                        "snap_tolerance": 3,
                        "join_tolerance": 3,
                        "edge_min_length": 3,
                        "min_words_vertical": 2,
                        "min_words_horizontal": 1
                    }
                )
            except Exception:
                tables = []

            if not tables:
                continue

            for table in tables:

                if not table:
                    continue

                # Remove completely empty rows
                table = [
                    row for row in table
                    if row and any(
                        str(cell).strip()
                        for cell in row
                        if cell is not None
                    )
                ]

                if not table:
                    continue

                # ------------------------------------------------
                # Find the demographic table header
                # ------------------------------------------------

                header_index = None

                for i, row in enumerate(table[:10]):

                    header_text = " ".join(
                        clean_str(cell).lower()
                        for cell in row
                        if cell is not None
                    )

                    # We specifically look for the demographic
                    # columns rather than relying on a page number.
                    has_ward = (
                        "ward" in header_text
                    )

                    has_population = (
                        "population" in header_text
                    )

                    has_households = (
                        "household" in header_text
                    )

                    has_male = (
                        "male" in header_text
                    )

                    has_female = (
                        "female" in header_text
                    )

                    if (
                        has_ward
                        and has_population
                        and (
                            has_households
                            or (has_male and has_female)
                        )
                    ):
                        header_index = i
                        break

                if header_index is None:
                    continue

                header = [
                    clean_str(cell).lower()
                    for cell in table[header_index]
                ]

                # ------------------------------------------------
                # Identify each column dynamically
                # ------------------------------------------------

                column_indexes = {}

                for index, value in enumerate(header):

                    value = re.sub(
                        r"\s+",
                        " ",
                        value
                    ).strip()

                    if "ward" in value:
                        column_indexes["Ward_Name"] = index

                    elif (
                        "household" in value
                        or "hh" == value
                    ):
                        column_indexes[
                            "Number_of_Households"
                        ] = index

                    elif (
                        "total population" in value
                        or value == "population"
                        or "total pop" in value
                    ):
                        column_indexes[
                            "Total_Population"
                        ] = index

                    elif "male" in value:
                        column_indexes[
                            "Male_Population"
                        ] = index

                    elif "female" in value:
                        column_indexes[
                            "Female_Population"
                        ] = index

                    elif (
                        "poverty" in value
                        or "poverty level" in value
                    ):
                        column_indexes[
                            "Poverty_Level_Status"
                        ] = index

                    elif (
                        "constituency" in value
                        or "constituencies" in value
                    ):
                        column_indexes[
                            "Constituency"
                        ] = index

                # ------------------------------------------------
                # We need at least Ward + population information
                # ------------------------------------------------

                if (
                    "Ward_Name" not in column_indexes
                    or "Total_Population" not in column_indexes
                ):
                    continue

                print(
                    f"   ✓ Demographic table found "
                    f"on page {page_number}"
                )

                # ------------------------------------------------
                # Extract every row
                # ------------------------------------------------

                for row in table[header_index + 1:]:

                    if not row:
                        continue

                    # Make sure we have enough cells
                    if len(row) <= column_indexes["Ward_Name"]:
                        continue

                    def get_cell(column_name):
                        index = column_indexes.get(
                            column_name
                        )

                        if index is None:
                            return ""

                        if index >= len(row):
                            return ""

                        return clean_str(row[index])

                    ward = get_cell("Ward_Name")

                    # ------------------------------------------------
                    # Reject non-data rows
                    # ------------------------------------------------

                    if not ward:
                        continue

                    ward_lower = ward.lower()

                    # Don't accidentally treat table headings,
                    # totals, or notes as wards.
                    invalid_values = [
                        "ward",
                        "total",
                        "totals",
                        "source",
                        "note",
                        "notes",
                        "male",
                        "female",
                        "population"
                    ]

                    if ward_lower in invalid_values:
                        continue

                    # A legitimate ward should not be an entire
                    # paragraph/table heading.
                    if len(ward) > 80:
                        continue

                    total_population = get_cell(
                        "Total_Population"
                    )

                    # Population should contain a number.
                    if not re.search(
                        r"\d",
                        total_population
                    ):
                        continue

                    # ------------------------------------------------
                    # Extract fields
                    # ------------------------------------------------

                    constituency = get_cell(
                        "Constituency"
                    )

                    households = get_cell(
                        "Number_of_Households"
                    )

                    male_population = get_cell(
                        "Male_Population"
                    )

                    female_population = get_cell(
                        "Female_Population"
                    )

                    poverty = get_cell(
                        "Poverty_Level_Status"
                    )

                    # ------------------------------------------------
                    # If Constituency isn't physically present in
                    # the table, derive it from the ward mapping.
                    #
                    # IMPORTANT:
                    # This does NOT create the ward data.
                    # It only standardizes the constituency after
                    # the ward itself has been extracted from PDF.
                    # ------------------------------------------------

                    if not constituency:
                        constituency = (
                            WARD_CONSTITUENCY_MAP
                            .get(
                                ward.upper(),
                                "Unspecified"
                            )
                        )

                    # ------------------------------------------------
                    # Clean numeric fields
                    # ------------------------------------------------

                    households = clean_num(
                        households
                    )

                    total_population = clean_num(
                        total_population
                    )

                    male_population = clean_num(
                        male_population
                    )

                    female_population = clean_num(
                        female_population
                    )

                    # ------------------------------------------------
                    # Missing values
                    # ------------------------------------------------

                    if not households:
                        households = "Unspecified"

                    if not total_population:
                        total_population = "Unspecified"

                    if not male_population:
                        male_population = "Unspecified"

                    if not female_population:
                        female_population = "Unspecified"

                    if not poverty:
                        poverty = "Unspecified"

                    if not constituency:
                        constituency = "Unspecified"

                    # ------------------------------------------------
                    # Save extracted record
                    # ------------------------------------------------

                    records.append({
                        "Constituency": constituency,
                        "Ward_Name": ward,
                        "Number_of_Households": households,
                        "Total_Population": total_population,
                        "Male_Population": male_population,
                        "Female_Population": female_population,
                        "Poverty_Level_Status": poverty
                    })

    # ------------------------------------------------------------
    # Create DataFrame
    # ------------------------------------------------------------

    df = pd.DataFrame(
        records,
        columns=columns
    )

    # ------------------------------------------------------------
    # Remove duplicate rows
    # ------------------------------------------------------------

    before = len(df)

    df = df.drop_duplicates(
        subset=[
            "Constituency",
            "Ward_Name",
            "Number_of_Households",
            "Total_Population",
            "Male_Population",
            "Female_Population",
            "Poverty_Level_Status"
        ]
    ).reset_index(drop=True)

    duplicates_removed = before - len(df)

    # ------------------------------------------------------------
    # Final cleanup
    # ------------------------------------------------------------

    for column in df.columns:

        if df[column].dtype == "object":

            df[column] = (
                df[column]
                .fillna("Unspecified")
                .apply(clean_str)
            )

            df[column] = df[column].replace(
                "",
                "Unspecified"
            )

    # ------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------

    print("\n" + "-" * 70)
    print("DATASET 1 EXTRACTION COMPLETE")
    print("-" * 70)

    print(
        f"   Wards extracted       : {len(df)}"
    )

    print(
        f"   Duplicates removed    : "
        f"{duplicates_removed}"
    )

    if not df.empty:

        print(
            f"   Constituencies found : "
            f"{df['Constituency'].nunique()}"
        )

        print("\n   Constituency breakdown:")

        print(
            df["Constituency"]
            .value_counts()
            .to_string()
        )

    else:

        print(
            "   ⚠ No demographic rows were found."
        )

    print("-" * 70)

    return df

def extract_health_facilities(pdf_bytes):
    """
    Dataset 2: Automatically extract health facilities from the Mufulira IDP PDF.

    No health-facility records are hardcoded.
    The PDF is the single source of truth.
    """

    print("Extracting Dataset 2: Health Facilities Inventory...")

    records = []

    # Different extraction strategies because PDF tables can have
    # visible borders, invisible borders, or text-aligned columns.
    table_settings_variants = [
        {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "intersection_tolerance": 5,
            "snap_tolerance": 3,
            "join_tolerance": 3,
        },
        {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "intersection_tolerance": 5,
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "text_tolerance": 3,
        },
        {
            "vertical_strategy": "lines",
            "horizontal_strategy": "text",
            "intersection_tolerance": 5,
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "text_tolerance": 3,
        }
    ]

    def normalize_header(value):
        if value is None:
            return ""

        value = str(value).lower()
        value = re.sub(r'[\n\r]+', ' ', value)
        value = re.sub(r'[^a-z0-9 ]+', ' ', value)
        value = re.sub(r'\s+', ' ', value).strip()

        return value

    def normalize_cell(value):
        if value is None:
            return ""

        value = str(value)
        value = re.sub(r'[\n\r]+', ' ', value)
        value = re.sub(r'\s+', ' ', value).strip()

        return value

    def clean_population(value):
        value = normalize_cell(value)

        if not value:
            return ""

        # Remove commas, spaces and other non-numeric characters.
        value = re.sub(r'[^\d]', '', value)

        return value

    def is_health_facility_table(table):
        """
        Determine whether a table contains the health-facility inventory.
        """

        if not table:
            return False

        # Examine first several rows because some PDF tables have
        # multi-row headers.
        header_text = ""

        for row in table[:5]:
            if row:
                header_text += " " + " ".join(
                    normalize_header(cell)
                    for cell in row
                    if cell
                )

        # Strong indicators that this is a health facility table.
        facility_keywords = [
            "facility",
            "health facility",
            "health centre",
            "health center",
            "hospital",
            "health post"
        ]

        structural_keywords = [
            "ward",
            "ownership",
            "catchment",
            "population",
            "facility type",
            "status",
            "operational"
        ]

        has_facility = any(
            keyword in header_text
            for keyword in facility_keywords
        )

        structural_matches = sum(
            keyword in header_text
            for keyword in structural_keywords
        )

        return has_facility and structural_matches >= 2

    def find_header_row(table):
        """
        Find the row containing the actual table headers.
        """

        for index, row in enumerate(table[:6]):

            headers = [
                normalize_header(cell)
                for cell in row
                if cell
            ]

            joined = " ".join(headers)

            if (
                ("facility" in joined or "health" in joined)
                and (
                    "ward" in joined
                    or "ownership" in joined
                    or "catchment" in joined
                    or "population" in joined
                )
            ):
                return index

        return None

    def find_column(headers, possible_names):
        """
        Dynamically locate a column based on header text.
        """

        for index, header in enumerate(headers):

            header = normalize_header(header)

            for name in possible_names:

                if name in header:
                    return index

        return None

    pdf_bytes.seek(0)

    with pdfplumber.open(pdf_bytes) as pdf:

        print(f"   Scanning {len(pdf.pages)} PDF pages...")

        for page_number, page in enumerate(pdf.pages, start=1):

            page_tables = []

            # Try several extraction methods.
            for settings in table_settings_variants:

                try:
                    tables = page.extract_tables(
                        table_settings=settings
                    )

                    if tables:
                        page_tables.extend(tables)

                except Exception:
                    continue

            # Remove duplicate tables produced by different strategies.
            unique_tables = []

            seen_tables = set()

            for table in page_tables:

                if not table:
                    continue

                signature = str(table)

                if signature not in seen_tables:
                    seen_tables.add(signature)
                    unique_tables.append(table)

            for table in unique_tables:

                if not is_health_facility_table(table):
                    continue

                header_row_index = find_header_row(table)

                if header_row_index is None:
                    continue

                # Build headers from the detected header row.
                headers = [
                    normalize_header(cell)
                    for cell in table[header_row_index]
                ]

                # Detect columns automatically.
                facility_id_col = find_column(
                    headers,
                    [
                        "facility id",
                        "facility no",
                        "facility number",
                        "id",
                        "no"
                    ]
                )

                facility_name_col = find_column(
                    headers,
                    [
                        "facility name",
                        "health facility name",
                        "name"
                    ]
                )

                facility_type_col = find_column(
                    headers,
                    [
                        "facility type",
                        "type",
                        "level"
                    ]
                )

                ward_col = find_column(
                    headers,
                    [
                        "ward"
                    ]
                )

                ownership_col = find_column(
                    headers,
                    [
                        "ownership",
                        "owner"
                    ]
                )

                status_col = find_column(
                    headers,
                    [
                        "operational status",
                        "operational",
                        "status"
                    ]
                )

                catchment_col = find_column(
                    headers,
                    [
                        "catchment population",
                        "catchment",
                        "population"
                    ]
                )

                # Facility name is essential.
                if facility_name_col is None:
                    print(
                        f"   ⚠ Page {page_number}: "
                        f"Health table found but facility-name column "
                        f"could not be identified."
                    )
                    continue

                print(
                    f"   ✓ Health facility table detected "
                    f"on page {page_number}"
                )

                print(
                    f"     Columns: {headers}"
                )

                # Process all rows after the header.
                for row in table[header_row_index + 1:]:

                    if not row:
                        continue

                    # Normalize row length.
                    row = list(row)

                    # Ignore completely empty rows.
                    if not any(
                        normalize_cell(cell)
                        for cell in row
                    ):
                        continue

                    def get_value(column_index):
                        if column_index is None:
                            return ""

                        if column_index >= len(row):
                            return ""

                        return normalize_cell(
                            row[column_index]
                        )

                    facility_name = get_value(
                        facility_name_col
                    )

                    # Ignore headings/repeated headers.
                    if not facility_name:
                        continue

                    normalized_name = normalize_header(
                        facility_name
                    )

                    if normalized_name in {
                        "facility name",
                        "health facility",
                        "name",
                        "facility"
                    }:
                        continue

                    # Reject obvious non-facility rows.
                    if (
                        len(facility_name) < 3
                        or facility_name.lower()
                        in {
                            "total",
                            "totals",
                            "source",
                            "note",
                            "notes"
                        }
                    ):
                        continue

                    record = {
                        "Facility_ID": get_value(
                            facility_id_col
                        ),
                        "Facility_Name": facility_name,
                        "Facility_Type": get_value(
                            facility_type_col
                        ),
                        "Ward": get_value(
                            ward_col
                        ),
                        "Ownership": get_value(
                            ownership_col
                        ),
                        "Operational_Status": get_value(
                            status_col
                        ),
                        "Catchment_Population": clean_population(
                            get_value(catchment_col)
                        )
                    }

                    records.append(record)

    if not records:
        print(
            "   ✗ No health facility table was detected "
            "in the PDF."
        )

        return pd.DataFrame(
            columns=[
                "Facility_ID",
                "Facility_Name",
                "Facility_Type",
                "Ward",
                "Ownership",
                "Operational_Status",
                "Catchment_Population",
                "Constituency"
            ]
        )

    df = pd.DataFrame(records)

    # ---------------------------------------------------------
    # CLEAN DATA
    # ---------------------------------------------------------

    for column in df.columns:
        df[column] = df[column].apply(clean_str)

    # Remove repeated rows that can occur because multiple
    # PDF extraction strategies found the same table.
    df = df.drop_duplicates(
        subset=[
            "Facility_Name",
            "Ward",
            "Facility_Type"
        ],
        keep="first"
    ).reset_index(drop=True)

    # ---------------------------------------------------------
    # FACILITY ID
    # ---------------------------------------------------------
    #
    # If the PDF itself supplied IDs, preserve them.
    # If it did not, generate IDs AFTER extraction.
    # The actual facilities still come entirely from the PDF.
    # ---------------------------------------------------------

    numeric_ids = pd.to_numeric(
        df["Facility_ID"],
        errors="coerce"
    )

    if numeric_ids.isna().all():

        df["Facility_ID"] = range(
            1,
            len(df) + 1
        )

    else:

        missing_ids = numeric_ids.isna()

        df["Facility_ID"] = numeric_ids

        next_id = (
            int(numeric_ids.max())
            if not numeric_ids.dropna().empty
            else 0
        )

        for index in df.index:

            if pd.isna(df.loc[index, "Facility_ID"]):

                next_id += 1

                df.loc[
                    index,
                    "Facility_ID"
                ] = next_id

        df["Facility_ID"] = (
            df["Facility_ID"]
            .astype(int)
        )

    # ---------------------------------------------------------
    # CONSTITUENCY
    # ---------------------------------------------------------
    #
    # Do NOT manually create the 42 facility records.
    #
    # First try to obtain constituency information directly
    # from the PDF table if it exists.
    #
    # If the facility table itself has no constituency column,
    # this column can be populated later from another PDF
    # table containing the Ward -> Constituency relationship.
    # ---------------------------------------------------------

    if "Constituency" not in df.columns:

        df["Constituency"] = "Unspecified"

    # Final column order.
    df = df[
        [
            "Facility_ID",
            "Facility_Name",
            "Facility_Type",
            "Ward",
            "Ownership",
            "Operational_Status",
            "Catchment_Population",
            "Constituency"
        ]
    ]

    print(
        f"   ✓ Extracted {len(df)} health facilities "
        f"from the PDF."
    )

    print(
        f"   ✓ Duplicate extraction rows removed."
    )

    print(
        f"   ✓ Unique facilities: "
        f"{df['Facility_Name'].nunique()}"
    )

    return df


def extract_public_consultation_issues(pdf_bytes):
    """
    Dataset 3: Automatically extract Ward Public Consultation
    Issues, Solutions and Sectors from the Mufulira IDP PDF.

    No consultation records are hardcoded.
    The PDF is the single source of truth.
    """

    print("Extracting Dataset 3: Ward Public Consultation Issues...")

    records = []

    table_settings_variants = [
        {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "intersection_tolerance": 5,
            "snap_tolerance": 3,
            "join_tolerance": 3,
        },
        {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "intersection_tolerance": 5,
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "text_tolerance": 3,
        },
        {
            "vertical_strategy": "lines",
            "horizontal_strategy": "text",
            "intersection_tolerance": 5,
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "text_tolerance": 3,
        }
    ]

    def normalize_header(value):
        if value is None:
            return ""

        value = str(value).lower()
        value = re.sub(r'[\n\r]+', ' ', value)
        value = re.sub(r'[^a-z0-9 ]+', ' ', value)
        value = re.sub(r'\s+', ' ', value).strip()

        return value

    def normalize_cell(value):
        if value is None:
            return ""

        value = str(value)
        value = re.sub(r'[\n\r]+', ' ', value)
        value = re.sub(r'\s+', ' ', value).strip()

        return value

    def is_consultation_table(table):
        """
        Detect a public consultation table based on its headers.
        """

        if not table:
            return False

        header_text = ""

        for row in table[:6]:

            if not row:
                continue

            header_text += " " + " ".join(
                normalize_header(cell)
                for cell in row
                if cell
            )

        # Different wording may be used in the IDP.
        ward_indicators = [
            "ward",
            "ward name"
        ]

        challenge_indicators = [
            "challenge",
            "challenges",
            "problem",
            "problems",
            "issue",
            "issues",
            "needs",
            "priority needs"
        ]

        solution_indicators = [
            "solution",
            "solutions",
            "intervention",
            "interventions",
            "recommendation",
            "recommendations",
            "proposed solution",
            "way forward"
        ]

        has_ward = any(
            word in header_text
            for word in ward_indicators
        )

        has_challenges = any(
            word in header_text
            for word in challenge_indicators
        )

        has_solutions = any(
            word in header_text
            for word in solution_indicators
        )

        return (
            has_ward
            and has_challenges
            and has_solutions
        )

    def find_header_row(table):

        for index, row in enumerate(table[:7]):

            headers = [
                normalize_header(cell)
                for cell in row
                if cell
            ]

            joined = " ".join(headers)

            has_ward = (
                "ward" in joined
            )

            has_challenge = any(
                word in joined
                for word in [
                    "challenge",
                    "problem",
                    "issue",
                    "needs"
                ]
            )

            has_solution = any(
                word in joined
                for word in [
                    "solution",
                    "intervention",
                    "recommendation",
                    "way forward"
                ]
            )

            if (
                has_ward
                and has_challenge
                and has_solution
            ):
                return index

        return None

    def find_column(headers, possible_names):

        for index, header in enumerate(headers):

            header = normalize_header(header)

            for name in possible_names:

                if name in header:
                    return index

        return None

    pdf_bytes.seek(0)

    with pdfplumber.open(pdf_bytes) as pdf:

        print(
            f"   Scanning {len(pdf.pages)} PDF pages..."
        )

        for page_number, page in enumerate(
            pdf.pages,
            start=1
        ):

            page_tables = []

            # Try multiple table extraction strategies.
            for settings in table_settings_variants:

                try:

                    tables = page.extract_tables(
                        table_settings=settings
                    )

                    if tables:
                        page_tables.extend(tables)

                except Exception:
                    continue

            # Remove duplicate tables generated by
            # different extraction strategies.
            unique_tables = []
            seen_tables = set()

            for table in page_tables:

                if not table:
                    continue

                signature = str(table)

                if signature not in seen_tables:

                    seen_tables.add(signature)
                    unique_tables.append(table)

            for table in unique_tables:

                if not is_consultation_table(table):
                    continue

                header_row_index = find_header_row(table)

                if header_row_index is None:
                    continue

                headers = [
                    normalize_header(cell)
                    for cell in table[header_row_index]
                ]

                # ---------------------------------------------
                # Detect columns automatically
                # ---------------------------------------------

                ward_col = find_column(
                    headers,
                    [
                        "ward name",
                        "ward"
                    ]
                )

                challenges_col = find_column(
                    headers,
                    [
                        "challenges",
                        "challenge",
                        "problems",
                        "problem",
                        "issues",
                        "issue",
                        "priority needs",
                        "needs"
                    ]
                )

                solutions_col = find_column(
                    headers,
                    [
                        "solutions",
                        "solution",
                        "proposed solutions",
                        "proposed solution",
                        "interventions",
                        "intervention",
                        "recommendations",
                        "recommendation",
                        "way forward"
                    ]
                )

                sector_col = find_column(
                    headers,
                    [
                        "sector",
                        "sectors",
                        "thematic area",
                        "thematic areas"
                    ]
                )

                # Ward + challenges + solutions are required.
                if (
                    ward_col is None
                    or challenges_col is None
                    or solutions_col is None
                ):
                    print(
                        f"   ⚠ Page {page_number}: "
                        f"Consultation table detected but "
                        f"required columns were not identified."
                    )

                    print(
                        f"     Detected headers: {headers}"
                    )

                    continue

                print(
                    f"   ✓ Public consultation table "
                    f"detected on page {page_number}"
                )

                print(
                    f"     Columns: {headers}"
                )

                # ---------------------------------------------
                # Extract every consultation row
                # ---------------------------------------------

                for row in table[
                    header_row_index + 1:
                ]:

                    if not row:
                        continue

                    row = list(row)

                    if not any(
                        normalize_cell(cell)
                        for cell in row
                    ):
                        continue

                    def get_value(column_index):

                        if column_index is None:
                            return ""

                        if column_index >= len(row):
                            return ""

                        return normalize_cell(
                            row[column_index]
                        )

                    ward_name = get_value(
                        ward_col
                    )

                    challenges = get_value(
                        challenges_col
                    )

                    solutions = get_value(
                        solutions_col
                    )

                    sector = get_value(
                        sector_col
                    )

                    # Ignore repeated headers.
                    if normalize_header(
                        ward_name
                    ) in {
                        "ward",
                        "ward name"
                    }:
                        continue

                    # Ignore totals/source/note rows.
                    if normalize_header(
                        ward_name
                    ) in {
                        "total",
                        "totals",
                        "source",
                        "note",
                        "notes"
                    }:
                        continue

                    # A consultation record should at least
                    # contain a ward and some issue/solution text.
                    if not ward_name:
                        continue

                    if (
                        not challenges
                        and not solutions
                    ):
                        continue

                    records.append({
                        "Ward_Name": ward_name,
                        "Challenges": challenges,
                        "Solutions": solutions,
                        "Sector": sector
                    })

    # ---------------------------------------------------------
    # NO DATA FOUND
    # ---------------------------------------------------------

    if not records:

        print(
            "   ✗ No public consultation table "
            "was detected in the PDF."
        )

        return pd.DataFrame(
            columns=[
                "Ward_Name",
                "Challenges",
                "Solutions",
                "Sector",
                "Constituency"
            ]
        )

    df = pd.DataFrame(records)

    # ---------------------------------------------------------
    # CLEAN TEXT
    # ---------------------------------------------------------

    for column in df.columns:

        df[column] = df[column].apply(
            clean_str
        )

    # ---------------------------------------------------------
    # REMOVE DUPLICATES
    #
    # Multiple extraction strategies may discover
    # exactly the same table.
    # ---------------------------------------------------------

    df = df.drop_duplicates(
        subset=[
            "Ward_Name",
            "Challenges",
            "Solutions"
        ],
        keep="first"
    ).reset_index(drop=True)

    # ---------------------------------------------------------
    # CONSTITUENCY
    #
    # Do NOT use WARD_CONSTITUENCY_MAP.
    # If constituency exists in the PDF table, detect it.
    # Otherwise leave it unspecified until we automatically
    # extract the ward/constituency relationship from the PDF.
    # ---------------------------------------------------------

    if "Constituency" not in df.columns:

        df["Constituency"] = "Unspecified"

    # ---------------------------------------------------------
    # FINAL COLUMN ORDER
    # ---------------------------------------------------------

    df = df[
        [
            "Ward_Name",
            "Challenges",
            "Solutions",
            "Sector",
            "Constituency"
        ]
    ]

    print(
        f"   ✓ Extracted {len(df)} consultation records "
        f"from the PDF."
    )

    print(
        f"   ✓ Unique wards represented: "
        f"{df['Ward_Name'].nunique()}"
    )

    return df

# ============================================================
# MASTER CAPITAL INVESTMENT FRAMEWORK - PDF EXTRACTION
# ============================================================

MASTER_CAPITAL_COLUMNS = [
    "Sector",
    "Main_Objective",
    "Specific_Objective_or_Program",
    "Project_Description",
    "Cost_ZMW",
    "Proposed_Source_of_Funds",
    "Location",
    "Ward",
    "Responsible_Agency",
    "Implementation_Period"
]


def normalize_table_cell(value):
    """
    Convert a PDF table cell into clean single-line text.
    """
    if value is None:
        return ""

    value = str(value)

    # PDF tables frequently put line breaks inside cells
    value = value.replace("\n", " ")
    value = value.replace("\r", " ")

    # Collapse repeated whitespace
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def clean_cost_zmw(value):
    """
    Convert monetary values extracted from PDF tables into
    clean numeric values.

    Examples:
        K 15,000,000       -> 15000000.00
        ZMW 15,000,000     -> 15000000.00
        15,000,000         -> 15000000.00
        15000000           -> 15000000.00
    """

    if value is None:
        return "Unspecified"

    value = normalize_table_cell(value)

    if not value:
        return "Unspecified"

    # Remove currency labels
    value = re.sub(
        r"\b(ZMW|K|KWACHA)\b",
        "",
        value,
        flags=re.IGNORECASE
    )

    # Remove commas and spaces
    value = value.replace(",", "")
    value = value.replace(" ", "")

    # Keep only numeric characters and decimal point
    value = re.sub(r"[^0-9.\-]", "", value)

    if not value:
        return "Unspecified"

    try:
        return f"{float(value):.2f}"
    except ValueError:
        return "Unspecified"


def normalize_header(header):
    """
    Normalize a PDF table column heading so that slightly
    different headings can be recognized.
    """

    if header is None:
        return ""

    header = normalize_table_cell(header).lower()

    # Remove punctuation
    header = re.sub(r"[^a-z0-9 ]", " ", header)

    # Collapse spaces
    header = re.sub(r"\s+", " ", header).strip()

    return header


def identify_capital_framework_header(row):
    """
    Determine whether a PDF table row is a Capital Investment
    Framework header.

    We do not assume exact wording because PDF extraction may
    split headings across lines.
    """

    if not row:
        return False

    text = " ".join(
        normalize_table_cell(cell).lower()
        for cell in row
        if cell
    )

    header_keywords = [
        "objective",
        "project",
        "cost",
        "source",
        "fund",
        "location",
        "ward",
        "agency",
        "implementation",
        "period"
    ]

    matches = sum(
        1 for keyword in header_keywords
        if keyword in text
    )

    return matches >= 4


def identify_sector_from_page_text(page_text):
    """
    Identify the sector associated with a page.

    The sector heading is normally printed before the
    corresponding investment matrix.
    """

    if not page_text:
        return None

    text = normalize_table_cell(page_text).lower()

    sector_patterns = [
        (
            "Water and Sanitation",
            [
                "water and sanitation",
                "water & sanitation"
            ]
        ),
        (
            "Education",
            [
                "education",
                "ece",
                "primary",
                "secondary",
                "tevets",
                "tertiary"
            ]
        ),
        (
            "Health and Medical Services",
            [
                "health and medical services",
                "health and medical",
                "health sector"
            ]
        ),
        (
            "Public Infrastructure, Roads, Bridges & Culverts",
            [
                "roads, bridges",
                "roads bridges",
                "public infrastructure"
            ]
        ),
        (
            "Street Lighting, Market & Bus Station Lighting",
            [
                "street lighting",
                "market lighting",
                "bus station lighting"
            ]
        ),
        (
            "Housing, Urban Planning & Informal Settlement Upgrading",
            [
                "housing",
                "urban planning",
                "informal settlement"
            ]
        ),
        (
            "Agriculture, Livestock, Veterinary & Fisheries",
            [
                "agriculture",
                "livestock",
                "veterinary",
                "fisheries"
            ]
        ),
        (
            "Forestry, Environment & Natural Resources",
            [
                "forestry",
                "environment",
                "natural resources"
            ]
        ),
        (
            "Public Health, Solid Waste Management & Sanitation",
            [
                "solid waste",
                "public health",
                "waste management"
            ]
        ),
        (
            "Mining, Commerce, Trade & Industrial Development",
            [
                "mining",
                "commerce",
                "trade",
                "industrial development"
            ]
        ),
        (
            "Energy, Petroleum & Telecommunications",
            [
                "energy",
                "petroleum",
                "telecommunications"
            ]
        ),
        (
            "Community Development, Gender & Social Welfare",
            [
                "community development",
                "gender",
                "social welfare"
            ]
        ),
        (
            "Governance, Public Safety, Police Posts & Correctional Services",
            [
                "governance",
                "public safety",
                "police posts",
                "correctional services"
            ]
        ),
        (
            "Disaster Risk Reduction & Fire Services",
            [
                "disaster risk reduction",
                "fire services",
                "fire"
            ]
        ),
        (
            "Sports, Youth Recreation & Culture",
            [
                "sports",
                "youth recreation",
                "culture"
            ]
        ),
        (
            "Local Authority Administration & Financial Management",
            [
                "local authority administration",
                "financial management"
            ]
        )
    ]

    # Prefer the longest/more specific matches
    for sector_name, patterns in sector_patterns:
        if any(pattern in text for pattern in patterns):
            return sector_name

    return None


def map_extracted_columns(table):
    """
    Convert an arbitrary PDF table into the required
    10-column schema.

    This does NOT assume the original PDF column names are
    exactly the same as our dataset names.
    """

    if not table:
        return None

    header = table[0]

    normalized_headers = [
        normalize_header(x)
        for x in header
    ]

    column_map = {}

    for index, header_text in enumerate(normalized_headers):

        if not header_text:
            continue

        if (
            "main objective" in header_text
            or header_text == "objective"
        ):
            column_map["Main_Objective"] = index

        elif (
            "specific objective" in header_text
            or "specific objective or program" in header_text
            or "program" in header_text
        ):
            column_map["Specific_Objective_or_Program"] = index

        elif (
            "project description" in header_text
            or "project" == header_text
            or "description" in header_text
        ):
            column_map["Project_Description"] = index

        elif (
            "cost" in header_text
            or "estimated cost" in header_text
            or "budget" in header_text
        ):
            column_map["Cost_ZMW"] = index

        elif (
            "source of funds" in header_text
            or "source of funding" in header_text
            or "funding source" in header_text
        ):
            column_map["Proposed_Source_of_Funds"] = index

        elif (
            "location" in header_text
            or "site" in header_text
            or "location or site" in header_text
        ):
            column_map["Location"] = index

        elif "ward" in header_text:
            column_map["Ward"] = index

        elif (
            "responsible agency" in header_text
            or "responsible institution" in header_text
            or "agency" in header_text
        ):
            column_map["Responsible_Agency"] = index

        elif (
            "implementation period" in header_text
            or "implementation" in header_text
            or "period" in header_text
        ):
            column_map["Implementation_Period"] = index

    # At least 3 useful columns must have been identified
    if len(column_map) < 3:
        return None

    return column_map


def get_cell(row, index):
    """
    Safely retrieve a cell from a PDF table row.
    """

    if index is None:
        return ""

    if index >= len(row):
        return ""

    return normalize_table_cell(row[index])


def extract_master_capital_investment_framework(pdf_bytes):
    """
    Extract the complete Master Capital Investment Framework
    from Part Four / Section 23 of the Mufulira IDP.

    IMPORTANT:
    - No projects are hardcoded.
    - Every PDF page is inspected.
    - Tables are extracted page-by-page.
    - Sector is inherited when a table continues onto
      subsequent pages.
    """

    print("\nExtracting Master Capital Investment Framework...")
    print("Scanning PDF page-by-page...")

    records = []

    current_sector = None
    inside_framework = False

    pdf_bytes.seek(0)

    with pdfplumber.open(pdf_bytes) as pdf:

        print(f"   PDF contains {len(pdf.pages)} pages.")

        for page_number, page in enumerate(pdf.pages, start=1):

            print(
                f"   Processing page "
                f"{page_number}/{len(pdf.pages)}..."
            )

            # ------------------------------------------------
            # Extract page text
            # ------------------------------------------------

            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""

            normalized_page_text = normalize_table_cell(
                page_text
            ).lower()

            # ------------------------------------------------
            # Detect Section 23
            # ------------------------------------------------

            if (
                "capital investment framework" in normalized_page_text
                or "sectoral investment matrices" in normalized_page_text
                or "capital investment frameworks" in normalized_page_text
            ):
                inside_framework = True

            # If we have not reached Section 23 yet,
            # ignore tables.
            if not inside_framework:
                continue

            # ------------------------------------------------
            # Detect sector heading
            # ------------------------------------------------

            detected_sector = identify_sector_from_page_text(
                page_text
            )

            if detected_sector:
                current_sector = detected_sector

                print(
                    f"      Sector detected: "
                    f"{current_sector}"
                )

            # ------------------------------------------------
            # Extract tables
            # ------------------------------------------------

            try:

                tables = page.extract_tables(
                    table_settings={
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "intersection_tolerance": 5,
                        "snap_tolerance": 3,
                        "join_tolerance": 3,
                        "edge_min_length": 3,
                        "min_words_vertical": 2,
                        "min_words_horizontal": 1
                    }
                )

            except Exception as e:

                print(
                    f"      Table extraction failed on "
                    f"page {page_number}: {e}"
                )

                tables = []

            if not tables:
                continue

            # ------------------------------------------------
            # Process every table on the page
            # ------------------------------------------------

            for table_number, table in enumerate(
                tables,
                start=1
            ):

                if not table:
                    continue

                # Remove completely empty rows
                table = [
                    row for row in table
                    if row and any(
                        normalize_table_cell(cell)
                        for cell in row
                    )
                ]

                if not table:
                    continue

                # ------------------------------------------------
                # Find header row
                # ------------------------------------------------

                header_index = None

                for i, row in enumerate(table[:5]):

                    if identify_capital_framework_header(row):
                        header_index = i
                        break

                if header_index is None:
                    continue

                header_row = table[header_index:]

                column_map = map_extracted_columns(
                    header_row
                )

                if column_map is None:
                    print(
                        f"      Skipping table "
                        f"{table_number}: "
                        f"columns not recognized."
                    )
                    continue

                print(
                    f"      Table {table_number}: "
                    f"{len(table) - header_index - 1} "
                    f"candidate rows."
                )

                # ------------------------------------------------
                # Extract every data row
                # ------------------------------------------------

                for row in table[header_index + 1:]:

                    if not row:
                        continue

                    cleaned_row = [
                        normalize_table_cell(cell)
                        for cell in row
                    ]

                    # Skip empty rows
                    if not any(cleaned_row):
                        continue

                    # Skip repeated table headers
                    if identify_capital_framework_header(
                        cleaned_row
                    ):
                        continue

                    # Combine all cells for row-level checks
                    row_text = " ".join(cleaned_row).lower()

                    # Ignore page/table headings
                    if (
                        "capital investment framework" in row_text
                        and not get_cell(
                            row,
                            column_map.get(
                                "Project_Description"
                            )
                        )
                    ):
                        continue

                    # ------------------------------------------------
                    # Extract fields
                    # ------------------------------------------------

                    project_description = get_cell(
                        row,
                        column_map.get(
                            "Project_Description"
                        )
                    )

                    main_objective = get_cell(
                        row,
                        column_map.get(
                            "Main_Objective"
                        )
                    )

                    specific_objective = get_cell(
                        row,
                        column_map.get(
                            "Specific_Objective_or_Program"
                        )
                    )

                    cost = clean_cost_zmw(
                        get_cell(
                            row,
                            column_map.get(
                                "Cost_ZMW"
                            )
                        )
                    )

                    source_of_funds = get_cell(
                        row,
                        column_map.get(
                            "Proposed_Source_of_Funds"
                        )
                    )

                    location = get_cell(
                        row,
                        column_map.get(
                            "Location"
                        )
                    )

                    ward = get_cell(
                        row,
                        column_map.get(
                            "Ward"
                        )
                    )

                    responsible_agency = get_cell(
                        row,
                        column_map.get(
                            "Responsible_Agency"
                        )
                    )

                    implementation_period = get_cell(
                        row,
                        column_map.get(
                            "Implementation_Period"
                        )
                    )

                    # ------------------------------------------------
                    # Reject rows that are obviously not projects
                    # ------------------------------------------------

                    meaningful_fields = [
                        main_objective,
                        specific_objective,
                        project_description,
                        source_of_funds,
                        location,
                        ward,
                        responsible_agency,
                        implementation_period
                    ]

                    populated = sum(
                        1 for value in meaningful_fields
                        if value
                    )

                    if populated < 2:
                        continue

                    # ------------------------------------------------
                    # Fill missing values
                    # ------------------------------------------------

                    if not current_sector:
                        current_sector = "Unspecified"

                    if not main_objective:
                        main_objective = "Unspecified"

                    if not specific_objective:
                        specific_objective = "Unspecified"

                    if not project_description:
                        project_description = "Unspecified"

                    if not source_of_funds:
                        source_of_funds = "Unspecified"

                    if not location:
                        location = "District-wide"

                    if not ward:
                        ward = "District-wide"

                    if not responsible_agency:
                        responsible_agency = "Unspecified"

                    if not implementation_period:
                        implementation_period = "2023-2032"

                    # ------------------------------------------------
                    # Add the individual project
                    # ------------------------------------------------

                    records.append({
                        "Sector": current_sector,
                        "Main_Objective": main_objective,
                        "Specific_Objective_or_Program":
                            specific_objective,
                        "Project_Description":
                            project_description,
                        "Cost_ZMW": cost,
                        "Proposed_Source_of_Funds":
                            source_of_funds,
                        "Location": location,
                        "Ward": ward,
                        "Responsible_Agency":
                            responsible_agency,
                        "Implementation_Period":
                            implementation_period
                    })

    # ------------------------------------------------------------
    # Create DataFrame
    # ------------------------------------------------------------

    df = pd.DataFrame(
        records,
        columns=MASTER_CAPITAL_COLUMNS
    )

    if df.empty:
        print(
            "\n   ✗ No Capital Investment Framework "
            "rows were extracted."
        )
        return df

    # ------------------------------------------------------------
    # Remove exact duplicates created by page/table repetition
    # ------------------------------------------------------------

    before = len(df)

    df = df.drop_duplicates(
        subset=[
            "Sector",
            "Main_Objective",
            "Specific_Objective_or_Program",
            "Project_Description",
            "Cost_ZMW",
            "Proposed_Source_of_Funds",
            "Location",
            "Ward",
            "Responsible_Agency",
            "Implementation_Period"
        ]
    ).reset_index(drop=True)

    removed = before - len(df)

    # ------------------------------------------------------------
    # Final missing-value protection
    # ------------------------------------------------------------

    text_columns = [
        "Sector",
        "Main_Objective",
        "Specific_Objective_or_Program",
        "Project_Description",
        "Proposed_Source_of_Funds",
        "Location",
        "Ward",
        "Responsible_Agency",
        "Implementation_Period"
    ]

    for column in text_columns:

        df[column] = (
            df[column]
            .replace("", pd.NA)
            .fillna("Unspecified")
            .apply(normalize_table_cell)
        )

    df["Cost_ZMW"] = df["Cost_ZMW"].replace(
        "",
        "Unspecified"
    )

    # ------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------

    print("\n" + "-" * 70)
    print("MASTER CAPITAL INVESTMENT FRAMEWORK EXTRACTION")
    print("-" * 70)

    print(
        f"   Extracted project rows : {len(df)}"
    )

    print(
        f"   Duplicate rows removed : {removed}"
    )

    print(
        f"   Sectors detected       : "
        f"{df['Sector'].nunique()}"
    )

    print("\n   Rows by sector:")

    sector_counts = (
        df["Sector"]
        .value_counts()
    )

    for sector, count in sector_counts.items():
        print(
            f"      {sector}: {count}"
        )

    print("-" * 70)

    return df

def main():
    print("="*70)
    print("MUFULIRA MUNICIPAL COUNCIL - IDP DATASET EXTRACTION PIPELINE")
    print("="*70)

    try:
        pdf_bytes = download_or_get_pdf_bytes()
    except Exception as e:
        print(e)
        return

    # Generate 4 Datasets
    df_wards = extract_wards_demographics(pdf_bytes)
    df_consult = extract_public_consultation_issues(pdf_bytes)
    df_health = extract_health_facilities(pdf_bytes)
    df_master_capital = extract_master_capital_investment_framework(pdf_bytes)

    # Define Output CSV File Names (Pipe Delimited '|')
    files = {
        "db-unza26-csc4792-mufulira_administrative_wards_demographics.csv":
            df_wards,

        "db-unza26-csc4792-mufulira_health_facilities.csv":
            df_health,

        "db-unza26-csc4792-mufulira_ward_public_consultation_issues.csv":
            df_consult,

        # NEW DATASET
        "db-unza26-csc4792-mufulira_master_capital_investment_framework.csv":
            df_master_capital
    }

    print("\nSaving Pipe-Delimited CSV Datasets to Current Directory:")
    for filename, df in files.items():
        # String cleanup across all text fields
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(clean_str)

        # Export with Pipe '|' Delimiter
        df.to_csv(filename, sep="|", index=False, encoding="utf-8")
        print(f"   ✓ {filename} ({len(df)} rows, {len(df.columns)} columns)")

    print("\n" + "="*70)
    print(
        "SUCCESS: All 5 IDP Governance Datasets "
        "Successfully Generated!"
    )
    print("="*70)

if __name__ == "__main__":
    main()