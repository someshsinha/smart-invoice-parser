import pytest
from app.extract.confidence import compute_field_confidence, calibrate_confidences
from app.extract.warnings import (
    warn_ambiguous_date,
    warn_terms_due_date,
    warn_conflicting_due_date,
    warn_arithmetic_mismatch,
    warn_no_currency,
    warn_currency_mismatch,
    warn_unknown_vendor,
    warn_brand_only_vendor,
    warn_vendor_resembles,
    warn_no_due_date_or_terms,
    warn_non_invoice_doctype,
    warn_no_text_layer,
    warn_multiple_invoice_numbers,
    warn_field_extraction_failed,
)
from app.pipeline import process_invoice_pdf
from tests.test_reader import create_simple_test_pdf


def test_confidence_null_is_always_zero():
    for f in ["vendor", "invoice_number", "invoice_date", "due_date", "currency", "subtotal", "tax", "total"]:
        assert compute_field_confidence(f, None) == 0.0


def test_confidence_rules():
    # Clean matches
    assert compute_field_confidence("vendor", "Northwind Traders") >= 0.95
    assert compute_field_confidence("invoice_number", "NW-1042") >= 0.95

    # Unknown vendor
    assert compute_field_confidence("vendor", "unknown") == 0.20

    # Ambiguous date
    assert compute_field_confidence("invoice_date", "2026-09-03", is_ambiguous=True) == 0.80

    # Due date from terms
    assert compute_field_confidence("due_date", "2026-10-03", is_derived_terms=True) == 0.85

    # Currency fallback (Rule O3)
    assert compute_field_confidence("currency", "GBP", is_fallback_vendor_cur=True) == 0.50

    # Arithmetic check valid vs invalid (Rule O2)
    assert compute_field_confidence("total", 433.92, arithmetic_valid=True) == 0.97
    assert compute_field_confidence("total", 433.92, arithmetic_valid=False) == 0.60


def test_all_warning_templates():
    assert "Date 03/09/2026 read as day-first (UK vendor)." in warn_ambiguous_date("03/09/2026", "day", "UK")
    assert "Due date derived from terms Net 30." in warn_terms_due_date("Net 30")
    assert "differs from terms Net 30" in warn_conflicting_due_date("2026-09-15", "Net 30", "2026-10-03")
    assert "Subtotal plus tax does not equal total (100.00 + 20.00 != 115.00)." in warn_arithmetic_mismatch(100.0, 20.0, 115.0)
    assert "No currency printed; assumed GBP from vendor." in warn_no_currency("GBP")
    assert "Printed currency USD differs from vendor default GBP." in warn_currency_mismatch("USD", "GBP")
    assert "Vendor name not in the canonical list." in warn_unknown_vendor()
    assert "Vendor matched on brand name only (Northwind Traders)." in warn_brand_only_vendor("Northwind Traders")
    assert "Vendor name resembles Northwind Traders but does not match" in warn_vendor_resembles("Northwind Traders")
    assert "No due date or payment terms found." in warn_no_due_date_or_terms()
    assert "Document appears to be a quotation, not an invoice." in warn_non_invoice_doctype("quotation")
    assert "No text layer found; scanned documents are out of scope." in warn_no_text_layer()
    assert "Multiple possible invoice numbers found; chose NW-1042." in warn_multiple_invoice_numbers("NW-1042")
    assert "Could not extract total." in warn_field_extraction_failed("total")


def test_pipeline_scanned_pdf_zero_confidence():
    import pymupdf as fitz
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    res, _ = process_invoice_pdf(pdf_bytes)
    assert res.vendor == "unknown"
    for k in ["vendor", "invoice_number", "invoice_date", "due_date", "currency", "subtotal", "tax", "total"]:
        assert getattr(res.confidence, k) == 0.0
