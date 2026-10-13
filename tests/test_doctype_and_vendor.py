import pytest
import fitz
from app.extract.doctype import classify_document_type
from app.extract.vendor import resolve_vendor
from app.pipeline import process_invoice_pdf
from tests.test_reader import create_simple_test_pdf


def test_doctype_rule_o4_quotation():
    pdf = create_simple_test_pdf([
        "NORTHWIND TRADERS LTD",
        "QUOTATION # Q-1029",
        "Bill to: Bruviti Services Pvt Ltd",
        "Total Amount: GBP 500.00"
    ])
    response, _ = process_invoice_pdf(pdf)
    assert response.vendor == "Northwind Traders"
    assert response.invoice_number is None
    assert response.total is None
    assert response.confidence.total == 0.0
    assert any("quotation" in w.lower() for w in response.warnings)


def test_doctype_rule_o4_delivery_note():
    pdf = create_simple_test_pdf([
        "Kestrel Components Inc.",
        "DELIVERY NOTE",
        "Packing slip no: DN-8812",
        "Sold to: Bruviti Services Pvt Ltd"
    ])
    response, _ = process_invoice_pdf(pdf)
    assert response.vendor == "Kestrel Components"
    assert response.invoice_number is None
    assert any("delivery note" in w.lower() for w in response.warnings)


def test_doctype_body_mention_does_not_flip_invoice():
    # A real invoice mentioning "Delivery note: 1042" in the reference body should remain an invoice
    pdf = create_simple_test_pdf([
        "NORTHWIND TRADERS LTD",
        "TAX INVOICE",
        "Invoice No: NW-1042",
        "Delivery note ref: DN-990",
        "Total: GBP 433.92"
    ])
    response, _ = process_invoice_pdf(pdf)
    assert response.vendor == "Northwind Traders"
    # Should not be classified as a delivery note
    assert not any("delivery note" in w.lower() for w in response.warnings)


def test_vendor_canonical_resolutions():
    vendors = [
        ("NORTHWIND TRADERS LTD", "Northwind Traders"),
        ("Blue Harbor Logistics Inc", "Blue Harbour Logistics"),  # American spelling + Inc
        ("Kestrel Components Inc. | 880 Industrial Pkwy", "Kestrel Components"),
        ("Meridian Industrial GmbH", "Meridian Industrial"),
        ("Sakura Precision KK", "Sakura Precision"),
        ("Pinecrest Packaging Pvt Ltd", "Pinecrest Packaging"),
    ]
    for header, expected in vendors:
        pdf = create_simple_test_pdf([header, "Invoice No: 1234", "Bill to: Bruviti Services Pvt Ltd"])
        response, _ = process_invoice_pdf(pdf)
        assert response.vendor == expected, f"Failed for header: {header}"


def test_vendor_brand_only():
    pdf = create_simple_test_pdf([
        "NORTHWIND LTD",
        "Invoice No: NW-1042",
        "Bill to: Bruviti Services Pvt Ltd"
    ])
    response, _ = process_invoice_pdf(pdf)
    assert response.vendor == "Northwind Traders"
    assert any("brand name only" in w.lower() for w in response.warnings)


def test_vendor_decoys_unknown():
    # Decoy 1: Same generic word, different brand
    pdf1 = create_simple_test_pdf([
        "Pinewood Packaging Ltd",
        "Invoice No: 8812",
        "Bill to: Bruviti Services Pvt Ltd"
    ])
    res1, _ = process_invoice_pdf(pdf1)
    assert res1.vendor == "unknown"

    # Decoy 2: Same brand token, conflicting generic word
    pdf2 = create_simple_test_pdf([
        "Northwind Logistics Ltd",
        "Invoice No: 9912",
        "Bill to: Bruviti Services Pvt Ltd"
    ])
    res2, _ = process_invoice_pdf(pdf2)
    assert res2.vendor == "unknown"
    assert any("resembles" in w.lower() for w in res2.warnings)


def test_customer_bruviti_never_selected_as_vendor():
    pdf = create_simple_test_pdf([
        "Bill To: Bruviti Services Pvt Ltd",
        "Invoice No: 100",
        "Amount: 200"
    ])
    res, _ = process_invoice_pdf(pdf)
    assert res.vendor == "unknown"
    assert res.vendor != "Bruviti Services Pvt Ltd"
