from pathlib import Path
import json
import pytest
from app.reader.pdf_text import extract_document_text

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


def test_generated_samples_exist_and_have_text():
    sample_names = ["northwind_1042", "kestrel_0311", "unknown_vendor", "meridian_german"]

    for name in sample_names:
        pdf_path = SAMPLES_DIR / f"{name}.pdf"
        json_path = SAMPLES_DIR / f"{name}.json"

        assert pdf_path.exists(), f"Missing PDF for {name}"
        assert json_path.exists(), f"Missing JSON for {name}"

        # Check ground truth JSON validity
        gt_data = json.loads(json_path.read_text())
        assert "vendor" in gt_data
        assert "invoice_number" in gt_data
        assert "invoice_date" in gt_data
        assert "total" in gt_data

        # Check text layer extraction
        parsed = extract_document_text(pdf_path.read_bytes())
        assert parsed.has_text is True
        assert len(parsed.pages) >= 1
        assert len(parsed.full_text) > 50


def test_appendix_n_northwind_text_content():
    pdf_path = SAMPLES_DIR / "northwind_1042.pdf"
    parsed = extract_document_text(pdf_path.read_bytes())
    full_text = parsed.full_text

    # Check key text elements from Appendix N
    assert "NORTHWIND TRADERS LTD" in full_text
    assert "NW-1042" in full_text
    assert "03/09/2026" in full_text
    assert "03/10/2026" in full_text
    assert "Bruviti Services Pvt Ltd" in full_text
    assert "361.60" in full_text
    assert "72.32" in full_text
    assert "433.92" in full_text


def test_appendix_n_kestrel_text_content():
    pdf_path = SAMPLES_DIR / "kestrel_0311.pdf"
    parsed = extract_document_text(pdf_path.read_bytes())
    full_text = parsed.full_text

    # Check key text elements from Appendix N
    assert "Kestrel Components Inc." in full_text
    assert "KC-0311" in full_text
    assert "9/3/26" in full_text
    assert "Net 30" in full_text
    assert "225.80" in full_text
    assert "16.37" in full_text
    assert "242.17" in full_text
