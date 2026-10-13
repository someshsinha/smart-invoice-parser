import pytest
from app.extract.candidates import (
    find_label_matches_in_text,
    extract_field_candidates,
    GeometricCandidate,
)
from app.reader.pdf_text import extract_document_text
from tests.test_reader import create_simple_test_pdf


def test_find_label_matches():
    lexicon = ["invoice no", "reference #", "date"]
    # Exact match
    matches = find_label_matches_in_text("Invoice No: NW-1042", lexicon)
    assert len(matches) >= 1
    assert matches[0][0] == "invoice no"
    assert matches[0][3] == 1.0

    # Fuzzy match with minor typo (e.g. Invoce No)
    fuzzy_matches = find_label_matches_in_text("Invoce No: NW-1042", lexicon)
    assert len(fuzzy_matches) >= 1
    assert fuzzy_matches[0][0] == "invoice no"
    assert 0.88 <= fuzzy_matches[0][3] <= 1.0


def test_candidates_same_line_and_right_cell():
    pdf = create_simple_test_pdf([
        "Invoice No: NW-1042       Invoice Date: 03/09/2026",
        "Total: 433.92"
    ])
    doc = extract_document_text(pdf)

    # Candidates for invoice_number
    num_cands = extract_field_candidates(doc, "invoice_number", ["invoice no", "inv no"])
    assert len(num_cands) >= 1
    assert any("NW-1042" in c.value_text for c in num_cands)
    assert any(c.relation in ("same_line", "right_cell") for c in num_cands)

    # Candidates for total
    tot_cands = extract_field_candidates(doc, "total", ["total"])
    assert len(tot_cands) >= 1
    assert any("433.92" in c.value_text for c in tot_cands)


def test_candidates_label_above_value():
    # Table layout: labels on row 1, values on row 2 underneath
    pdf = create_simple_test_pdf([
        "Invoice No     Date           Total",
        "MI-8821        12.09.2026     1428.00"
    ])
    doc = extract_document_text(pdf)

    cands = extract_field_candidates(doc, "invoice_number", ["invoice no"])
    assert len(cands) >= 1
    # Check that below_row relation was detected
    assert any(c.relation == "below_row" for c in cands)
    assert any("MI-8821" in c.value_text for c in cands)


def test_candidates_exclusions():
    pdf = create_simple_test_pdf([
        "Purchase Order: PO-9988",
        "Invoice No: NW-1042"
    ])
    doc = extract_document_text(pdf)

    # If excluding PO lines
    cands = extract_field_candidates(
        doc,
        "invoice_number",
        ["invoice no", "po"],
        exclude_labels=["purchase order"]
    )
    # PO line should be excluded
    assert not any("PO-9988" in c.value_text for c in cands)
    assert any("NW-1042" in c.value_text for c in cands)
