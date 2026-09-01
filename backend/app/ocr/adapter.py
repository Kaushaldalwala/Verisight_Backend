"""
adapter.py

OCR Output Adapter — Bridge between Module 1 (OCR Extraction) and Module 2 (Document Validation).

Normalizes different field dict layouts (flat, nested, MRZ vs visual, unpaired text)
from passport, visa, aadhaar, driving license, national ID, and permit OCR wrappers
into a standard dictionary format suitable for DocumentInput.

Handles international variations:
  - Passports: MRZ TD3, TD1, TD2 (ICAO 9303 compliant), all countries
  - Visas: Schengen, US, UK, UAE, Indian, Chinese, etc.
  - National IDs: pan-European, GCC, South Asian, African, LATAM formats
  - Driving Licenses: Indian, EU (Directive 2006/126/EC), US, ASEAN formats
  - Permits: Work, Residency, Travel permits (incl. Estonian/Baltic/Nordic/EU formats)

The layout-agnostic OCR module (generic_document_ocr.py) frequently inverts field
labels and values when the document is multi-lingual (e.g., Estonian ELAMISLUBA cards).
This adapter detects and corrects that inversion via _parse_layout_agnostic_fields().
"""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ISO 3166-1 alpha-3 → alpha-2 lookup (common MRZ country codes)
# ---------------------------------------------------------------------------
_ALPHA3_TO_ALPHA2: dict[str, str] = {
    "AFG": "AF", "ALB": "AL", "DZA": "DZ", "AND": "AD", "AGO": "AO",
    "ARG": "AR", "ARM": "AM", "AUS": "AU", "AUT": "AT", "AZE": "AZ",
    "BHS": "BS", "BHR": "BH", "BGD": "BD", "BLR": "BY", "BEL": "BE",
    "BLZ": "BZ", "BEN": "BJ", "BTN": "BT", "BOL": "BO", "BIH": "BA",
    "BWA": "BW", "BRA": "BR", "BRN": "BN", "BGR": "BG", "BFA": "BF",
    "BDI": "BI", "CPV": "CV", "KHM": "KH", "CMR": "CM", "CAN": "CA",
    "CAF": "CF", "TCD": "TD", "CHL": "CL", "CHN": "CN", "COL": "CO",
    "COM": "KM", "COD": "CD", "COG": "CG", "CRI": "CR", "CIV": "CI",
    "HRV": "HR", "CUB": "CU", "CYP": "CY", "CZE": "CZ", "DNK": "DK",
    "DJI": "DJ", "DOM": "DO", "ECU": "EC", "EGY": "EG", "SLV": "SV",
    "GNQ": "GQ", "ERI": "ER", "EST": "EE", "SWZ": "SZ", "ETH": "ET",
    "FJI": "FJ", "FIN": "FI", "FRA": "FR", "GAB": "GA", "GMB": "GM",
    "GEO": "GE", "DEU": "DE", "GHA": "GH", "GRC": "GR", "GTM": "GT",
    "GIN": "GN", "GNB": "GW", "GUY": "GY", "HTI": "HT", "HND": "HN",
    "HUN": "HU", "ISL": "IS", "IND": "IN", "IDN": "ID", "IRN": "IR",
    "IRQ": "IQ", "IRL": "IE", "ISR": "IL", "ITA": "IT", "JAM": "JM",
    "JPN": "JP", "JOR": "JO", "KAZ": "KZ", "KEN": "KE", "PRK": "KP",
    "KOR": "KR", "KWT": "KW", "KGZ": "KG", "LAO": "LA", "LVA": "LV",
    "LBN": "LB", "LSO": "LS", "LBR": "LR", "LBY": "LY", "LIE": "LI",
    "LTU": "LT", "LUX": "LU", "MDG": "MG", "MWI": "MW", "MYS": "MY",
    "MDV": "MV", "MLI": "ML", "MLT": "MT", "MRT": "MR", "MUS": "MU",
    "MEX": "MX", "MDA": "MD", "MCO": "MC", "MNG": "MN", "MNE": "ME",
    "MAR": "MA", "MOZ": "MZ", "MMR": "MM", "NAM": "NA", "NPL": "NP",
    "NLD": "NL", "NZL": "NZ", "NIC": "NI", "NER": "NE", "NGA": "NG",
    "MKD": "MK", "NOR": "NO", "OMN": "OM", "PAK": "PK", "PAN": "PA",
    "PNG": "PG", "PRY": "PY", "PER": "PE", "PHL": "PH", "POL": "PL",
    "PRT": "PT", "QAT": "QA", "ROU": "RO", "RUS": "RU", "RWA": "RW",
    "SAU": "SA", "SEN": "SN", "SRB": "RS", "SLE": "SL", "SGP": "SG",
    "SVK": "SK", "SVN": "SI", "SOM": "SO", "ZAF": "ZA", "SSD": "SS",
    "ESP": "ES", "LKA": "LK", "SDN": "SD", "SUR": "SR", "SWE": "SE",
    "CHE": "CH", "SYR": "SY", "TWN": "TW", "TJK": "TJ", "TZA": "TZ",
    "THA": "TH", "TLS": "TL", "TGO": "TG", "TTO": "TT", "TUN": "TN",
    "TUR": "TR", "TKM": "TM", "UGA": "UG", "UKR": "UA", "ARE": "AE",
    "GBR": "GB", "USA": "US", "URY": "UY", "UZB": "UZ", "VEN": "VE",
    "VNM": "VN", "YEM": "YE", "ZMB": "ZM", "ZWE": "ZW",
    # Special MRZ codes
    "UNO": "UN", "XOM": "UN", "XXX": "XX",
}


