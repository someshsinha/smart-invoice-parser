"""
Country and locale mapping rules.
"""

COUNTRY_LOCALES = {
    "United Kingdom": {"date_order": "DMY", "currency": "GBP", "decimal": "."},
    "United States": {"date_order": "MDY", "currency": "USD", "decimal": "."},
    "Germany": {"date_order": "DMY", "currency": "EUR", "decimal": ","},
    "Japan": {"date_order": "DMY", "currency": "JPY", "decimal": None},
    "India": {"date_order": "DMY", "currency": "INR", "decimal": "."},
}

import re
from typing import Tuple
from app.reader.pdf_text import ParsedDocument

CUSTOMER_EXCLUSIONS = [
    r"\bbruviti\b", r"\bbill\s*to\b", r"\bsold\s*to\b", r"\bship\s*to\b", r"\bcustomer\b"
]

US_PATTERNS = [
    r"\b(usa|united states|u\.s\.a\.|u\.s\.)\b",
    r"\b(texas|tx|california|ca|new york|ny|florida|fl|ohio|oh|washington|wa|illinois|il)\b",
]

UK_PATTERNS = [
    r"\b(united kingdom|u\.k\.|great britain|england|scotland|wales)\b",
    r"\b[A-Za-z]{1,2}\d[A-Za-z\d]?\s*\d[A-Za-z]{2}\b",
]

DE_PATTERNS = [
    r"\b(germany|deutschland|stuttgart|berlin|münchen|munich|frankfurt|hamburg)\b",
]

IN_PATTERNS = [
    r"\b(india|bharat|bengaluru|bangalore|mumbai|delhi|hyderabad|chennai)\b",
    r"\bgstin\b",
]

JP_PATTERNS = [
    r"\b(japan|nippon|tokyo|osaka|kyoto|chiyoda)\b",
]


def infer_locale_from_document(doc: ParsedDocument) -> Tuple[str, str]:
    """
    Infers (country, date_order) from document content when the vendor is unknown.
    Inspects supplier header lines, skipping customer blocks and Bruviti lines.
    Falls back to printed currency and finally default UK/DMY.
    """
    if not doc.pages or not doc.has_text:
        return "United Kingdom", "DMY"

    page1 = doc.pages[0]
    supplier_lines = []
    in_customer_block = False

    for line in page1.lines[:12]:
        text_lower = line.text.lower()
        if any(re.search(pat, text_lower) for pat in CUSTOMER_EXCLUSIONS):
            in_customer_block = True
            continue
        if in_customer_block:
            continue
        supplier_lines.append(text_lower)

    combined_header = "   ".join(supplier_lines)

    # 1. Address / Country text in supplier header
    if any(re.search(pat, combined_header) for pat in US_PATTERNS):
        return "United States", "MDY"
    if any(re.search(pat, combined_header) for pat in UK_PATTERNS):
        return "United Kingdom", "DMY"
    if any(re.search(pat, combined_header) for pat in DE_PATTERNS):
        return "Germany", "DMY"
    if any(re.search(pat, combined_header) for pat in IN_PATTERNS):
        return "India", "DMY"
    if any(re.search(pat, combined_header) for pat in JP_PATTERNS):
        return "Japan", "DMY"

    # 2. Check printed currency in the full text of page 1
    page1_text = " ".join(line.text for line in page1.lines)
    if re.search(r"\bUSD\b|\$", page1_text):
        return "United States", "MDY"
    if re.search(r"\bGBP\b|£", page1_text):
        return "United Kingdom", "DMY"
    if re.search(r"\bEUR\b|€", page1_text):
        return "Germany", "DMY"
    if re.search(r"\bINR\b|₹|\bRs\.?\b", page1_text):
        return "India", "DMY"
    if re.search(r"\bJPY\b|¥|円", page1_text):
        return "Japan", "DMY"

    # 3. Default fallback
    return "United Kingdom", "DMY"

