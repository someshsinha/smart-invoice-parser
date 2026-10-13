"""
F3: Document-Type Classifier (Rule O4).
Identifies non-invoice documents (quotations, delivery notes, account statements, purchase orders, credit notes).
Rule O4: Returns every field null, vendor as found, and a warning describing what it is.
"""

from typing import Tuple, Optional
import re
from app.reader.pdf_text import ParsedDocument
from app.extract.warnings import warn_non_invoice_doctype

# Non-invoice document type keywords (Title zone)
NON_INVOICE_TYPES = {
    "quotation": [
        r"\bquotation\b", r"\bquote\b", r"\bestimate\b", r"\bproforma\b",
        r"\bangebot\b", r"\bkostenvoranschlag\b", r"見積"
    ],
    "delivery note": [
        r"\bdelivery note\b", r"\bpacking slip\b", r"\bdispatch note\b",
        r"\bgoods received\b", r"\blieferschein\b", r"納品書"
    ],
    "statement": [
        r"\bstatement of account\b", r"\baccount statement\b",
        r"\bbank statement\b", r"\bkontoauszug\b", r"\bstatement\b"
    ],
    "purchase order": [
        r"\bpurchase order\b", r"\border confirmation\b", r"\bbestellung\b", r"発注書"
    ],
    "credit note": [
        r"\bcredit note\b", r"\bcredit memo\b", r"\bgutschrift\b"
    ],
}

INVOICE_TITLE_PATTERNS = [
    r"\btax invoice\b", r"\binvoice\b", r"\brechnung\b", r"請求書"
]


def classify_document_type(doc: ParsedDocument) -> Tuple[bool, str, Optional[str]]:
    """
    Evaluates whether the document is an invoice or a non-invoice document.
    Returns:
        (is_invoice: bool, detected_kind: str, warning_message: Optional[str])
    """
    if not doc.pages or not doc.has_text:
        return True, "invoice", None

    first_page = doc.pages[0]
    page_height = first_page.height

    # Collect title zone lines: top 35% of page or lines with large font
    median_font_size = 10.0
    all_font_sizes = [w.font_size for line in first_page.lines for w in line.words]
    if all_font_sizes:
        all_font_sizes.sort()
        median_font_size = all_font_sizes[len(all_font_sizes) // 2]

    title_lines = []
    for line in first_page.lines:
        is_top_region = line.y0 <= (page_height * 0.35)
        is_large_font = line.font_size >= (median_font_size * 1.25)
        if is_top_region or is_large_font:
            title_lines.append(line.text.lower())

    title_zone_text = "   ".join(title_lines)

    # Check for explicit invoice indicators in the title zone
    has_invoice_title = any(re.search(pat, title_zone_text) for pat in INVOICE_TITLE_PATTERNS)

    # Check for competing non-invoice keywords in the title zone
    for doc_type, patterns in NON_INVOICE_TYPES.items():
        for pat in patterns:
            if re.search(pat, title_zone_text):
                # If document explicitly states "INVOICE" or "TAX INVOICE", it is an invoice unless the primary title is a non-invoice
                if has_invoice_title:
                    # An invoice mentioning a quote/po/delivery note reference in the title zone is still an invoice
                    is_reference = bool(
                        re.search(r"\b(delivery note|statement|quote|quotation|po|order)\s*(no|num|#|ref|reference|dated|date)\b", title_zone_text)
                    )
                    if is_reference:
                        continue
                    # If invoice title exists and this is not a reference, invoice still wins unless non-invoice is the sole large title
                    continue

                return False, doc_type, warn_non_invoice_doctype(doc_type)

    return True, "invoice", None