def _normalize_country(raw: str | None) -> str | None:
    """
    Accept an ISO 3166-1 alpha-2, alpha-3, full country name, or MRZ code
    and return a normalised alpha-2 code (or the original string if unknown).
    """
    if not raw:
        return None
    raw = str(raw).strip().upper()
    if len(raw) == 3 and raw in _ALPHA3_TO_ALPHA2:
        return _ALPHA3_TO_ALPHA2[raw]
    if len(raw) == 2:
        return raw
    _NAME_MAP = {
        "INDIA": "IN", "UNITED STATES": "US", "UNITED STATES OF AMERICA": "US",
        "UNITED KINGDOM": "GB", "UNITED ARAB EMIRATES": "AE",
        "CHINA": "CN", "GERMANY": "DE", "FRANCE": "FR", "ITALY": "IT",
        "SPAIN": "ES", "JAPAN": "JP", "RUSSIA": "RU", "AUSTRALIA": "AU",
        "CANADA": "CA", "BRAZIL": "BR", "SOUTH AFRICA": "ZA", "EGYPT": "EG",
        "PAKISTAN": "PK", "BANGLADESH": "BD", "SRI LANKA": "LK",
        "NEPAL": "NP", "BHUTAN": "BT", "MALDIVES": "MV", "MYANMAR": "MM",
        "THAILAND": "TH", "INDONESIA": "ID", "MALAYSIA": "MY",
        "SINGAPORE": "SG", "PHILIPPINES": "PH", "VIETNAM": "VN",
        "SAUDI ARABIA": "SA", "IRAN": "IR", "IRAQ": "IQ",
        "TURKEY": "TR", "ISRAEL": "IL", "JORDAN": "JO", "KUWAIT": "KW",
        "QATAR": "QA", "BAHRAIN": "BH", "OMAN": "OM", "NIGERIA": "NG",
        "KENYA": "KE", "GHANA": "GH", "ETHIOPIA": "ET",
        "DEMOCRATIC REPUBLIC OF CONGO": "CD", "TANZANIA": "TZ",
        "SOUTH KOREA": "KR", "NORTH KOREA": "KP", "MEXICO": "MX",
        "ARGENTINA": "AR", "COLOMBIA": "CO", "CHILE": "CL", "PERU": "PE",
        "UKRAINE": "UA", "POLAND": "PL", "ROMANIA": "RO", "NETHERLANDS": "NL",
        "BELGIUM": "BE", "SWEDEN": "SE", "NORWAY": "NO", "DENMARK": "DK",
        "FINLAND": "FI", "SWITZERLAND": "CH", "AUSTRIA": "AT",
        "PORTUGAL": "PT", "CZECH REPUBLIC": "CZ", "CZECHIA": "CZ",
        "HUNGARY": "HU", "GREECE": "GR", "NEW ZEALAND": "NZ",
        "IRELAND": "IE", "ESTONIA": "EE", "LATVIA": "LV", "LITHUANIA": "LT",
        "CROATIA": "HR", "SLOVENIA": "SI", "SLOVAKIA": "SK", "BULGARIA": "BG",
        "SERBIA": "RS", "ALBANIA": "AL", "NORTH MACEDONIA": "MK",
    }
    return _NAME_MAP.get(raw, raw)


_KNOWN_LABEL_HEADERS = {
    "SEX", "GENDER", "BIRTH DATE", "DATE OF BIRTH", "DOB", "NATIONALITY",
    "ISSUE DATE", "DATE OF ISSUE", "EXPIRATION DATE", "EXPIRY DATE", "VALID UNTIL",
    "PASSPORT NUMBER", "PASSPORT NO", "VISA NUMBER", "VISA NO", "CONTROL NUMBER",
    "GIVEN NAME", "SURNAME", "FULL NAME", "ISSUING POST", "TYPE /CLASS", "CLASS", "ENTRIES"
}


def _clean_str(v: Any) -> str | None:
    """Strip whitespace and return None for empty values or header labels."""
    if v is None:
        return None
    if isinstance(v, list):
        valid_items = [str(x).strip() for x in v if x and str(x).strip().upper() not in _KNOWN_LABEL_HEADERS]
        if not valid_items:
            return None
        s = valid_items[0]
    else:
        s = str(v).strip()
    if not s or s.upper() in _KNOWN_LABEL_HEADERS:
        return None
    return s


def _normalise_gender(raw: Any) -> str | None:
    """Normalise various OCR gender representations to M / F / X."""
    if raw is None:
        return None
    s = str(raw).strip().upper()
    # Handle combined strings like "N / F" or "M / H"
    # Extract just the letter tokens
    tokens = re.split(r"[\s/\\|,]+", s)
    for t in tokens:
        if t in ("M", "MALE", "1", "HOMME", "MASCULINO", "MASC", "ERKEK", "MUŠKI", "H"):
            return "M"
        if t in ("F", "FEMALE", "2", "FEMME", "FEMENINO", "FEM", "KADIN", "ŽENSKI",
                 "N",   # N = Naine (female) in Estonian
                 "K",   # K = Kobieta (female) in Polish
                 "V",   # V = Vrouw (female) in Dutch
                 "W",   # W = Weiblich (female) in German
                 ):
            return "F"
        if t in ("X", "OTHER", "UNSPECIFIED", "DIVERSE", "INDETERMINATE"):
            return "X"
    return s or None


