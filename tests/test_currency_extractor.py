import pytest
from app.extract.currency import extract_currency
from app.pipeline import process_invoice_pdf
from tests.test_reader import create_simple_test_pdf


def test_currency_iso_codes():
    codes = [("GBP", "GBP"), ("USD", "USD"), ("EUR", "EUR"), ("JPY", "JPY"), ("INR", "INR")]
    for code_text, expected in codes:
        pdf = create_simple_test_pdf([
            "Apex Supplies",
            f"Total Amount: {code_text} 500.00"
        ])
        response, _ = process_invoice_pdf(pdf)
        assert response.currency == expected


def test_currency_symbols():
    symbols = [
        ("£ 100.00", "GBP"),
        ("$ 250.00", "USD"),
        ("120.00 €", "EUR"),
        ("¥ 5000", "JPY"),
        ("₹ 1500.00", "INR"),
        ("Rs. 1500.00", "INR"),
    ]
    for sym_line, expected in symbols:
        pdf = create_simple_test_pdf([
            "Apex Supplies",
            f"Balance Due: {sym_line}"
        ])
        response, _ = process_invoice_pdf(pdf)
        assert response.currency == expected


def test_rule_o3_no_currency_printed_falls_back_to_vendor():
    # Invoice has no £ or GBP anywhere
    pdf = create_simple_test_pdf([
        "NORTHWIND TRADERS LTD",
        "Invoice No: NW-100",
        "Subtotal: 100.00",
        "VAT: 20.00",
        "Total: 120.00"
    ])
    response, _ = process_invoice_pdf(pdf)

    # Should fall back to vendor's currency (GBP)
    assert response.currency == "GBP"
    # Should lower confidence to 0.50
    assert response.confidence.currency == 0.50
    # Must add warning per Rule O3
    assert any("No currency printed; assumed GBP from vendor" in w for w in response.warnings)


def test_printed_currency_differs_from_vendor_default():
    # UK vendor Northwind billing in USD
    pdf = create_simple_test_pdf([
        "NORTHWIND TRADERS LTD",
        "Invoice No: NW-101",
        "Amount Due: USD 500.00"
    ])
    response, _ = process_invoice_pdf(pdf)

    # Printed currency wins!
    assert response.currency == "USD"
    # Adds mismatch warning
    assert any("Printed currency USD differs from vendor default GBP" in w for w in response.warnings)
