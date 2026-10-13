"""
Generator script to render the canonical Appendix N invoices and test fixtures as digital PDFs using ReportLab.
Outputs both PDF files and ground-truth JSON files to samples/ and tests/fixtures/.
"""

import json
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = BASE_DIR / "samples"
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"


def generate_northwind_pdf(pdf_path: Path):
    """Generates Northwind Traders Example 1 PDF from Appendix N."""
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4

    # Top Margin
    y = height - 50

    # Letterhead
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "NORTHWIND TRADERS LTD")
    y -= 18

    c.setFont("Helvetica", 10)
    c.drawString(50, y, "14 Quay Street, Bristol BS1 4DB, United Kingdom")
    y -= 14
    c.drawString(50, y, "VAT No. GB 123 4567 89")
    y -= 25

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(width - 50, y + 20, "INVOICE")
    y -= 10

    # Metadata
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Invoice No:")
    c.setFont("Helvetica", 10)
    c.drawString(130, y, "NW-1042")
    y -= 16

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Invoice Date:")
    c.setFont("Helvetica", 10)
    c.drawString(130, y, "03/09/2026")
    y -= 16

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Due Date:")
    c.setFont("Helvetica", 10)
    c.drawString(130, y, "03/10/2026")
    y -= 25

    # Bill to
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Bill to:")
    c.setFont("Helvetica", 10)
    c.drawString(130, y, "Bruviti Services Pvt Ltd")
    y -= 35

    # Table Header
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Item")
    c.drawString(240, y, "Qty")
    c.drawString(300, y, "Unit Price")
    c.drawString(400, y, "Amount")
    y -= 6
    c.setLineWidth(0.5)
    c.line(50, y, width - 50, y)
    y -= 16

    # Line Items
    items = [
        ("Pallet wrap, 500mm", "12", "18.50", "222.00"),
        ("Corrugated boxes, large", "40", "2.35", "94.00"),
        ("Packing tape, brown", "24", "1.90", "45.60"),
    ]
    c.setFont("Helvetica", 10)
    for desc, qty, price, amt in items:
        c.drawString(50, y, desc)
        c.drawString(245, y, qty)
        c.drawString(310, y, price)
        c.drawString(410, y, amt)
        y -= 16

    y -= 10
    c.line(300, y, width - 50, y)
    y -= 18

    # Totals
    c.setFont("Helvetica", 10)
    c.drawRightString(380, y, "Subtotal")
    c.drawRightString(460, y, "361.60")
    y -= 16

    c.drawRightString(380, y, "VAT 20%")
    c.drawRightString(460, y, "72.32")
    y -= 18

    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(380, y, "Amount Due")
    c.drawRightString(460, y, "GBP 433.92")

    c.save()


def generate_kestrel_pdf(pdf_path: Path):
    """Generates Kestrel Components Example 2 PDF from Appendix N."""
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter

    y = height - 50

    # Header with pipe separator
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Kestrel Components Inc.  |  880 Industrial Pkwy, Dayton OH 45402, USA")
    y -= 25

    # Inline Reference and Dated
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Reference #")
    c.setFont("Helvetica", 10)
    c.drawString(130, y, "KC-0311")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(240, y, "Dated")
    c.setFont("Helvetica", 10)
    c.drawString(290, y, "9/3/26")
    y -= 18

    # Terms Net 30
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Terms")
    c.setFont("Helvetica", 10)
    c.drawString(130, y, "Net 30")
    y -= 18

    # Sold to
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Sold to")
    c.setFont("Helvetica", 10)
    c.drawString(130, y, "Bruviti Services Pvt Ltd")
    y -= 30

    # Items table (with trap header "Particulars  Total")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Particulars")
    c.drawString(380, y, "Total")
    y -= 6
    c.line(50, y, width - 50, y)
    y -= 16

    items = [
        ("Bearing kit 6204-2RS (x10)", "145.00"),
        ("Drive belt A-42 (x4)", "62.80"),
        ("Shipping", "18.00"),
    ]
    c.setFont("Helvetica", 10)
    for desc, amt in items:
        c.drawString(50, y, desc)
        c.drawString(390, y, amt)
        y -= 16

    y -= 8
    c.line(340, y, width - 50, y)
    y -= 18

    c.drawString(300, y, "Sub total")
    c.drawString(390, y, "225.80")
    y -= 16

    c.drawString(300, y, "Sales tax 7.25%")
    c.drawString(390, y, "16.37")
    y -= 18

    c.setFont("Helvetica-Bold", 10)
    c.drawString(300, y, "Balance Due")
    c.drawString(380, y, "$ 242.17")

    c.save()


def generate_unknown_vendor_pdf(pdf_path: Path):
    """Generates Unknown Vendor Example 3 PDF."""
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Apex Supplies Ltd")
    y -= 25

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Invoice Number:")
    c.setFont("Helvetica", 10)
    c.drawString(160, y, "7781")
    y -= 16

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Invoice Date:")
    c.setFont("Helvetica", 10)
    c.drawString(160, y, "2026-08-21")
    y -= 25

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Billed To:")
    c.setFont("Helvetica", 10)
    c.drawString(160, y, "Bruviti Services Pvt Ltd")
    y -= 40

    c.drawString(50, y, "Services Rendered")
    c.drawRightString(450, y, "12000.00")
    y -= 25

    c.drawString(300, y, "Subtotal:")
    c.drawRightString(450, y, "INR 12000.00")
    y -= 16

    c.drawString(300, y, "GST Tax:")
    c.drawRightString(450, y, "INR 2160.00")
    y -= 18

    c.setFont("Helvetica-Bold", 11)
    c.drawString(300, y, "Total Payable:")
    c.drawRightString(450, y, "INR 14160.00")

    c.save()


