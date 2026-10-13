import time
import pytest
import pymupdf as fitz
from pathlib import Path
from app.pipeline import process_invoice_pdf


def create_pdf_with_stream_order(lines_with_pos: list) -> bytes:
    """
    Creates a single-page PDF with text inserted in the exact order of the list.
    lines_with_pos: list of tuples (text, x, y, font_size)
    """
    doc = fitz.open()
    page = doc.new_page(width=595.27, height=841.89)
    for text, x, y, size in lines_with_pos:
        page.insert_text(fitz.Point(x, y), text, fontsize=size)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_metamorphic_drawing_order_invariance():
    """
    Metamorphic Test: Changing the drawing order of PDF text stream operators
    must NOT affect the reading order or extraction result.
    """
    elements = [
        ("NORTHWIND TRADERS LTD", 50.0, 50.0, 14.0),
        ("TAX INVOICE", 450.0, 50.0, 14.0),
        ("Invoice No: NW-1042", 50.0, 90.0, 10.0),
        ("Invoice Date: 12/03/2026", 50.0, 110.0, 10.0),
        ("Subtotal: GBP 361.60", 400.0, 300.0, 10.0),
        ("Tax: GBP 72.32", 400.0, 320.0, 10.0),
        ("Total: GBP 433.92", 400.0, 340.0, 11.0),
    ]

    # 1. Normal order (top to bottom)
    pdf_normal = create_pdf_with_stream_order(elements)
    resp_normal, _ = process_invoice_pdf(pdf_normal)

    # 2. Reverse order (bottom elements drawn first in stream)
    elements_reversed = list(reversed(elements))
    pdf_reversed = create_pdf_with_stream_order(elements_reversed)
    resp_reversed, _ = process_invoice_pdf(pdf_reversed)

    # 3. Shuffled order (random stream order)
    import random
    elements_shuffled = list(elements)
    random.Random(42).shuffle(elements_shuffled)
    pdf_shuffled = create_pdf_with_stream_order(elements_shuffled)
    resp_shuffled, _ = process_invoice_pdf(pdf_shuffled)

    # All three extraction responses must be 100% identical
    assert resp_normal.vendor == resp_reversed.vendor == resp_shuffled.vendor == "Northwind Traders"
    assert resp_normal.invoice_number == resp_reversed.invoice_number == resp_shuffled.invoice_number == "NW-1042"
    assert resp_normal.total == resp_reversed.total == resp_shuffled.total == 433.92
    assert resp_normal.currency == resp_reversed.currency == resp_shuffled.currency == "GBP"


def test_metamorphic_vertical_jitter_invariance():
    """
    Metamorphic Test: Slight baseline jitter (± 1.0 pt) within a line should
    still cluster words into the same logical line.
    """
    doc = fitz.open()
    page = doc.new_page(width=595.27, height=841.89)

    # Insert words of "Invoice No: NW-9900" with slight vertical offsets
    page.insert_text(fitz.Point(50.0, 100.0), "Invoice", fontsize=10.0)
    page.insert_text(fitz.Point(90.0, 100.8), "No:", fontsize=10.0)
    page.insert_text(fitz.Point(120.0, 99.4), "NW-9900", fontsize=10.0)

    # Add vendor and totals
    page.insert_text(fitz.Point(50.0, 50.0), "Northwind Traders Ltd", fontsize=14.0)
    page.insert_text(fitz.Point(50.0, 200.0), "Total: GBP 100.00", fontsize=10.0)

    pdf_bytes = doc.tobytes()
    doc.close()

    resp, _ = process_invoice_pdf(pdf_bytes)
    assert resp.invoice_number == "NW-9900"
    assert resp.total == 100.00


def test_cpu_latency_ci_guard():
    """
    Latency CI Guard: PRD Constraint C2 requires latency < 1.0s on CPU.
    Our high-efficiency geometry parser should run in < 50ms p50 and < 200ms p95.
    Fails if any single document exceeds 500ms.
    """
    from generator.make_dataset import sample_invoice_data, render_invoice_pdf
    import random
    import tempfile

    rng = random.Random(100)
    latencies = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Generate 15 diverse documents
        pdf_bytes_list = []
        for i in range(15):
            data = sample_invoice_data(rng)
            pdf_path = tmp_path / f"test_{i}.pdf"
            render_invoice_pdf(data, pdf_path, rng)
            pdf_bytes_list.append(pdf_path.read_bytes())

        # Measure extraction latency per document
        for pdf_bytes in pdf_bytes_list:
            t0 = time.perf_counter()
            resp, _ = process_invoice_pdf(pdf_bytes)
            elapsed = time.perf_counter() - t0
            latencies.append(elapsed)

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    max_lat = max(latencies)

    # Strict CI latency assertions
    assert p50 < 0.050, f"Median latency {p50*1000:.1f}ms exceeds 50ms guard"
    assert p95 < 0.200, f"95th percentile latency {p95*1000:.1f}ms exceeds 200ms guard"
    assert max_lat < 0.500, f"Max latency {max_lat*1000:.1f}ms exceeds 500ms guard"
