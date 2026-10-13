import pytest
import fitz
from app.reader.pdf_text import extract_document_text
from app.reader.normalize import normalize_text
from app.pipeline import process_invoice_pdf


def create_simple_test_pdf(text_lines):
    doc = fitz.open()
    page = doc.new_page()
    y = 50.0
    for line in text_lines:
        page.insert_text((50.0, y), line, fontsize=11)
        y += 20.0
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_text_normalization():
    assert normalize_text("Hello   World") == "Hello World"
    # Full-width digits and characters (NFKC)
    assert normalize_text("１２３４") == "1234"
    # Unify various dashes/minus
    assert normalize_text("Invoice—No: 10–20") == "Invoice-No: 10-20"
    # Non-breaking spaces
    assert normalize_text("Total:\u00a0100.00") == "Total: 100.00"


def test_extract_document_text_basic():
    pdf_bytes = create_simple_test_pdf([
        "NORTHWIND TRADERS LTD",
        "Invoice No: NW-1042       Invoice Date: 03/09/2026",
        "Amount Due GBP 433.92"
    ])

    parsed = extract_document_text(pdf_bytes)
    assert parsed.has_text is True
    assert len(parsed.pages) == 1
    assert "NORTHWIND TRADERS" in parsed.full_text

    # Verify line clustering and cell splitting on line 2
    line2 = parsed.pages[0].lines[1]
    assert len(line2.cells) >= 2
    cell_texts = [c.text for c in line2.cells]
    assert any("NW-1042" in c for c in cell_texts)
    assert any("03/09/2026" in c for c in cell_texts)


def test_scanned_pdf_without_text_layer():
    # Create empty PDF page with no text
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    parsed = extract_document_text(pdf_bytes)
    assert parsed.has_text is False

    response, _ = process_invoice_pdf(pdf_bytes)
    assert response.vendor == "unknown"
    assert response.invoice_number is None
    assert response.total is None
    assert "No text layer found; scanned documents are out of scope." in response.warnings


def test_corrupt_pdf_raises_value_error():
    with pytest.raises(ValueError, match="Corrupt or unreadable PDF"):
        extract_document_text(b"%PDF-corrupted-bytes-data")