def generate_german_meridian_pdf(pdf_path: Path):
    """Generates German DIN-style PDF for Meridian Industrial GmbH."""
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Meridian Industrial GmbH")
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawString(50, y, "Industriestraße 10, 70173 Stuttgart, Deutschland")
    y -= 30

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "RECHNUNG")
    y -= 25

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Rechnungsnummer:")
    c.setFont("Helvetica", 10)
    c.drawString(170, y, "MI-8821")
    y -= 16

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Rechnungsdatum:")
    c.setFont("Helvetica", 10)
    c.drawString(170, y, "12.09.2026")
    y -= 16

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Fälligkeitsdatum:")
    c.setFont("Helvetica", 10)
    c.drawString(170, y, "12.10.2026")
    y -= 25

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Kunde:")
    c.setFont("Helvetica", 10)
    c.drawString(170, y, "Bruviti Services Pvt Ltd")
    y -= 40

    c.drawString(50, y, "Industriebedarf Position 1")
    c.drawRightString(450, y, "1.200,00 €")
    y -= 25

    c.drawString(300, y, "Nettobetrag:")
    c.drawRightString(450, y, "1.200,00 €")
    y -= 16

    c.drawString(300, y, "MwSt 19%:")
    c.drawRightString(450, y, "228,00 €")
    y -= 18

    c.setFont("Helvetica-Bold", 11)
    c.drawString(300, y, "Gesamtbetrag:")
    c.drawRightString(450, y, "1.428,00 €")

    c.save()


def build_all_samples():
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Northwind
    nw_pdf = SAMPLES_DIR / "northwind_1042.pdf"
    generate_northwind_pdf(nw_pdf)
    nw_gt = {
        "vendor": "Northwind Traders",
        "invoice_number": "NW-1042",
        "invoice_date": "2026-09-03",
        "due_date": "2026-10-03",
        "currency": "GBP",
        "subtotal": 361.6,
        "tax": 72.32,
        "total": 433.92,
        "warnings": [],
    }
    with open(SAMPLES_DIR / "northwind_1042.json", "w") as f:
        json.dump(nw_gt, f, indent=2)

    # 2. Kestrel
    kc_pdf = SAMPLES_DIR / "kestrel_0311.pdf"
    generate_kestrel_pdf(kc_pdf)
    kc_gt = {
        "vendor": "Kestrel Components",
        "invoice_number": "KC-0311",
        "invoice_date": "2026-09-03",
        "due_date": "2026-10-03",
        "currency": "USD",
        "subtotal": 225.8,
        "tax": 16.37,
        "total": 242.17,
        "warnings": [
            "Date 9/3/26 read as month-first (US vendor).",
            "Due date derived from terms Net 30.",
        ],
    }
    with open(SAMPLES_DIR / "kestrel_0311.json", "w") as f:
        json.dump(kc_gt, f, indent=2)

    # 3. Unknown Vendor
    unk_pdf = SAMPLES_DIR / "unknown_vendor.pdf"
    generate_unknown_vendor_pdf(unk_pdf)
    unk_gt = {
        "vendor": "unknown",
        "invoice_number": "7781",
        "invoice_date": "2026-08-21",
        "due_date": None,
        "currency": "INR",
        "subtotal": 12000.0,
        "tax": 2160.0,
        "total": 14160.0,
        "warnings": [
            "Vendor name not in the canonical list.",
            "No due date or payment terms found.",
        ],
    }
    with open(SAMPLES_DIR / "unknown_vendor.json", "w") as f:
        json.dump(unk_gt, f, indent=2)

    # 4. Meridian German
    de_pdf = SAMPLES_DIR / "meridian_german.pdf"
    generate_german_meridian_pdf(de_pdf)
    de_gt = {
        "vendor": "Meridian Industrial",
        "invoice_number": "MI-8821",
        "invoice_date": "2026-09-12",
        "due_date": "2026-10-12",
        "currency": "EUR",
        "subtotal": 1200.0,
        "tax": 228.0,
        "total": 1428.0,
        "warnings": [],
    }
    with open(SAMPLES_DIR / "meridian_german.json", "w") as f:
        json.dump(de_gt, f, indent=2)

    # Copy / Mirror to tests/fixtures
    for name in ["northwind_1042", "kestrel_0311", "unknown_vendor", "meridian_german"]:
        (FIXTURES_DIR / f"{name}.pdf").write_bytes((SAMPLES_DIR / f"{name}.pdf").read_bytes())
        (FIXTURES_DIR / f"{name}.json").write_text((SAMPLES_DIR / f"{name}.json").read_text())

    print(f"Successfully generated all samples in {SAMPLES_DIR} and {FIXTURES_DIR}")


if __name__ == "__main__":
    build_all_samples()
