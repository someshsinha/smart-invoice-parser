import pytest
from app.parsing.dates import parse_date_string
from app.parsing.terms import parse_payment_terms
from app.pipeline import process_invoice_pdf
from tests.test_reader import create_simple_test_pdf


def test_date_parser_formats():
    cases = [
        ("2026-09-03", "DMY", "UK", "2026-09-03", False),
        ("2026.09.03", "DMY", "Germany", "2026-09-03", False),
        ("20260903", "DMY", "Japan", "2026-09-03", False),
        ("21/08/2026", "DMY", "India", "2026-08-21", False),
        ("3 Sep 2026", "DMY", "UK", "2026-09-03", False),
        ("3rd September 2026", "DMY", "UK", "2026-09-03", False),
        ("September 3, 2026", "MDY", "US", "2026-09-03", False),
        ("03-Sep-26", "DMY", "UK", "2026-09-03", False),
        ("3. März 2026", "DMY", "Germany", "2026-03-03", False),
        ("15.10.2026", "DMY", "Germany", "2026-10-15", False),
    ]
    for raw, order, country, expected_iso, should_warn in cases:
        iso, warn = parse_date_string(raw, order, country)
        assert iso == expected_iso, f"Failed for {raw}"
        if not should_warn:
            assert warn is None


def test_date_parser_ambiguity():
    # Ambiguous 03/09/2026: UK -> 3 September
    iso_uk, warn_uk = parse_date_string("03/09/2026", "DMY", "United Kingdom")
    assert iso_uk == "2026-09-03"
    assert "read as day-first (United Kingdom vendor)" in warn_uk

    # Ambiguous 9/3/26: US -> 3 September
    iso_us, warn_us = parse_date_string("9/3/26", "MDY", "United States")
    assert iso_us == "2026-09-03"
    assert "read as month-first (United States vendor)" in warn_us


def test_payment_terms_parser():
    assert parse_payment_terms("Net 30") == (30, "Net 30")
    assert parse_payment_terms("Terms: Net 15") == (15, "Net 15")
    assert parse_payment_terms("payable within 45 days") == (45, "within 45 days")
    assert parse_payment_terms("Zahlungsziel 14 Tage") == (14, "Zahlungsziel 14 Tage")
    assert parse_payment_terms("Due on receipt") == (0, "Due on receipt")
    # Should not match amount Net 361.60
    assert parse_payment_terms("Net 361.60") is None


def test_rule_o1_terms_only():
    # Kestrel Example 2 pattern: Dated 9/3/26, Terms Net 30
    pdf = create_simple_test_pdf([
        "Kestrel Components Inc.",
        "Reference # KC-0311 Dated 9/3/26",
        "Terms Net 30",
        "Sold to Bruviti Services Pvt Ltd"
    ])
    response, _ = process_invoice_pdf(pdf)
    assert response.vendor == "Kestrel Components"
    assert response.invoice_date == "2026-09-03"
    assert response.due_date == "2026-10-03"  # Sep 3 + 30 days
    assert any("Due date derived from terms Net 30" in w for w in response.warnings)


def test_rule_o1_printed_and_terms_agree():
    pdf = create_simple_test_pdf([
        "NORTHWIND TRADERS LTD",
        "Invoice Date: 03/09/2026",
        "Due Date: 03/10/2026",
        "Terms: Net 30",
        "Bill to: Bruviti Services Pvt Ltd"
    ])
    response, _ = process_invoice_pdf(pdf)
    assert response.invoice_date == "2026-09-03"
    assert response.due_date == "2026-10-03"
    # No conflict warning
    assert not any("differs from terms" in w for w in response.warnings)


def test_rule_o1_conflicting_due_date_and_terms():
    # Printed due date disagrees with terms: printed date must win and emit warning
    pdf = create_simple_test_pdf([
        "NORTHWIND TRADERS LTD",
        "Invoice Date: 03/09/2026",
        "Due Date: 15/09/2026",
        "Terms: Net 30",  # would be 03/10/2026
        "Bill to: Bruviti Services Pvt Ltd"
    ])
    response, _ = process_invoice_pdf(pdf)
    assert response.due_date == "2026-09-15"  # printed date wins
    assert any("differs from terms" in w for w in response.warnings)


def test_rule_o1_neither_due_date_nor_terms():
    # Example 3 pattern: No due date and no terms
    pdf = create_simple_test_pdf([
        "Invoice Date: 21/08/2026",
        "Bill to: Bruviti Services Pvt Ltd"
    ])
    response, _ = process_invoice_pdf(pdf)
    assert response.due_date is None
    assert any("No due date or payment terms found" in w for w in response.warnings)


def test_unknown_vendor_us_address_ambiguous_date():
    # Unknown vendor with explicit US address and ambiguous date 9/3/26
    pdf = create_simple_test_pdf([
        "ACME FIELD SUPPLIES",
        "Austin, Texas, USA",
        "Invoice Date: 9/3/26",
        "Terms: Net 10",
        "Bill to: Bruviti Services Pvt Ltd",
        "Total: USD 250.00"
    ])
    response, _ = process_invoice_pdf(pdf)
    assert response.vendor == "unknown"
    assert response.invoice_date == "2026-09-03"  # Month first: Sep 3
    assert response.due_date == "2026-09-13"  # Sep 3 + 10 days
    assert any("month-first" in w.lower() for w in response.warnings)


def test_official_northwind_date_warnings_empty():
    from pathlib import Path
    pdf_bytes = (Path("samples") / "northwind_1042.pdf").read_bytes()
    response, _ = process_invoice_pdf(pdf_bytes)
    assert response.vendor == "Northwind Traders"
    assert response.invoice_date == "2026-09-03"
    assert response.due_date == "2026-10-03"
    # Official Northwind sample should have no warnings
    assert response.warnings == []
    assert response.confidence.invoice_date >= 0.90
    assert response.confidence.due_date >= 0.90

