"""
Focused regression and generalization tests for Bugs A, B, C, and D.
Validates underlying parsing rules with synthetic fixtures across varying labels,
vendor recognition, line items, missing fields, and distractor text.
"""

import pytest
from app.reader.pdf_text import TextLine, TextCell, TextWord, ParsedPage, ParsedDocument
from app.extract.invoice_number import extract_invoice_number, clean_invoice_number_value
from app.extract.amounts import extract_amounts
from app.pipeline import process_invoice_pdf
from app.schemas import InvoiceExtractionResponse


def create_synthetic_doc(lines_text: list[str], page_height: float = 800.0) -> ParsedDocument:
    """Helper to construct a geometric ParsedDocument from a list of text lines."""
    lines = []
    y = 50.0
    for txt in lines_text:
        words = []
        x = 50.0
        for w_str in txt.split():
            tw = TextWord(w_str, x, y, x + len(w_str) * 8.0, y + 12.0, 10.0, 0)
            words.append(tw)
            x += len(w_str) * 8.0 + 5.0
        cell = TextCell(txt, words, 50.0, y, x, y + 12.0, 10.0, 0)
        line = TextLine(txt, [cell], words, 50.0, y, x, y + 12.0, 10.0, 0)
        lines.append(line)
        y += 22.0
    page = ParsedPage(0, 600.0, page_height, lines, "\n".join(lines_text))
    return ParsedDocument([page], "\n".join(lines_text), True)


# ---------------------------------------------------------------------------
# BUG A: Invoice Number Label Generalization & Value Normalization
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "line,expected_inv_num",
    [
        ("Document Number: DOC-2026-X1", "DOC-2026-X1"),
        ("Document No.: DN-8849/B", "DN-8849/B"),
        ("Document #: D-9901", "D-9901"),
        ("Doc No: 4482-1", "4482-1"),
        ("Doc #: DC-003", "DC-003"),
        ("Belegnummer: BLG-2026-99", "BLG-2026-99"),
        ("Beleg-Nr: 7781-A", "7781-A"),
        ("Bill Number: BILL-1234", "BILL-1234"),
        ("Bill No: B-992", "B-992"),
        ("Invoice Number: BHL/2026.21-A", "BHL/2026.21-A"),
        ("Invoice No.: INV-2026.01/02", "INV-2026.01/02"),
    ],
)
def test_bug_a_alternative_document_number_labels(line, expected_inv_num):
    doc = create_synthetic_doc(["Acme Supplies Corp", line, "Date: 2026-10-14"])
    num, conf, warns = extract_invoice_number(doc)
    assert num == expected_inv_num
    assert conf >= 0.90
    assert warns == []


def test_bug_a_ignores_distractors_and_returns_null_when_unsupported():
    # Negative test: document with PO number and customer number, but no invoice/doc number
    doc = create_synthetic_doc([
        "Acme Supplies Corp",
        "Purchase Order: PO-99882",
        "Customer ID: CUST-441",
        "Phone: +1-555-0199",
        "Date: 2026-10-14",
    ])
    num, conf, warns = extract_invoice_number(doc)
    assert num is None
    assert conf == 0.0
    assert warns == []


def test_bug_a_clean_invoice_number_value_filters_currencies_and_dates():
    assert clean_invoice_number_value("CAD 1.70") is None
    assert clean_invoice_number_value("USD 80.00") is None
    assert clean_invoice_number_value("$ 300.00") is None
    assert clean_invoice_number_value("€ 750.00") is None
    assert clean_invoice_number_value("2026-10-14") is None
    assert clean_invoice_number_value("14/10/2026") is None
    assert clean_invoice_number_value("14.10.2026") is None
    # Valid IDs
    assert clean_invoice_number_value("KC-EDGE-11") == "KC-EDGE-11"
    assert clean_invoice_number_value("BHL/2026.21-A") == "BHL/2026.21-A"


# ---------------------------------------------------------------------------
# BUG B: Subtotal Extraction on Unfamiliar Vendors & Line Item Context
# ---------------------------------------------------------------------------

def test_bug_b_unknown_vendor_line_item_subtotal_extracted():
    # Unfamiliar vendor with line item "Parts $ 300.00", Tax $ 24.00, Total $ 324.00
    doc = create_synthetic_doc([
        "Acme Repair Services",
        "Invoice No: ACME-01",
        "Date: 10/14/2026",
        "Parts $ 300.00",
        "Tax $ 24.00",
        "Total $ 324.00",
    ])
    s, sc, t, tc, tot, totc, warns = extract_amounts(doc, "unknown")
    assert s == 300.0
    assert sc >= 0.90
    assert t == 24.0
    assert tc >= 0.90
    assert tot == 324.0
    assert totc >= 0.90
    assert warns == []


def test_bug_b_multiple_line_items_summed_for_subtotal():
    # Multiple line items without explicit subtotal label
    doc = create_synthetic_doc([
        "Apex Mechanical",
        "Document Number: APX-99",
        "Date: 14/10/2026",
        "Materials £ 200.00",
        "Labor £ 150.00",
        "VAT £ 70.00",
        "Total £ 420.00",
    ])
    s, sc, t, tc, tot, totc, warns = extract_amounts(doc, "unknown")
    assert s == 350.0
    assert t == 70.0
    assert tot == 420.0
    assert warns == []