def _normalise_date(raw: Any) -> str | None:
    """
    Try to normalise OCR date strings into YYYY-MM-DD.
    Handles formats produced by MRZ (YYMMDD) and visual OCR.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    # Already ISO
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s

    # MRZ format YYMMDD  (e.g. 850312 → 1985-03-12, 260401 → 2026-04-01)
    if re.match(r"^\d{6}$", s):
        yy, mm, dd = int(s[:2]), int(s[2:4]), int(s[4:6])
        year = (2000 + yy) if yy <= 35 else (1900 + yy)
        return f"{year:04d}-{mm:02d}-{dd:02d}"

    # DD/MM/YYYY or MM/DD/YYYY
    m = re.match(r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})$", s)
    if m:
        a, b, c = m.group(1), m.group(2), m.group(3)
        year = (2000 + int(c)) if len(c) == 2 else int(c)
        return f"{year:04d}-{int(b):02d}-{int(a):02d}"

    # DD MMM YYYY (e.g. 15 JAN 1990)
    _MONTHS = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
        "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
        "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
    }
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})$", s)
    if m:
        dd, mon, yyyy = m.group(1), m.group(2).upper()[:3], m.group(3)
        if mon in _MONTHS:
            return f"{yyyy}-{_MONTHS[mon]}-{int(dd):02d}"

    # YYYY/MM/DD
    m = re.match(r"^(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})$", s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # Partial: just year  "2029"
    if re.match(r"^\d{4}$", s):
        return s   # keep as-is; will be filled later if day/month found

    return s  # return as-is if we cannot parse


# ---------------------------------------------------------------------------
# Known label keywords in multilingual EU/international documents
# Maps any substring/keyword → canonical field name
# ---------------------------------------------------------------------------
_LABEL_KEYWORDS: dict[str, str] = {
    # ── National ID number ──────────────────────────────────────────────────────
    "id number":            "id_number",
    "id no":                "id_number",
    "id#":                  "id_number",
    "national id":          "id_number",
    "identity number":      "id_number",
    "identity card no":     "id_number",
    "isikukood":            "id_number",       # Estonian ID code
    "personal code":        "id_number",
    "identitätsnummer":     "id_number",       # German
    "numero d'identite":    "id_number",       # French
    "numero de identidad":  "id_number",       # Spanish

    # ── Permit number (document number) ────────────────────────────────────────
    "elamisluba":           "permit_number",   # Estonian: Residence Permit
    "elamisõigus":          "permit_number",   # Estonian: Right of Residence
    "loa number":           "permit_number",
    "permit number":        "permit_number",
    "permit no":            "permit_number",
    "permit#":              "permit_number",
    "document number":      "permit_number",
    "doc number":           "permit_number",
    "document no":          "permit_number",
    "izinname":             "permit_number",   # Turkish
    "nr zezwolenia":        "permit_number",   # Polish
    "numero de permis":     "permit_number",   # French
    "residence card":       "permit_number",
    "card number":          "permit_number",

    # ── Permit type ─────────────────────────────────────────────────────────────
    "loa liik":             "permit_type",     # Estonian: Type of permit
    "type of permit":       "permit_type",
    "type de permis":       "permit_type",     # French
    "art der genehmigung":  "permit_type",     # German
    "tipo de permiso":      "permit_type",     # Spanish
    "permit category":      "permit_type",
    "residence type":       "permit_type",
    "card type":            "permit_type",

    # ── Surname ─────────────────────────────────────────────────────────────────
    "perekonnanimi":        "surname",         # Estonian
    "surname":              "surname",
    "last name":            "surname",
    "family name":          "surname",
    "nom":                  "surname",         # French
    "apellido":             "surname",         # Spanish
    "nachname":             "surname",         # German
    "uzvārds":              "surname",         # Latvian
    "pavardė":              "surname",         # Lithuanian
    "příjmení":             "surname",         # Czech
    "priezvisko":           "surname",         # Slovak
    "prezime":              "surname",         # Croatian/Serbian
    "cognome":              "surname",         # Italian

    # ── Given name ──────────────────────────────────────────────────────────────
    "eesnimi":              "given_name",      # Estonian
    "forename":             "given_name",
    "first name":           "given_name",
    "given name":           "given_name",
    "given names":          "given_name",
    "prénom":               "given_name",      # French
    "nombre":               "given_name",      # Spanish
    "vorname":              "given_name",      # German
    "vārds":                "given_name",      # Latvian
    "vardas":               "given_name",      # Lithuanian
    "křestní jméno":        "given_name",      # Czech
    "meno":                 "given_name",      # Slovak
    "ime":                  "given_name",      # Croatian/Serbian
    "nome":                 "given_name",      # Italian

    # ── Nationality / Citizenship ────────────────────────────────────────────────
    "kodakondsus":          "nationality",     # Estonian
    "citizenship":          "nationality",
    "nationality":          "nationality",
    "nationalité":          "nationality",     # French
    "nationalidad":         "nationality",     # Spanish
    "staatsangehörigkeit":  "nationality",     # German
    "pilsonība":            "nationality",     # Latvian
    "pilietybė":            "nationality",     # Lithuanian
    "obywatelstwo":         "nationality",     # Polish
    "cittadinanza":         "nationality",     # Italian

    # ── Date of birth ────────────────────────────────────────────────────────────
    "sunniaeg":             "date_of_birth",   # Estonian: Date of birth
    "sünniaeg":             "date_of_birth",   # Estonian (accented)
    "date of birth":        "date_of_birth",
    "dob":                  "date_of_birth",
    "birth date":           "date_of_birth",
    "date de naissance":    "date_of_birth",   # French
    "fecha de nacimiento":  "date_of_birth",   # Spanish
    "geburtsdatum":         "date_of_birth",   # German
    "dzimšanas datums":     "date_of_birth",   # Latvian
    "gimimo data":          "date_of_birth",   # Lithuanian
    "data urodzenia":       "date_of_birth",   # Polish
    "data nascita":         "date_of_birth",   # Italian

    # ── Date of expiry / Valid until ─────────────────────────────────────────────
    "kehtiv kuni":          "date_of_expiry",  # Estonian: Valid until
    "card expiry":          "date_of_expiry",
    "date of expiry":       "date_of_expiry",
    "expiry date":          "date_of_expiry",
    "expiration date":      "date_of_expiry",
    "valid until":          "date_of_expiry",
    "valid thru":           "date_of_expiry",
    "date d'expiration":    "date_of_expiry",  # French
    "fecha de vencimiento": "date_of_expiry",  # Spanish
    "ablaufdatum":          "date_of_expiry",  # German
    "derīguma termiņš":     "date_of_expiry",  # Latvian
    "galiojimo data":       "date_of_expiry",  # Lithuanian

    # ── Date of issue ─────────────────────────────────────────────────────────────
    "date of issue":        "date_of_issue",
    "issued":               "date_of_issue",
    "issue date":           "date_of_issue",
    "väljastamise kuupäev": "date_of_issue",   # Estonian
    "date de délivrance":   "date_of_issue",   # French
    "ausstellungsdatum":    "date_of_issue",   # German
    "izsniegšanas datums":  "date_of_issue",   # Latvian

    # ── Gender / Sex ──────────────────────────────────────────────────────────────
    "sugu":                 "gender",          # Estonian
    "sex":                  "gender",
    "gender":               "gender",
    "sexe":                 "gender",          # French
    "geschlecht":           "gender",          # German
    "dzimums":              "gender",          # Latvian
    "lytis":                "gender",          # Lithuanian
    "płeć":                 "gender",          # Polish

    # ── Issuing country ───────────────────────────────────────────────────────────
    "issuing country":      "issuing_country",
    "country":              "issuing_country",
    "country code":         "issuing_country",
    "est":                  "issuing_country",  # Estonia code on document

    # ── Address ───────────────────────────────────────────────────────────────────
    "aadress":              "address",         # Estonian
    "address":              "address",
    "adresse":              "address",         # French/German
    "adres":                "address",         # Polish/Dutch
}

# Permit number patterns — match across any country format
_PERMIT_NUM_PATTERNS = [
    r"^[A-Z]{1,3}\d{6,10}$",      # PS98765432, AAB123456
    r"^[A-Z]\d{8}$",               # UK-style permits
    r"^\d{9,12}$",                  # Numeric-only permits
    r"^[A-Z]{2}\d{3}[A-Z]{2}\d{3}$",  # Mixed
]

# Known label-like strings to skip as data values
_LABEL_NOISE: set[str] = {
    "REMARKS", "MARKUSED", "ELAMISLUBA", "RESIDENCE PERMIT",
    "LOA LIIK", "TYPE OF PERMIT", "LONG TERM RESIDENT", "PIKAAJALINE ELANIK",
    "EU", "EC", "TOOTADA LUBATUD", "LUBATUD", "0\"",
    "REPUBLIC OF ESTONIA", "ESTONIA", "IDENTITY CARD", "ID CARD",
    "NATIONAL IDENTITY CARD", "DRIVING LICENCE", "DRIVER LICENSE",
    "PASSPORT", "VISA", "REPUBLIC OF INDIA", "GOVERNMENT OF INDIA",
    "UNITED STATES OF AMERICA", "EU PASSPORT", "RESIDENT CARD",
}


def _is_label_noise(text: str) -> bool:
    """Return True if the text is a field label/header rather than a value."""
    u = text.strip().upper()
    if u in _LABEL_NOISE:
        return True
    for kw in _LABEL_KEYWORDS:
        if kw in u.lower():
            return True
    return False


def _looks_like_permit_number(text: str) -> bool:
    """Return True if text matches a known permit/residence card number pattern."""
    t = text.strip().upper().replace(" ", "")
    for pat in _PERMIT_NUM_PATTERNS:
        if re.match(pat, t):
            return True
    return False


def _is_name_token(text: str) -> bool:
    """
    Return True if text looks like a personal name token (all caps alpha, 2–30 chars,
    no digits, not a known country code or label keyword).
    """
    t = text.strip()
    if not re.match(r"^[A-Z][A-Z\-\' ]{1,29}$", t):
        return False
    if t.upper() in _LABEL_NOISE:
        return False
    # Skip known 3-letter country codes
    if len(t) == 3 and t.upper() in _ALPHA3_TO_ALPHA2:
        return False
    # Skip short noise tokens
    if t.upper() in ("EU", "EC", "UN", "ID", "OK"):
        return False
    return True


def _parse_layout_agnostic_fields(
    raw_fields: dict[str, Any],
) -> dict[str, Any]:
    """
    Fix the inverted key-value problem produced by generic_document_ocr.py.

    The layout-agnostic OCR heuristic often treats actual data values (names, IDs)
    as field keys, and actual labels as values.  This function:

    1.  Scans the fields dict for keys that are LABEL keywords  → extracts value
    2.  Scans the fields dict for keys that ARE data values     → extracts key as data
    3.  Parses _unpaired_text sequentially to fill remaining gaps
    4.  Reassembles a clean, canonical fields dict
    """
    out: dict[str, Any] = {}

    # ── Phase 1: Interpret the flat fields dict ──────────────────────────────
    # Walk each key-value pair; determine whether the KEY is a label or a data value
    for raw_key, raw_val in raw_fields.items():
        if raw_key == "_unpaired_text":
            continue

        key_u = raw_key.strip().upper()
        key_l = raw_key.strip().lower()
        val_s = _clean_str(raw_val)

        # --- Check if this key is a known label keyword ---
        matched_field = None
        for kw, field in _LABEL_KEYWORDS.items():
            if kw in key_l:
                matched_field = field
                break

        if matched_field and val_s:
            # The value is the actual document data
            if matched_field not in out:
                out[matched_field] = val_s
            continue

        # --- Key is NOT a known label; check if the KEY IS a data value ---
        # Case: key looks like a permit number → it IS the permit number
        if _looks_like_permit_number(key_u) and matched_field is None:
            if "permit_number" not in out:
                out["permit_number"] = key_u
            continue

        # Case: key is a name token (value is label noise) → key is the data
        if _is_name_token(raw_key) and val_s and _is_label_noise(val_s):
            # We don't know yet if this is surname or given_name; collect as candidates
            if "_name_candidates" not in out:
                out["_name_candidates"] = []
            out["_name_candidates"].append(raw_key.strip())
            continue

        # Case: key is purely numeric (e.g. "07") → likely a date fragment
        if re.match(r"^\d{1,4}$", raw_key.strip()):
            if "_date_fragments" not in out:
                out["_date_fragments"] = []
            out["_date_fragments"].append((raw_key.strip(), val_s or ""))
            continue

        # Default: try to map via FIELD_MAP (handled later), store as-is
        if val_s is not None:
            out[key_l] = val_s

    # ── Phase 2: Parse _unpaired_text sequentially ───────────────────────────
    unpaired: list[str] = raw_fields.get("_unpaired_text") or []

    # Build a flat uppercase token list for sequential scanning
    tokens = [t.strip() for t in unpaired if t.strip()]

    i = 0
    surname_seen = False
    given_name_seen = False

    while i < len(tokens):
        tok = tokens[i]
        tok_u = tok.upper()
        tok_l = tok.lower()

        # Combined surname+forename label → next two tokens are surname + forename
        if any(x in tok_u for x in ("PEREKONNANIMI", "SURNAME FORENAME", "SURNAME GIVEN", "NOM PRENOM", "APELLIDO NOMBRE", "NACHNAME VORNAME")):
            j = i + 1
            while j < len(tokens) and _is_label_noise(tokens[j]):
                j += 1
            if j < len(tokens) and _is_name_token(tokens[j]):
                out.setdefault("surname", tokens[j])
                surname_seen = True
                j += 1
            while j < len(tokens) and _is_label_noise(tokens[j]):
                j += 1
            if j < len(tokens) and _is_name_token(tokens[j]):
                out.setdefault("given_name", tokens[j])
                given_name_seen = True
            i = max(i + 1, j)
            continue

        # Check if this token is a label keyword
        matched_label = None
        for kw, field in _LABEL_KEYWORDS.items():
            if kw in tok_l:
                matched_label = field
                break

        if matched_label:
            # Consume next non-label token as the value
            j = i + 1
            while j < len(tokens) and _is_label_noise(tokens[j]):
                j += 1
            if j < len(tokens) and matched_label not in out:
                candidate = tokens[j].strip()
                if matched_label in ("permit_number", "id_number"):
                    out[matched_label] = candidate
                elif matched_label == "nationality":
                    if len(candidate) in (2, 3) and candidate.upper() not in ("EU", "EC", "UN"):
                        out["nationality"] = candidate
                elif matched_label == "gender":
                    cand_u = candidate.upper()
                    if cand_u in ("M", "F", "N", "X"):
                        out["gender"] = cand_u
                    else:
                        k = j
                        while k < len(tokens):
                            t_u = tokens[k].upper()
                            if t_u in ("M", "F", "N", "X"):
                                out["gender"] = t_u
                                break
                            if any(kw in t_u.lower() for kw in _LABEL_KEYWORDS):
                                break
                            k += 1
                elif matched_label == "date_of_expiry" and re.search(r"\d{4}", candidate):
                    out["date_of_expiry"] = candidate
                elif matched_label == "date_of_birth" and re.search(r"\d{4}", candidate):
                    out["date_of_birth"] = candidate
                elif matched_label in ("surname", "given_name", "permit_type", "address"):
                    out[matched_label] = candidate
            i += 1
            continue

        # Nationality code (3-letter country code isolated in unpaired text)
        # Only accept if previous context was NOT a gender label
        if (re.match(r"^[A-Z]{3}$", tok_u)
                and tok_u in _ALPHA3_TO_ALPHA2
                and tok_u not in ("EST",)   # EST is issuing country, not nationality
                and "nationality" not in out):
            out["nationality"] = tok_u
            i += 1
            continue

        # Issuing country code (2-letter) — EST doc → EE
        # MUST NOT capture EU, EC, UN, or other noise tokens
        _SKIP_2LETTER = {"EU", "EC", "UN", "ID", "OK", "PC", "DC"}
        if (re.match(r"^[A-Z]{2}$", tok_u)
                and tok_u not in _SKIP_2LETTER
                and tok_u in {v for v in _ALPHA3_TO_ALPHA2.values()}
                and "issuing_country" not in out):
            out.setdefault("issuing_country", tok_u)
            i += 1
            continue

        # Gender token (standalone N, M, F, etc.) — check BEFORE name-token handler
        if tok_u in ("M", "F", "N", "X") and "gender" not in out:
            out["gender"] = tok_u
            i += 1
            continue
        # Patterns like "N / F" or "M / H"
        if re.match(r"^[NMFXnmfx]\s*/\s*[MFHKmfhk]$", tok):
            out.setdefault("gender", tok_u)
            i += 1
            continue

        # Permit type values (Estonian/Nordic)
        if tok_u in ("PIKAAJALINE", "LONG") and "permit_type" not in out:
            # Collect adjacent permit type tokens
            type_parts = [tok_u]
            j = i + 1
            while j < len(tokens) and tokens[j].upper() in (
                "ELANIK", "RESIDENT", "TERM", "EU", "EC",
                "PIKAAJALINE", "LONG", "TEMPORARY",
            ):
                type_parts.append(tokens[j].upper())
                j += 1
            out["permit_type"] = " ".join(type_parts)
            i = j
            continue

        # Date fragments: isolated day/month/year numbers
        if re.match(r"^\d{4}$", tok):
            if "date_of_expiry" not in out:
                out.setdefault("_expiry_year", tok)
            elif "date_of_birth" not in out:
                out.setdefault("_birth_year", tok)
            i += 1
            continue

        if re.match(r"^\d{2}$", tok):
            # Could be day or month; collect for later reconstruction
            if "_date_nums" not in out:
                out["_date_nums"] = []
            out["_date_nums"].append(tok)
            i += 1
            continue

        # ALL-CAPS name token not yet assigned
        if _is_name_token(tok_u):
            if "surname" not in out and not surname_seen:
                out["surname"] = tok
                surname_seen = True
            elif "given_name" not in out and not given_name_seen:
                out["given_name"] = tok
                given_name_seen = True
            elif "_name_candidates" not in out:
                out.setdefault("_name_candidates", []).append(tok)
        else:
            # Titlecase / mixed-case name (e.g. "Sharma" from fields dict)
            if re.match(r"^[A-Z][a-z]+$", tok) and "surname" not in out:
                out["surname"] = tok.upper()
                surname_seen = True

        i += 1

    # ── Phase 3: Reconcile name candidates collected from inverted keys ──────
    # Only fill fields that Phase 2 did NOT already populate
    name_candidates: list[str] = out.pop("_name_candidates", []) or []
    for cand in name_candidates:
        cu = cand.upper()
        # Skip if value is already authoritative from Phase 2 unpaired-text parsing
        if "surname" not in out:
            out["surname"] = cu
        elif "given_name" not in out and cu != out.get("surname", "").upper():
            out["given_name"] = cu

    # ── Phase 4: Reconstruct date_of_birth from fragments ────────────────────
    # Fragments collected: _date_nums = ["14", "07"], _birth_year from dict "07":"1995"
    date_fragments_raw = out.pop("_date_fragments", [])  # [(key, value), ...]
    date_nums = out.pop("_date_nums", [])
    expiry_year = out.pop("_expiry_year", None)
    birth_year = out.pop("_birth_year", None)

    # From the raw fields dict fragment pairs like {"07": "1995"}
    for frag_key, frag_val in date_fragments_raw:
        # The VALUE is likely the year (4 digits)
        if re.match(r"^\d{4}$", frag_val):
            # The KEY is a month or day
            if "date_of_birth" not in out and not birth_year:
                birth_year = frag_val
                date_nums.append(frag_key)

    if birth_year and date_nums and "date_of_birth" not in out:
        # We may have ["14", "07"] for day/month, plus year from fragments
        nums_sorted = sorted(date_nums, key=lambda x: int(x))
        if len(nums_sorted) >= 2:
            day_candidate = nums_sorted[0]   # smaller = day (1-31)
            month_candidate = nums_sorted[1] # larger = month? Not always; use position
            # For the Estonian card: "14" "07" in order → day=14, month=07
            ordered = [n for n in date_nums]  # preserve order
            dd = ordered[0] if len(ordered) > 0 else "01"
            mm = ordered[1] if len(ordered) > 1 else "01"
            out["date_of_birth"] = f"{birth_year}-{int(mm):02d}-{int(dd):02d}"

    # Expiry: year from fields dict ("KEHTIV KUNI / CARD EXPIRY": "2029")
    # and day/month may be in unpaired ("06", "20")
    cur_exp = str(out.get("date_of_expiry") or "")
    if expiry_year or (cur_exp and len(cur_exp) == 4):
        exp_y = expiry_year or cur_exp
        remaining_nums = [
            n for n in date_nums
            if "date_of_birth" not in out or n not in out.get("date_of_birth", "").split("-")
        ]
        if len(remaining_nums) >= 2:
            n1, n2 = int(remaining_nums[0]), int(remaining_nums[1])
            if n1 > 12 and n2 <= 12:
                day, month = n1, n2
            elif n2 > 12 and n1 <= 12:
                day, month = n2, n1
            else:
                day, month = int(remaining_nums[0]), int(remaining_nums[1])
            out["date_of_expiry"] = f"{exp_y}-{month:02d}-{day:02d}"
        elif exp_y:
            out["date_of_expiry"] = exp_y

    # If only expiry year in the main fields dict value
    if "date_of_expiry" not in out:
        for fk, fv in raw_fields.items():
            if "kehtiv" in fk.lower() or "expiry" in fk.lower() or "valid" in fk.lower():
                if fv and re.search(r"\d{4}", str(fv)):
                    out["date_of_expiry"] = _clean_str(fv)
                    break

    return out


class OCROutputAdapter:
    """
    Adapts raw dict output from Module 1 OCR wrappers into standardized fields.

    Supports international document variants across all 195+ UN member states,
    handling MRZ-derived fields (ICAO 9303 TD1/TD2/TD3), visual OCR field names
    from Indian, EU, GCC, ASEAN, LATAM, and African document formats.

    Includes special handling for layout-agnostic OCR output where field labels
    and values are frequently swapped (e.g., Estonian residence permits).
    """

    # --------------------------------------------------------------------------
    # Comprehensive field name mapping → canonical schema column name
    # Covers: English labels, French, Spanish, German, Arabic transliterations,
    #         common abbreviations, and EasyOCR/Tesseract output variations.
    # --------------------------------------------------------------------------
    FIELD_MAP: dict[str, str] = {
        # ── Name ───────────────────────────────────────────────────────────────
        "name":                  "name",
        "full_name":             "name",
        "fullname":              "name",
        "holder_name":           "name",
        "card_holder":           "name",
        "cardholder":            "name",
        "card_holder_name":      "name",
        "nom":                   "name",
        "nombre":                "name",
        "nome":                  "name",
        "isim":                  "name",
        "naam":                  "name",
        "name_on_card":          "name",
        "applicant_name":        "name",
        "permit_holder":         "name",

        # ── Surname / Given name ───────────────────────────────────────────────
        "surname":               "surname",
        "last_name":             "surname",
        "family_name":           "surname",
        "nom_de_famille":        "surname",
        "apellido":              "surname",
        "cognome":               "surname",
        "nachname":              "surname",
        "given_name":            "given_name",
        "first_name":            "given_name",
        "prenom":                "given_name",
        "nombre_propio":         "given_name",
        "vorname":               "given_name",
        "names":                 "given_name",

        # ── Gender / Sex ───────────────────────────────────────────────────────
        "sex":                   "gender",
        "gender":                "gender",
        "sexe":                  "gender",
        "sexo":                  "gender",
        "geschlecht":            "gender",
        "cinsiyet":              "gender",
        "sugu":                  "gender",

        # ── Date of birth ──────────────────────────────────────────────────────
        "date_of_birth":         "date_of_birth",
        "dob":                   "date_of_birth",
        "birth_date":            "date_of_birth",
        "birthdate":             "date_of_birth",
        "date_de_naissance":     "date_of_birth",
        "fecha_de_nacimiento":   "date_of_birth",
        "data_nascita":          "date_of_birth",
        "geburtsdatum":          "date_of_birth",
        "geboortedatum":         "date_of_birth",
        "dogum_tarihi":          "date_of_birth",
        "birth":                 "date_of_birth",
        "sunniaeg":              "date_of_birth",

        # ── Date of issue ──────────────────────────────────────────────────────
        "date_of_issue":         "date_of_issue",
        "issue_date":            "date_of_issue",
        "issued_date":           "date_of_issue",
        "issued_on":             "date_of_issue",
        "date_issued":           "date_of_issue",
        "date_of_issuance":      "date_of_issue",
        "date_delivrance":       "date_of_issue",
        "fecha_de_emision":      "date_of_issue",
        "ausstellungsdatum":     "date_of_issue",

        # ── Date of expiry ─────────────────────────────────────────────────────
        "date_of_expiry":        "date_of_expiry",
        "expiry_date":           "date_of_expiry",
        "expiration_date":       "date_of_expiry",
        "valid_until":           "date_of_expiry",
        "valid_thru":            "date_of_expiry",
        "validity":              "date_of_expiry",
        "expires":               "date_of_expiry",
        "expiry":                "date_of_expiry",
        "date_expiry":           "date_of_expiry",
        "date_of_expiration":    "date_of_expiry",
        "date_dexpiration":      "date_of_expiry",
        "fecha_vencimiento":     "date_of_expiry",
        "verfallsdatum":         "date_of_expiry",
        "son_kullanma_tarihi":   "date_of_expiry",
        "kehtiv_kuni":           "date_of_expiry",
        "card_expiry":           "date_of_expiry",

        # ── Nationality ────────────────────────────────────────────────────────
        "nationality":           "nationality",
        "nationalite":           "nationality",
        "nationalidad":          "nationality",
        "nationalität":          "nationality",
        "nazionalita":           "nationality",
        "nationaliteit":         "nationality",
        "milliyet":              "nationality",
        "citizen":               "nationality",
        "citizenship":           "nationality",
        "country_of_citizenship":"nationality",
        "kodakondsus":           "nationality",

        # ── Issuing country ────────────────────────────────────────────────────
        "issuing_country":       "issuing_country",
        "country_code":          "issuing_country",
        "country":               "issuing_country",
        "issued_by":             "issuing_country",
        "country_of_issue":      "issuing_country",
        "issuingcountry":        "issuing_country",

        # ── Issuing authority ──────────────────────────────────────────────────
        "issuing_authority":     "issuing_authority",
        "issuing_office":        "issuing_authority",
        "issued_by_authority":   "issuing_authority",
        "authority":             "issuing_authority",
        "issued_at":             "issuing_authority",
        "place_of_issue":        "issuing_authority",
        "issuing_post":          "issuing_post",
        "post":                  "issuing_post",

        # ── Passport fields ────────────────────────────────────────────────────
        "passport_number":       "passport_number",
        "passport_no":           "passport_number",
        "passport_num":          "passport_number",
        "document_number":       "passport_number",
        "doc_number":            "passport_number",
        "personal_number":       "personal_number",
        "personal_no":           "personal_number",
        "optional_field":        "personal_number",
        "passport_type":         "passport_type",
        "document_type":         "passport_type",
        "type":                  "passport_type",
        "mrz_type":              "passport_type",
        "place_of_birth":        "place_of_birth",
        "birth_place":           "place_of_birth",
        "lieu_de_naissance":     "place_of_birth",

        # ── Aadhaar fields ─────────────────────────────────────────────────────
        "aadhaar_number":        "aadhaar_number",
        "aadhaar_no":            "aadhaar_number",
        "uid_number":            "aadhaar_number",
        "uid":                   "aadhaar_number",
        "masked_number":         "masked_number",
        "masked_aadhaar":        "masked_number",

        # ── Visa fields ────────────────────────────────────────────────────────
        "visa_number":           "visa_number",
        "visa_no":               "visa_number",
        "folio_number":          "visa_number",
        "sticker_number":        "visa_number",
        "control_number":        "control_number",
        "visa_type":             "visa_type",
        "category":              "visa_type",
        "class":                 "visa_type",
        "entries":               "entries",
        "number_of_entries":     "entries",
        "annotation":            "annotation",
        "remarks":               "annotation",

        # ── Driving License fields ─────────────────────────────────────────────
        "license_number":        "license_number",
        "licence_number":        "license_number",
        "dl_number":             "license_number",
        "driving_licence_no":    "license_number",
        "license_no":            "license_number",
        "licence_no":            "license_number",
        "dl_no":                 "license_number",
        "blood_group":           "blood_group",
        "blood_type":            "blood_group",
        "blood":                 "blood_group",
        "relation":              "relation",
        "s_w_d_of":              "relation",
        "address":               "address",
        "vehicle_classes":       "vehicle_classes",
        "vehicle_categories":    "vehicle_classes",
        "categories":            "vehicle_classes",

        # ── National ID fields ─────────────────────────────────────────────────
        "id_number":             "id_number",
        "id_no":                 "id_number",
        "national_id":           "id_number",
        "national_id_number":    "id_number",
        "national_id_no":        "id_number",
        "identity_number":       "id_number",
        "cin":                   "id_number",
        "nic":                   "id_number",
        "tc_kimlik_no":          "id_number",
        "curp":                  "id_number",
        "nid":                   "id_number",
        "fin":                   "id_number",
        "nric":                  "id_number",
        "pesel":                 "id_number",
        "nin":                   "id_number",
        "hin":                   "id_number",
        "pan":                   "id_number",
        "voter_id":              "id_number",
        "epic":                  "id_number",
        "emirates_id":           "id_number",
        "iqama_number":          "id_number",

        # ── Permit fields ──────────────────────────────────────────────────────
        "permit_number":         "permit_number",
        "permit_no":             "permit_number",
        "permit_type":           "permit_type",
        "permit_category":       "permit_type",
        "work_permit_number":    "permit_number",
        "residence_permit_no":   "permit_number",
        "pass_number":           "permit_number",
        "pass_no":               "permit_number",
        "elamisluba":            "permit_number",   # Estonian
        "loa_liik":              "permit_type",     # Estonian
    }

    # Document types that use the layout-agnostic OCR and need the special parser
    _LAYOUT_AGNOSTIC_DOC_TYPES = {"permit", "national_id", "generic", "unknown"}

    @classmethod
    def adapt(cls, raw_ocr_result: dict[str, Any] | None, doc_type_override: str | None = None) -> dict[str, Any]:
        """
        Takes raw output dict from Module 1 OCR wrapper and returns a normalized dictionary.
        """
        if not isinstance(raw_ocr_result, dict):
            raw_ocr_result = {}

        raw_doc_type = str(raw_ocr_result.get("document_type") or "unknown").lower().replace(" ", "_")
        doc_type = str(doc_type_override or raw_doc_type).lower().replace(" ", "_")

        raw_conf = raw_ocr_result.get("ocr_confidence")
        try:
            ocr_confidence = float(raw_conf) if raw_conf is not None else 0.0
        except (ValueError, TypeError):
            ocr_confidence = 0.0

        status = str(raw_ocr_result.get("status") or "UNKNOWN")
        reason = str(raw_ocr_result.get("reason") or "")

        raw_fields = raw_ocr_result.get("fields")
        if not isinstance(raw_fields, dict):
            raw_fields = {}

        normalized_fields: dict[str, Any] = {}

        # ── Step 1: Handle nested Visa wrapper structure ──────────────────────
        if "extracted" in raw_fields and isinstance(raw_fields["extracted"], dict):
            for k, v in raw_fields["extracted"].items():
                val = _clean_str(v)
                if val is not None:
                    std_key = cls.FIELD_MAP.get(k.lower(), k.lower())
                    normalized_fields[std_key] = val

        # ── Step 2: Merge MRZ fields ──────────────────────────────────────────
        if "mrz" in raw_fields and isinstance(raw_fields["mrz"], dict):
            mrz_data = raw_fields["mrz"]
            if mrz_data.get("raw_line1"):
                normalized_fields["mrz_line1"] = mrz_data["raw_line1"]
            if mrz_data.get("raw_line2"):
                normalized_fields["mrz_line2"] = mrz_data["raw_line2"]
            if mrz_data.get("raw_line3"):
                normalized_fields["mrz_line3"] = mrz_data["raw_line3"]

            for k, v in mrz_data.items():
                if k in ("raw_line1", "raw_line2", "raw_line3", "valid"):
                    continue
                val = _clean_str(v)
                if val:
                    std_key = cls.FIELD_MAP.get(k.lower(), k.lower())
                    if std_key not in normalized_fields:
                        normalized_fields[std_key] = val

        # ── Step 3: Layout-agnostic document special handling ─────────────────
        # For permits/national IDs, the generic OCR often inverts keys and values
        has_unpaired = bool(raw_fields.get("_unpaired_text"))
        is_layout_agnostic = (
            doc_type in cls._LAYOUT_AGNOSTIC_DOC_TYPES or
            has_unpaired
        )

        if is_layout_agnostic and (has_unpaired or raw_fields):
            la_fields = _parse_layout_agnostic_fields(raw_fields)
            # Merge: layout-agnostic parser takes priority for permit docs
            for k, v in la_fields.items():
                if k.startswith("_"):
                    continue
                std_key = cls.FIELD_MAP.get(k.lower(), k.lower())
                if std_key not in normalized_fields:
                    normalized_fields[std_key] = v

        # ── Step 4: Top-level flat fields (standard wrappers) ────────────────
        _skip_keys = {
            "extracted", "mrz", "checks", "matches",
            "close_matches", "mismatches", "_unpaired_text",
        }
        for k, v in raw_fields.items():
            if k in _skip_keys:
                continue
            val = _clean_str(v)
            if val is not None:
                std_key = cls.FIELD_MAP.get(k.lower(), k.lower())
                # Only fill gaps — never overwrite what layout-agnostic parser found
                if std_key not in normalized_fields:
                    normalized_fields[std_key] = val

        # ── Step 5: Aadhaar — pull top-level aadhaar/masked fields ───────────
        if doc_type == "aadhaar":
            for k in ("masked_number", "aadhaar_number", "uid_number"):
                if k in raw_ocr_result and k not in normalized_fields:
                    val = _clean_str(raw_ocr_result[k])
                    if val:
                        std_key = cls.FIELD_MAP.get(k, k)
                        normalized_fields[std_key] = val

        # ── Step 6: Reconstruct full name from parts ──────────────────────────
        surname    = _clean_str(normalized_fields.get("surname")) or ""
        given_name = _clean_str(normalized_fields.get("given_name")) or ""
        cur_name   = _clean_str(normalized_fields.get("name")) or ""

        if cur_name and surname and not given_name and surname.upper() != cur_name.upper():
            given_name = cur_name

        if given_name or surname:
            normalized_fields["name"] = f"{given_name} {surname}".strip()
        elif cur_name:
            normalized_fields["name"] = cur_name

        # ── Step 7: Normalise gender ──────────────────────────────────────────
        if "gender" in normalized_fields:
            normalized_fields["gender"] = _normalise_gender(normalized_fields["gender"])

        # ── Step 8: Normalise dates ───────────────────────────────────────────
        for date_field in ("date_of_birth", "date_of_issue", "date_of_expiry"):
            if date_field in normalized_fields:
                normalized_fields[date_field] = _normalise_date(normalized_fields[date_field])

        # ── Step 9: Country determination (ISO 3166-1 alpha-2) ───────────────
        country_raw = (
            normalized_fields.get("issuing_country") or
            normalized_fields.get("country") or
            normalized_fields.get("nationality")
        )
        if not country_raw and doc_type in ("aadhaar",):
            country_raw = "IN"
        if not country_raw and doc_type == "driving_license":
            lic = _clean_str(normalized_fields.get("license_number")) or ""
            if re.match(r"^[A-Z]{2}\d{2}", lic):
                country_raw = "IN"
        if country_raw:
            country_raw = _normalize_country(country_raw)

        if "nationality" in normalized_fields:
            normalized_fields["nationality"] = (
                _normalize_country(normalized_fields["nationality"])
                or normalized_fields["nationality"]
            )
        if "issuing_country" in normalized_fields:
            normalized_fields["issuing_country"] = (
                _normalize_country(normalized_fields["issuing_country"])
                or normalized_fields["issuing_country"]
            )

        # ── Step 10: Filter to Canonical Fields ONLY ──────────────────────────
        CANONICAL_FIELDS = {
            "name", "surname", "given_name", "date_of_birth", "date_of_issue",
            "date_of_expiry", "gender", "nationality", "issuing_country",
            "issuing_authority", "issuing_post", "passport_number", "personal_number",
            "passport_type", "place_of_birth", "aadhaar_number", "masked_number",
            "visa_number", "control_number", "visa_type", "entries", "annotation",
            "license_number", "blood_group", "relation", "address", "vehicle_classes",
            "id_number", "permit_number", "permit_type", "mrz_line1", "mrz_line2", "mrz_line3"
        }

        clean_fields = {
            k: v for k, v in normalized_fields.items()
            if k in CANONICAL_FIELDS and v is not None and str(v).strip() != ""
        }

        return {
            "document_type":    doc_type,
            "document_country": country_raw,
            "ocr_confidence":   ocr_confidence,
            "fields":           clean_fields,
            "raw_ocr":          raw_ocr_result,
            "status":           status,
            "reason":           reason,
        }
