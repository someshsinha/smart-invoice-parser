"""
F12: Currency Extractor (Rule O3).
Extracts ISO 4217 currency codes (GBP, USD, EUR, JPY, INR) and symbols (£, $, €, ¥, ₹),
prioritizes currency printed next to amounts/totals,
and enforces Rule O3 (falling back to vendor default with lowered confidence 0.5 when no currency is printed).
"""

from typing import Tuple, Optional, List
import re
from app.reader.pdf_text import ParsedDocument
from app.knowledge.vendors import CANONICAL_VENDORS
from app.knowledge.currencies import CURRENCY_SYMBOLS, VALID_CURRENCY_CODES
from app.extract.warnings import warn_no_currency, warn_currency_mismatch

# Regex for ISO codes
ISO_REGEX = r"\b(GBP|USD|EUR|JPY|INR)\b"
# Regex for symbols
SYMBOL_MAP = {
    r"£": "GBP",
    r"\$": "USD",
    r"US\$": "USD",
    r"€": "EUR",
    r"[¥￥円]": "JPY",
    r"(?:₹|Rs\.?|INR)": "INR",
}


def extract_currency(
    doc: ParsedDocument,
    vendor_name: str,
) -> Tuple[Optional[str], float, List[str]]:
    """
    Extracts the invoice currency.
    Returns:
        (currency_code: Optional[str], confidence: float, warnings: List[str])
    """
    if not doc.pages or not doc.has_text:
        return None, 0.0, []

    vendor_meta = CANONICAL_VENDORS.get(vendor_name, {})
    canonical_currency = vendor_meta.get("currency")

    warnings: List[str] = []

    # Priority 1: Check totals and amount lines (highest confidence)
    # Scan from bottom of pages upwards (where totals sit)
    totals_lines = []
    for page in doc.pages:
        for line in page.lines:
            lower = line.text.lower()
            if any(k in lower for k in ["total", "due", "balance", "amount", "subtotal", "vat", "tax", "betrag", "summe"]):
                totals_lines.append(line.text)

    # Search for ISO codes on totals lines first
    for t_line in totals_lines:
        iso_match = re.search(ISO_REGEX, t_line, flags=re.IGNORECASE)
        if iso_match:
            code = iso_match.group(1).upper()
            if canonical_currency and code != canonical_currency:
                warnings.append(warn_currency_mismatch(code, canonical_currency))
            return code, 0.95, warnings

        # Search for symbols on totals lines
        for sym_pat, mapped_code in SYMBOL_MAP.items():
            if re.search(sym_pat, t_line):
                if canonical_currency and mapped_code != canonical_currency:
                    warnings.append(warn_currency_mismatch(mapped_code, canonical_currency))
                return mapped_code, 0.95, warnings

    # Priority 2: Full document scan for ISO codes or symbols
    doc_text = doc.full_text

    # Check ISO codes anywhere
    iso_match = re.search(ISO_REGEX, doc_text, flags=re.IGNORECASE)
    if iso_match:
        code = iso_match.group(1).upper()
        if canonical_currency and code != canonical_currency:
            warnings.append(warn_currency_mismatch(code, canonical_currency))
        return code, 0.90, warnings

    # Check symbols anywhere
    for sym_pat, mapped_code in SYMBOL_MAP.items():
        if re.search(sym_pat, doc_text):
            if canonical_currency and mapped_code != canonical_currency:
                warnings.append(warn_currency_mismatch(mapped_code, canonical_currency))
            return mapped_code, 0.90, warnings

    # Priority 3: Rule O3 - No currency printed
    if canonical_currency:
        # Fall back to vendor's currency from Appendix M and lower confidence to 0.50
        warnings.append(warn_no_currency(canonical_currency))
        return canonical_currency, 0.50, warnings

    # Unknown vendor and no currency printed
    return None, 0.0, []