def test_bug_b_explicit_subtotal_preferred_over_line_items():
    # Document with line item AND explicit subtotal: explicit subtotal should win
    doc = create_synthetic_doc([
        "Global Hardware Ltd",
        "Invoice No: GH-10",
        "Tools 120.00",
        "Hardware 80.00",
        "Subtotal 200.00",
        "Tax 20.00",
        "Total 220.00",
    ])
    s, sc, t, tc, tot, totc, warns = extract_amounts(doc, "unknown")
    assert s == 200.0
    assert sc == 0.97
    assert t == 20.0
    assert tot == 220.0


def test_bug_b_negative_unmatched_line_item_returns_null_subtotal():
    # Negative test: single line item does NOT equal subtotal + tax == total (e.g. 150 != 300)
    doc = create_synthetic_doc([
        "Unknown Garage",
        "Invoice No: UG-42",
        "Date: 10/14/2026",
        "Diagnostic fee $ 150.00",
        "Total $ 300.00",
    ])
    s, sc, t, tc, tot, totc, warns = extract_amounts(doc, "unknown")
    # Subtotal must NOT be guessed as 150.0 or 300.0
    assert s is None
    assert sc == 0.0
    assert tot == 300.0


# ---------------------------------------------------------------------------
# BUG C: Missing Tax Not Invented & Arithmetic Integrity
# ---------------------------------------------------------------------------

def test_bug_c_missing_tax_returns_null_without_mismatch_warning():
    # Invoice with Subtotal EUR 500.00 and Total EUR 500.00, no tax printed
    doc = create_synthetic_doc([
        "Meridian Industrial GmbH",
        "Invoice Number: MI-EDGE-20",
        "Invoice Date: 14.10.2026",
        "Subtotal EUR 500.00",
        "Total EUR 500.00",
    ])
    s, sc, t, tc, tot, totc, warns = extract_amounts(doc, "Meridian Industrial")
    assert s == 500.0
    assert t is None
    assert tc == 0.0
    assert tot == 500.0
    assert warns == []


def test_bug_c_header_or_body_text_containing_word_tax_does_not_invent_tax():
    # Line like "20 missing tax terms" or "Section 2 tax exemption notice"
    doc = create_synthetic_doc([
        "20 missing tax terms",
        "Meridian Industrial GmbH",
        "Invoice Number: MI-99",
        "Subtotal EUR 500.00",
        "Total EUR 500.00",
    ])
    s, sc, t, tc, tot, totc, warns = extract_amounts(doc, "Meridian Industrial")
    assert t is None
    assert s == 500.0
    assert tot == 500.0
    assert warns == []


def test_bug_c_tax_rate_without_amount_returns_null_tax():
    # Text states "VAT rate: 20%" but no tax currency amount is printed
    doc = create_synthetic_doc([
        "Northwind Traders Ltd",
        "Invoice No: NW-200",
        "Subtotal GBP 100.00",
        "Applicable VAT: 20%",
        "Total GBP 100.00",
    ])
    s, sc, t, tc, tot, totc, warns = extract_amounts(doc, "Northwind Traders")
    assert s == 100.0
    assert t is None
    assert tot == 100.0
    assert warns == []


def test_bug_c_real_arithmetic_mismatch_preserved_with_warning():
    # Real arithmetic mismatch: Subtotal 100 + Tax 8 != Total 115
    doc = create_synthetic_doc([
        "Kestrel Components Inc.",
        "Invoice No: KC-19",
        "Subtotal USD 100.00",
        "Sales Tax USD 8.00",
        "Total Due USD 115.00",
    ])
    s, sc, t, tc, tot, totc, warns = extract_amounts(doc, "Kestrel Components")
    assert s == 100.0
    assert t == 8.0
    assert tot == 115.0
    assert any("Subtotal plus tax does not equal total" in w for w in warns)


# ---------------------------------------------------------------------------
# BUG D: Multiple Invoice Number Warning Precision
# ---------------------------------------------------------------------------

def test_bug_d_unrelated_currency_note_does_not_trigger_warning():
    # Document with valid invoice number and unrelated currency conversion note
    doc = create_synthetic_doc([
        "Northwind Traders Ltd",
        "Invoice No: NW-EDGE-25",
        "Date: 14/10/2026",
        "Subtotal GBP 100.00",
        "VAT 20.00",
        "Total GBP 120.00",
        "Internal note: conversion reference CAD 1.70",
    ])
    inv, conf, warns = extract_invoice_number(doc)
    assert inv == "NW-EDGE-25"
    assert conf >= 0.90
    assert not any("Multiple possible invoice numbers" in w for w in warns)


def test_bug_d_exchange_rate_line_does_not_trigger_warning():
    # Document with exchange rate details
    doc = create_synthetic_doc([
        "Global Logistics Corp",
        "Document Number: GL-4412",
        "Date: 2026-10-14",
        "Rate: 1 USD = 0.92 EUR",
        "Total USD 500.00",
    ])
    inv, conf, warns = extract_invoice_number(doc)
    assert inv == "GL-4412"
    assert not any("Multiple possible invoice numbers" in w for w in warns)


def test_bug_d_genuine_ambiguity_triggers_warning():
    # Document with two distinct, explicitly labeled invoice numbers on page 1
    doc = create_synthetic_doc([
        "Apex Systems",
        "Invoice No: INV-1001",
        "Document Number: DOC-9902",
        "Date: 2026-10-14",
    ])
    inv, conf, warns = extract_invoice_number(doc)
    assert inv in ("INV-1001", "DOC-9902")
    assert any("Multiple possible invoice numbers" in w for w in warns)
