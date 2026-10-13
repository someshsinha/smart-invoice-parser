import pytest
from app.parsing.amounts import parse_money_amount, is_percentage_token
from app.pipeline import process_invoice_pdf
from tests.test_reader import create_simple_test_pdf


def test_amount_parser_locales():
    # US / UK
    assert parse_money_amount("361.60") == 361.60
    assert parse_money_amount("1,234.56") == 1234.56
    assert parse_money_amount("GBP 433.92") == 433.92
    assert parse_money_amount("$ 242.17") == 242.17

    # German (dot thousands, comma decimal)
    assert parse_money_amount("1.200,00", decimal_separator_hint=",") == 1200.00
    assert parse_money_amount("1.428,00 €", decimal_separator_hint=",") == 1428.00

    # Indian Lakh grouping
    assert parse_money_amount("1,23,456.00") == 123456.00

    # JPY integer
    assert parse_money_amount("12000") == 12000.00

    # Percentages must return None
    assert parse_money_amount("20%") is None
    assert parse_money_amount("7.25%") is None
    assert is_percentage_token("VAT 20%") is True


def test_northwind_amounts_exact():
    # Appendix N Example 1
    from pathlib import Path
    pdf_bytes = (Path("samples") / "northwind_1042.pdf").read_bytes()
    response, _ = process_invoice_pdf(pdf_bytes)

    assert response.vendor == "Northwind Traders"
    assert response.subtotal == 361.60
    assert response.tax == 72.32
    assert response.total == 433.92
    assert response.confidence.subtotal >= 0.95
    assert response.confidence.tax >= 0.95
    assert response.confidence.total >= 0.95


def test_kestrel_amounts_exact_and_table_header_trap():
    # Appendix N Example 2
    from pathlib import Path
    pdf_bytes = (Path("samples") / "kestrel_0311.pdf").read_bytes()
    response, _ = process_invoice_pdf(pdf_bytes)

    assert response.vendor == "Kestrel Components"
    assert response.subtotal == 225.80
    assert response.tax == 16.37
    assert response.total == 242.17
    # Trapping check: "Total" column header was NOT chosen as the total
    assert response.total != 145.00


def test_rule_o2_arithmetic_mismatch_never_corrects_numbers():
    # Subtotal 100.00 + Tax 20.00 != Total 115.00
    pdf = create_simple_test_pdf([
        "NORTHWIND TRADERS LTD",
        "Invoice No: NW-999",
        "Subtotal: 100.00",
        "VAT: 20.00",
        "Amount Due: GBP 115.00"
    ])
    response, _ = process_invoice_pdf(pdf)

    # Returns printed values exactly without altering arithmetic
    assert response.subtotal == 100.00
    assert response.tax == 20.00
    assert response.total == 115.00

    # Warning must be emitted
    assert any("Subtotal plus tax does not equal total (100.00 + 20.00 != 115.00)" in w for w in response.warnings)
    # Confidence must be capped per spec
    assert response.confidence.total <= 0.60


def test_german_meridian_amounts():
    from pathlib import Path
    pdf_bytes = (Path("samples") / "meridian_german.pdf").read_bytes()
    response, _ = process_invoice_pdf(pdf_bytes)

    assert response.vendor == "Meridian Industrial"
    assert response.subtotal == 1200.00
    assert response.tax == 228.00
    assert response.total == 1428.00


def test_multi_tax_components_sum():
    pdf = create_simple_test_pdf([
        "Pinecrest Packaging Pvt Ltd",
        "Subtotal: 1000.00",
        "CGST 9%: 90.00",
        "SGST 9%: 90.00",
        "Total: 1180.00"
    ])
    response, _ = process_invoice_pdf(pdf)

    assert response.subtotal == 1000.00
    assert response.tax == 180.00  # 90 + 90
    assert response.total == 1180.00
