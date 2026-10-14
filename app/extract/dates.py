"""
F10: Invoice Date, Due Date, and Payment Terms Extractor (Rule O1).
Extracts dates, converts payment terms (e.g. Net 30), disambiguates ambiguous dates,
and enforces Rule O1 precedence and warnings.
"""

from typing import Tuple, Optional, List
import re
from datetime import date, timedelta
from app.reader.pdf_text import ParsedDocument
from app.knowledge.vendors import CANONICAL_VENDORS
from app.knowledge.locales import infer_locale_from_document
from app.knowledge.labels import LABELS
from app.parsing.dates import parse_date_string
from app.parsing.terms import parse_payment_terms
from app.extract.warnings import (
    warn_terms_due_date,
    warn_conflicting_due_date,
    warn_no_due_date_or_terms,
)

EXCLUDE_DATE_PATTERNS = [
    r"\border\s*date\b", r"\bdelivery\s*date\b", r"\bship\s*date\b",
    r"\bshipped\b", r"\bdate\s*of\s*supply\b", r"\btax\s*point\b", r"\bpo\s*date\b"
]


def extract_dates(
    doc: ParsedDocument,
    vendor_name: str,
) -> Tuple[Optional[str], float, Optional[str], float, List[str]]:
    """
    Extracts invoice_date and due_date, evaluating payment terms (Rule O1).
    Returns:
        (invoice_date_iso, inv_date_conf, due_date_iso, due_date_conf, warnings)
    """
    if not doc.pages or not doc.has_text:
        return None, 0.0, None, 0.0, []

    # Get vendor locale metadata (or infer from document if unknown/unregistered vendor)
    vendor_meta = CANONICAL_VENDORS.get(vendor_name)
    if vendor_meta:
        date_order = vendor_meta.get("date_order", "DMY")
        country = vendor_meta.get("country", "United Kingdom")
    else:
        country, date_order = infer_locale_from_document(doc)

    warnings: List[str] = []

    printed_inv_date: Optional[str] = None
    inv_date_conf = 0.0
    printed_due_date: Optional[str] = None
    due_date_conf = 0.0
    found_terms_days: Optional[int] = None
    found_terms_str: Optional[str] = None

    # Scan lines for date and terms candidates
    for page in doc.pages:
        for line in page.lines:
            line_text = line.text
            line_lower = line_text.lower()

            # Skip distractor date lines (order date, ship date, etc.)
            if any(re.search(pat, line_lower) for pat in EXCLUDE_DATE_PATTERNS):
                continue

            # 1. Check for payment terms (e.g. Terms Net 30, Zahlungsziel 14 Tage)
            terms_res = parse_payment_terms(line_text)
            if terms_res and found_terms_days is None:
                found_terms_days, found_terms_str = terms_res

            # 2. Check each cell or segment for labels and values
            for cell in line.cells:
                cell_text = cell.text
                cell_lower = cell_text.lower()

                # A. Due date check
                if printed_due_date is None and any(re.search(rf"\b{lbl}\b", cell_lower) for lbl in LABELS["due_date"]):
                    # Look for date string in this cell or neighboring cells
                    d_iso, d_warn = _extract_date_from_cell_or_line(cell_text, line_text, date_order, country)
                    if d_iso:
                        printed_due_date = d_iso
                        # Standard day-first dates from known canonical day-first vendors are not ambiguous anomalies
                        suppress_standard_warn = bool(vendor_meta and date_order == "DMY" and d_warn and "day-first" in d_warn)
                        effective_warn = None if suppress_standard_warn else d_warn
                        due_date_conf = 0.80 if effective_warn else 0.90
                        if effective_warn:
                            warnings.append(effective_warn)

                # B. Invoice date check
                if printed_inv_date is None and any(re.search(rf"\b{lbl}\b", cell_lower) for lbl in LABELS["invoice_date"]):
                    d_iso, d_warn = _extract_date_from_cell_or_line(cell_text, line_text, date_order, country)
                    if d_iso:
                        printed_inv_date = d_iso
                        suppress_standard_warn = bool(vendor_meta and date_order == "DMY" and d_warn and "day-first" in d_warn)
                        effective_warn = None if suppress_standard_warn else d_warn
                        inv_date_conf = 0.80 if effective_warn else 0.90
                        if effective_warn:
                            warnings.append(effective_warn)

    # Fallback scan: if invoice date not found by label, look for dates in header region of page 1
    if printed_inv_date is None and doc.pages:
        for line in doc.pages[0].lines[:10]:
            if any(re.search(pat, line.text.lower()) for pat in EXCLUDE_DATE_PATTERNS):
                continue
            d_iso, d_warn = parse_date_string(line.text, date_order, country)
            if d_iso:
                printed_inv_date = d_iso
                suppress_standard_warn = bool(vendor_meta and date_order == "DMY" and d_warn and "day-first" in d_warn)
                effective_warn = None if suppress_standard_warn else d_warn
                inv_date_conf = 0.70 if effective_warn else 0.85
                if effective_warn:
                    warnings.append(effective_warn)
                break

    # Resolve Due Date with Payment Terms (Rule O1)
    final_due_date: Optional[str] = None
    final_due_conf = 0.0

    derived_due_date: Optional[str] = None
    if found_terms_days is not None and printed_inv_date is not None:
        try:
            base_dt = date.fromisoformat(printed_inv_date)
            calc_dt = base_dt + timedelta(days=found_terms_days)
            derived_due_date = calc_dt.isoformat()
        except Exception:
            pass

    if printed_due_date is not None and derived_due_date is not None:
        # Both printed date and terms are present
        if printed_due_date == derived_due_date:
            final_due_date = printed_due_date
            final_due_conf = due_date_conf
        else:
            # Rule O1: Disagreement -> use printed date and warn
            final_due_date = printed_due_date
            final_due_conf = due_date_conf
            warnings.append(
                warn_conflicting_due_date(printed_due_date, found_terms_str, derived_due_date)
            )
    elif printed_due_date is not None:
        final_due_date = printed_due_date
        final_due_conf = due_date_conf
    elif derived_due_date is not None:
        # Derived from terms only (Rule O1 & Example 2)
        final_due_date = derived_due_date
        final_due_conf = 0.85
        warnings.append(warn_terms_due_date(found_terms_str))
    else:
        # Neither found (Example 3)
        final_due_date = None
        final_due_conf = 0.0
        warnings.append(warn_no_due_date_or_terms())

    return printed_inv_date, inv_date_conf, final_due_date, final_due_conf, warnings


def _extract_date_from_cell_or_line(
    cell_text: str, line_text: str, date_order: str, country: str
) -> Tuple[Optional[str], Optional[str]]:
    """Tries parsing date from cell text; if cell only has label, tries from entire line."""
    d_iso, d_warn = parse_date_string(cell_text, date_order, country)
    if d_iso:
        return d_iso, d_warn
    return parse_date_string(line_text, date_order, country)
