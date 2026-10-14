import pytest
from app.extract.invoice_number import clean_invoice_number_value, extract_invoice_number
from app.pipeline import process_invoice_pdf
from tests.test_reader import create_simple_test_pdf


def test_clean_invoice_number_value():
    assert clean_invoice_number_value("NW-1042") == "NW-1042"
    assert clean_invoice_number_value("#KC-0311") == "KC-0311"
    assert clean_invoice_number_value("Invoice No: 7781.") == "7781"
    assert clean_invoice_number_value("MI-8821,") == "MI-8821"

    # Rejects dates
    assert clean_invoice_number_value("03/09/2026") is None
    assert clean_invoice_number_value("2026-09-03") is None

    # Rejects pure text with no digits
    assert clean_invoice_number_value("INVOICE") is None


def test_northwind_invoice_number():
    from pathlib import Path
    pdf_bytes = (Path("samples") / "northwind_1042.pdf").read_bytes()
    response, _ = process_invoice_pdf(pdf_bytes)
    assert response.invoice_number == "NW-1042"
    assert response.confidence.invoice_number >= 0.90


def test_kestrel_invoice_number_inline():
    from pathlib import Path
    pdf_bytes = (Path("samples") / "kestrel_0311.pdf").read_bytes()
    response, _ = process_invoice_pdf(pdf_bytes)
    assert response.invoice_number == "KC-0311"
    assert response.confidence.invoice_number >= 0.90


def test_unknown_vendor_invoice_number():
    from pathlib import Path
    pdf_bytes = (Path("samples") / "unknown_vendor.pdf").read_bytes()
    response, _ = process_invoice_pdf(pdf_bytes)
    assert response.invoice_number == "7781"


def test_distractor_numbers_rejected():
    # Invoice containing PO number, VAT number, and Account number distractors
    pdf = create_simple_test_pdf([
        "NORTHWIND TRADERS LTD",
        "VAT No. GB 123 4567 89",
        "Purchase Order: PO-998877",
        "Customer Ref: CUST-4433",
        "Invoice No: INV-2026-001",
        "Total: GBP 100.00"
    ])
    response, _ = process_invoice_pdf(pdf)

    # Must pick the invoice number, not the PO, VAT, or customer number
    assert response.invoice_number == "INV-2026-001"
    assert response.invoice_number != "PO-998877"
    assert response.invoice_number != "CUST-4433"
    assert response.invoice_number != "GB 123 4567 89"


def test_invoice_id_label():
    # Fix 2: Support for "Invoice ID" label
    pdf = create_simple_test_pdf([
        "Sakura Precision KK",
        "Invoice ID: SP-90326",
        "Invoice Date: 03/09/2026",
        "Total: JPY 165000"
    ])
    response, _ = process_invoice_pdf(pdf)
    assert response.invoice_number == "SP-90326"
    assert response.confidence.invoice_number >= 0.90


def test_invoice_number_leading_punctuation_cleaning():
    # Fix 3: Strip leading label punctuation like "." from ". PP-7781"
    assert clean_invoice_number_value(". PP-7781") == "PP-7781"
    assert clean_invoice_number_value(": SP-90326") == "SP-90326"
    assert clean_invoice_number_value("Invoice ID: SP-90326") == "SP-90326"
    assert clean_invoice_number_value("MI-260903") == "MI-260903"

    pdf = create_simple_test_pdf([
        "Pinecrest Packaging Pvt Ltd",
        "Invoice No. PP-7781",
        "Invoice Date: 21/08/2026",
        "Total: INR 14160.00"
    ])
    response, _ = process_invoice_pdf(pdf)
    assert response.invoice_number == "PP-7781"

