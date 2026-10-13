"""
F9: Invoice Number Extractor.
Extracts invoice number as printed and trimmed, preserving case and punctuation,
filtering out distractor numbers (PO, order numbers, VAT/GSTIN, IBAN, account numbers).
"""

from typing import Tuple, Optional, List
import re
from app.reader.pdf_text import ParsedDocument, TextLine
from app.knowledge.labels import LABELS
from app.extract.warnings import warn_multiple_invoice_numbers

# Regex for valid invoice number value: 2-30 characters, contains at least one digit, allows hyphens, slashes, dots
INVOICE_NUM_VALUE_REGEX = r"[A-Za-z0-9][A-Za-z0-9\-/._]{1,29}"


def clean_invoice_number_value(raw: str) -> Optional[str]:
    """
    Cleans raw candidate string into trimmed invoice number value.
    Strips leading #, No, Nr, :, and trailing punctuation, while preserving casing and hyphens.
    Rejects dates (e.g. 03/09/2026) and pure currency numbers.
    """
    if not raw:
        return None

    # Strip leading noise prefixes
    cleaned = raw.strip()
    cleaned = re.sub(r"^(?:invoice|rechnung|reference)\b\s*[:#.]*\s*", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^(?:inv|ref)\b\s*[:#.]+\s*", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^(?:no|nr)\b\.?\s*[:#]?\s*", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = cleaned.lstrip("#: \t").rstrip(".,;:|")



    if not cleaned:
        return None

    # Must contain at least one digit
    if not any(ch.isdigit() for ch in cleaned):
        return None

    # Must not be a date: YYYY-MM-DD or DD/MM/YYYY or DD.MM.YYYY
    if re.fullmatch(r"\d{1,4}[./\-]\d{1,2}[./\-]\d{2,4}", cleaned):
        return None

    # Must be between 2 and 30 characters
    if len(cleaned) < 2 or len(cleaned) > 30:
        return None

    return cleaned


def extract_invoice_number(doc: ParsedDocument) -> Tuple[Optional[str], float, List[str]]:
    """
    Extracts invoice_number from document.
    Returns:
        (invoice_number: Optional[str], confidence: float, warnings: List[str])
    """
    if not doc.pages or not doc.has_text:
        return None, 0.0, []

    candidates: List[Tuple[str, float, float]] = []  # (value, score, y0)

    # Scan page 1 lines primarily
    page1 = doc.pages[0]

    for line in page1.lines:
        line_text = line.text
        line_lower = line_text.lower()

        # 1. Skip distractor lines (PO, Order No, Customer No, VAT No, Account No, IBAN, Phone)
        if any(re.search(rf"\b{pat}\b", line_lower) for pat in LABELS["exclude_invoice_number"]):
            # Unless line also explicitly has an invoice number label
            has_explicit_inv_label = any(re.search(rf"\b{lbl}\b", line_lower) for lbl in LABELS["invoice_number"])
            if not has_explicit_inv_label:
                continue

        # 2. Check each cell in the line for invoice number labels
        for i, cell in enumerate(line.cells):
            cell_lower = cell.text.lower()

            for lbl in LABELS["invoice_number"]:
                lbl_match = re.search(rf"\b{lbl}\b", cell_lower)
                if lbl_match:
                    # Look for value:
                    # Case A: Value in the same cell after the label
                    val_candidate = None
                    after_label = cell.text[lbl_match.end():].strip()
                    cleaned_val = clean_invoice_number_value(after_label)
                    if cleaned_val:
                        val_candidate = cleaned_val

                    # Case B: Value in the next cell on the same line
                    if not val_candidate and i + 1 < len(line.cells):
                        next_cell_text = line.cells[i + 1].text.strip()
                        cleaned_val = clean_invoice_number_value(next_cell_text)
                        if cleaned_val:
                            val_candidate = cleaned_val

                    # Case C: Check rest of the line
                    if not val_candidate:
                        line_after = line.text[line_lower.find(lbl) + len(lbl):].strip()
                        # Split by whitespace, take first token
                        parts = line_after.split()
                        if parts:
                            cleaned_val = clean_invoice_number_value(parts[0])
                            if cleaned_val:
                                val_candidate = cleaned_val

                    if val_candidate:
                        # Position bonus: top 35% of page is standard for invoice numbers
                        score = 0.95 if line.y0 < (page1.height * 0.35) else 0.88
                        candidates.append((val_candidate, score, line.y0))

    if not candidates:
        # Fallback: check bare title header lines like "INVOICE #1042" or "INVOICE NW-1042"
        for line in page1.lines[:8]:
            m = re.search(r"\b(?:invoice|rechnung)\s*#?\s*([A-Za-z0-9\-/_]{2,20})\b", line.text, re.IGNORECASE)
            if m:
                cleaned_val = clean_invoice_number_value(m.group(1))
                if cleaned_val:
                    candidates.append((cleaned_val, 0.75, line.y0))

    if not candidates:
        return None, 0.0, []

    # Sort by score (descending) and y0 (top of page first)
    candidates.sort(key=lambda c: (-c[1], c[2]))
    chosen_val, chosen_conf, _ = candidates[0]

    warnings = []
    # If multiple distinct candidate values found with high score
    unique_values = list({c[0] for c in candidates if c[1] >= 0.85})
    if len(unique_values) > 1:
        warnings.append(warn_multiple_invoice_numbers(chosen_val))

    return chosen_val, chosen_conf, warnings
