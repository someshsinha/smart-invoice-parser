"""
F13: Confidence Model & Calibration.
Calculates explainable, calibrated confidence scores in [0.0, 0.99] for each extracted invoice field.
Enforces that null fields always receive 0.0, while supported fields reflect evidence strength.
"""

from typing import Dict, Any, Optional
from app.schemas import FieldConfidence


def compute_field_confidence(
    field_name: str,
    value: Any,
    label_exact: bool = True,
    is_ambiguous: bool = False,
    arithmetic_valid: Optional[bool] = None,
    is_derived_terms: bool = False,
    is_fallback_vendor_cur: bool = False,
    is_scanned_or_null: bool = False,
) -> float:
    """
    Computes calibrated confidence for a single field based on evidence strength.
    Rule: A null or unextracted field always receives 0.0 confidence.
    """
    if value is None or is_scanned_or_null:
        return 0.0

    # Base confidences per field
    base_scores = {
        "vendor": 0.95,
        "invoice_number": 0.95,
        "invoice_date": 0.92,
        "due_date": 0.90,
        "currency": 0.95,
        "subtotal": 0.92,
        "tax": 0.92,
        "total": 0.95,
    }
    score = base_scores.get(field_name, 0.90)

    # 1. Vendor specific factors
    if field_name == "vendor":
        if value == "unknown":
            return 0.20
        # If brand only match (warning emitted)
        if not label_exact:
            score = 0.85

    # 2. Date specific factors
    if field_name in ("invoice_date", "due_date"):
        if is_ambiguous:
            score = 0.80
        elif is_derived_terms and field_name == "due_date":
            score = 0.85

    # 3. Currency specific factors (Rule O3)
    if field_name == "currency":
        if is_fallback_vendor_cur:
            return 0.50

    # 4. Amount specific factors (Rule O2)
    if field_name in ("subtotal", "tax", "total"):
        if arithmetic_valid is True:
            # Triple satisfies subtotal + tax == total
            score = 0.97
        elif arithmetic_valid is False:
            # Triple failed arithmetic check -> cap at 0.60 per PRD
            score = 0.60

    # Label similarity penalty
    if not label_exact and field_name != "vendor":
        score *= 0.90

    # Clip confidence to [0.0, 0.99]
    return max(0.0, min(0.99, round(score, 2)))


def calibrate_confidences(
    vendor: str,
    invoice_number: Optional[str],
    invoice_date: Optional[str],
    due_date: Optional[str],
    currency: Optional[str],
    subtotal: Optional[float],
    tax: Optional[float],
    total: Optional[float],
    warnings: list,
    has_text: bool = True,
) -> FieldConfidence:
    """
    Constructs a calibrated FieldConfidence object for all 8 fields based on extracted values and warnings.
    """
    if not has_text:
        return FieldConfidence()

    # Vendor evidence
    vendor_exact = not any("brand name only" in w.lower() for w in warnings)
    vendor_conf = compute_field_confidence("vendor", vendor, label_exact=vendor_exact)

    # Invoice number evidence
    inv_num_conf = compute_field_confidence("invoice_number", invoice_number)

    # Dates evidence
    inv_date_ambiguous = any("read as" in w.lower() and "vendor" in w.lower() for w in warnings)
    inv_date_conf = compute_field_confidence(
        "invoice_date", invoice_date, is_ambiguous=inv_date_ambiguous
    )

    due_derived = any("derived from terms" in w.lower() for w in warnings)
    due_conf = compute_field_confidence(
        "due_date", due_date, is_derived_terms=due_derived
    )

    # Currency evidence (Rule O3)
    cur_fallback = any("assumed" in w.lower() and "from vendor" in w.lower() for w in warnings)
    cur_conf = compute_field_confidence(
        "currency", currency, is_fallback_vendor_cur=cur_fallback
    )

    # Amounts evidence (Rule O2)
    arithmetic_failed = any("does not equal total" in w.lower() for w in warnings)
    all_amounts_present = subtotal is not None and tax is not None and total is not None
    arithmetic_valid = (all_amounts_present and not arithmetic_failed) if all_amounts_present else None
    if arithmetic_failed:
        arithmetic_valid = False

    sub_conf = compute_field_confidence(
        "subtotal", subtotal, arithmetic_valid=arithmetic_valid
    )
    tax_conf = compute_field_confidence(
        "tax", tax, arithmetic_valid=arithmetic_valid
    )
    tot_conf = compute_field_confidence(
        "total", total, arithmetic_valid=arithmetic_valid
    )

    return FieldConfidence(
        vendor=vendor_conf,
        invoice_number=inv_num_conf,
        invoice_date=inv_date_conf,
        due_date=due_conf,
        currency=cur_conf,
        subtotal=sub_conf,
        tax=tax_conf,
        total=tot_conf,
    )
