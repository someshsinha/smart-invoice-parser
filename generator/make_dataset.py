"""
F16: Synthetic Dataset Generator CLI.
Generates diverse invoice PDFs across layout families with exact paired ground-truth JSON files.
Supports reproducible seeds, dev/val/heldout splits, noise models, and distractor lines.
"""

import argparse
import json
import random
from pathlib import Path
from datetime import date, timedelta
from typing import Dict, Any, Tuple, List

from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from generator.vocab import LINE_ITEMS, CUSTOMER_INFO, DECOY_VENDORS, VENDOR_ADDRESSES
from generator.noise import generate_distractors
from app.knowledge.vendors import CANONICAL_VENDORS

FONT_PATH = Path(__file__).resolve().parent / "fonts" / "DejaVuSans.ttf"
HAS_DEJAVU = False
if FONT_PATH.exists():
    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans", str(FONT_PATH)))
        HAS_DEJAVU = True
    except Exception:
        pass


def sample_invoice_data(rng: random.Random) -> Dict[str, Any]:
    """
    Samples a structured invoice data object with exact ground truth.
    """
    # 1. Decide if document is a non-invoice (quotation, delivery note, etc.) (~8%)
    is_non_invoice = rng.random() < 0.08
    doc_type = "invoice"
    if is_non_invoice:
        doc_type = rng.choice(["quotation", "delivery note", "statement", "purchase order"])

    # 2. Sample Vendor
    is_unknown = rng.random() < 0.12
    if is_unknown:
        decoy = rng.choice(DECOY_VENDORS)
        vendor_header = decoy["name"]
        ground_truth_vendor = "unknown"
        country = "India"
        currency = "INR"
        date_order = "DMY"
    else:
        canonical_name = rng.choice(list(CANONICAL_VENDORS.keys()))
        meta = CANONICAL_VENDORS[canonical_name]
        ground_truth_vendor = canonical_name
        country = meta["country"]
        currency = meta["currency"]
        date_order = meta["date_order"]

        # Variations in vendor name rendering
        brand_only = rng.random() < 0.10
        if brand_only:
            vendor_header = f"{meta['brand_token'].upper()} LTD"
        else:
            vendor_header = canonical_name
            # Suffix variations
            if rng.random() < 0.3:
                vendor_header = vendor_header.upper()
            elif country == "United Kingdom" and rng.random() < 0.3:
                vendor_header = vendor_header.replace("Harbour", "Harbor")

    # 3. Sample Dates & Terms
    inv_year = 2026
    # Ambiguous date (>50%): day and month both <= 12 and differ
    if rng.random() < 0.60:
        d = rng.randint(1, 12)
        m = rng.randint(1, 12)
        while d == m:
            m = rng.randint(1, 12)
    else:
        d = rng.randint(13, 28)
        m = rng.randint(1, 12)

    inv_date = date(inv_year, m, d)
    inv_date_iso = inv_date.isoformat()

    # Ambiguity check warning expectation
    date_warnings = []
    if d <= 12 and m <= 12 and d != m:
        order_str = "month" if date_order == "MDY" else "day"
        date_warnings.append(f"Date {d:02d}/{m:02d}/{inv_year} read as {order_str}-first ({country} vendor).")

    # Payment terms & Due date
    terms_days = rng.choice([0, 14, 15, 30, 45, 60])
    terms_style = rng.choice(["terms_only", "printed_only", "both_agree", "both_disagree", "neither"])

    printed_due_iso = None
    final_due_iso = None
    terms_str = None

    if terms_style == "terms_only":
        terms_str = f"Net {terms_days}"
        final_due_iso = (inv_date + timedelta(days=terms_days)).isoformat()
        date_warnings.append(f"Due date derived from terms {terms_str}.")
    elif terms_style == "printed_only":
        printed_due_iso = (inv_date + timedelta(days=terms_days)).isoformat()
        final_due_iso = printed_due_iso
    elif terms_style == "both_agree":
        terms_str = f"Net {terms_days}"
        printed_due_iso = (inv_date + timedelta(days=terms_days)).isoformat()
        final_due_iso = printed_due_iso
    elif terms_style == "both_disagree":
        terms_str = f"Net {terms_days}"
        printed_due_iso = (inv_date + timedelta(days=terms_days + 10)).isoformat()
        final_due_iso = printed_due_iso
        derived_iso = (inv_date + timedelta(days=terms_days)).isoformat()
        date_warnings.append(
            f"Printed due date {printed_due_iso} differs from terms {terms_str} ({derived_iso}); used printed date."
        )
    else:  # neither
        final_due_iso = None
        date_warnings.append("No due date or payment terms found.")

    # 4. Sample Line Items & Amounts
    num_items = rng.randint(1, 5)
    sampled_items = rng.sample(LINE_ITEMS, num_items)
    items_data = []
    subtotal = 0.0
    for desc, unit_price in sampled_items:
        qty = rng.randint(1, 10)
        line_total = round(qty * unit_price, 2)
        items_data.append((desc, qty, unit_price, line_total))
        subtotal += line_total
    subtotal = round(subtotal, 2)

    # Tax rates
    tax_rate = 0.20 if currency == "GBP" else (0.19 if currency == "EUR" else (0.08 if currency == "USD" else 0.18))
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)

    amount_warnings = []
    # Inject Rule O2 arithmetic mismatch (~4%)
    if rng.random() < 0.04:
        total = round(total + 5.00, 2)
        amount_warnings.append(
            f"Subtotal plus tax does not equal total ({subtotal:.2f} + {tax:.2f} != {total:.2f})."
        )

    # Invoice number
    inv_num = f"{ground_truth_vendor[:2].upper()}-{rng.randint(1000, 9999)}"

    # All warnings
    warnings = []
    if ground_truth_vendor == "unknown":
        warnings.append("Vendor name not in the canonical list.")
    elif brand_only:
        warnings.append(f"Vendor matched on brand name only ({ground_truth_vendor}).")

    if is_non_invoice:
        warnings.append(f"Document appears to be a {doc_type}, not an invoice.")

    warnings.extend(date_warnings)
    warnings.extend(amount_warnings)

    # Ground truth mapping
    if is_non_invoice:
        gt = {
            "vendor": ground_truth_vendor,
            "invoice_number": None,
            "invoice_date": None,
            "due_date": None,
            "currency": None,
            "subtotal": None,
            "tax": None,
            "total": None,
            "warnings": warnings,
        }
    else:
        gt = {
            "vendor": ground_truth_vendor,
            "invoice_number": inv_num,
            "invoice_date": inv_date_iso,
            "due_date": final_due_iso,
            "currency": currency,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "warnings": warnings,
        }

    return {
        "header_vendor": vendor_header,
        "doc_type": doc_type,
        "is_non_invoice": is_non_invoice,
        "country": country,
        "currency": currency,
        "date_order": date_order,
        "inv_num": inv_num,
        "inv_date": inv_date,
        "inv_date_iso": inv_date_iso,
        "printed_due_iso": printed_due_iso,
        "terms_str": terms_str,
        "items": items_data,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "ground_truth": gt,
    }


def render_invoice_pdf(data: Dict[str, Any], output_path: Path, rng: random.Random):
    """
    Renders structured invoice data into a PDF using ReportLab canvas.
    """
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    font_name = "DejaVuSans" if HAS_DEJAVU else "Helvetica"
    font_bold = "DejaVuSans" if HAS_DEJAVU else "Helvetica-Bold"

    y = height - 50.0

    # 1. Vendor Header
    c.setFont(font_bold, 14.0)
    c.drawString(50.0, y, data["header_vendor"])
    y -= 18.0

    # Address
    c.setFont(font_name, 9.0)
    vendor_addr = VENDOR_ADDRESSES.get(data["ground_truth"]["vendor"], "100 Commercial Way, Industrial Estate")
    c.drawString(50.0, y, vendor_addr)
    y -= 25.0

    # Document Title
    title = "INVOICE" if not data["is_non_invoice"] else data["doc_type"].upper()
    c.setFont(font_bold, 15.0)
    c.drawRightString(width - 50.0, y + 10.0, title)
    y -= 10.0

    # Metadata Block
    num_label = "Invoice No:"
    date_label = "Invoice Date:"
    if data["is_non_invoice"]:
        dt = data["doc_type"]
        if dt == "quotation":
            num_label, date_label = "Quote No:", "Quote Date:"
        elif dt == "delivery note":
            num_label, date_label = "Delivery Note No:", "Delivery Date:"
        elif dt == "statement":
            num_label, date_label = "Statement No:", "Statement Date:"
        elif dt == "purchase order":
            num_label, date_label = "PO No:", "Order Date:"
        elif dt == "credit note":
            num_label, date_label = "Credit Note No:", "Credit Note Date:"

    c.setFont(font_bold, 9.5)
    c.drawString(50.0, y, num_label)
    c.setFont(font_name, 9.5)
    c.drawString(160.0, y, data["inv_num"])
    y -= 15.0

    # Format date according to date_order
    d_obj = data["inv_date"]
    if data["date_order"] == "MDY":
        d_str = f"{d_obj.month}/{d_obj.day}/{d_obj.year}"
    else:
        d_str = f"{d_obj.day:02d}/{d_obj.month:02d}/{d_obj.year}"

    c.setFont(font_bold, 9.5)
    c.drawString(50.0, y, date_label)
    c.setFont(font_name, 9.5)
    c.drawString(160.0, y, d_str)
    y -= 15.0

    if data["printed_due_iso"]:
        due_d = date.fromisoformat(data["printed_due_iso"])
        due_str = f"{due_d.day:02d}/{due_d.month:02d}/{due_d.year}"
        c.setFont(font_bold, 9.5)
        c.drawString(50.0, y, "Due Date:")
        c.setFont(font_name, 9.5)
        c.drawString(140.0, y, due_str)
        y -= 15.0

    if data["terms_str"]:
        c.setFont(font_bold, 9.5)
        c.drawString(50.0, y, "Terms:")
        c.setFont(font_name, 9.5)
        c.drawString(140.0, y, data["terms_str"])
        y -= 15.0

    # Customer Block
    y -= 10.0
    c.setFont(font_bold, 9.5)
    c.drawString(50.0, y, "Bill to:")
    c.setFont(font_name, 9.5)
    c.drawString(140.0, y, CUSTOMER_INFO["name"])
    y -= 25.0

    # Distractor Lines
    distractors = generate_distractors(rng)
    c.setFont(font_name, 8.5)
    for dist in distractors:
        c.drawString(50.0, y, dist)
        y -= 12.0
    y -= 10.0

    # Items Table Header
    c.setFont(font_bold, 9.5)
    c.drawString(50.0, y, "Item Description")
    c.drawString(300.0, y, "Qty")
    c.drawString(380.0, y, "Unit Price")
    c.drawString(470.0, y, "Total")
    y -= 6.0
    c.line(50.0, y, width - 50.0, y)
    y -= 16.0

    # Line Items
    c.setFont(font_name, 9.0)
    for desc, qty, price, total_amt in data["items"]:
        c.drawString(50.0, y, desc[:40])
        c.drawString(305.0, y, str(qty))
        c.drawString(385.0, y, f"{price:.2f}")
        c.drawRightString(width - 50.0, y, f"{total_amt:.2f}")
        y -= 15.0

    y -= 10.0
    c.line(320.0, y, width - 50.0, y)
    y -= 18.0

    # Totals Box
    cur = data["currency"]
    c.setFont(font_name, 9.5)
    c.drawRightString(420.0, y, "Subtotal:")
    c.drawRightString(width - 50.0, y, f"{data['subtotal']:.2f}")
    y -= 16.0

    c.drawRightString(420.0, y, "Tax:")
    c.drawRightString(width - 50.0, y, f"{data['tax']:.2f}")
    y -= 18.0

    c.setFont(font_bold, 10.5)
    c.drawRightString(420.0, y, "Amount Due:")
    c.drawRightString(width - 50.0, y, f"{cur} {data['total']:.2f}")

    c.save()


def generate_dataset_split(split_name: str, n_docs: int, seed: int, out_dir: Path):
    """
    Generates n_docs invoices with matching JSON ground truth into out_dir.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    print(f"\nGenerating {n_docs} documents for split '{split_name}' (seed {seed}) in {out_dir}...")

    for i in range(1, n_docs + 1):
        inv_data = sample_invoice_data(rng)
        file_prefix = f"inv_{split_name}_{i:04d}"
        pdf_path = out_dir / f"{file_prefix}.pdf"
        json_path = out_dir / f"{file_prefix}.json"

        render_invoice_pdf(inv_data, pdf_path, rng)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(inv_data["ground_truth"], f, indent=2)

    print(f"Generated {n_docs} synthetic invoice pairs in {out_dir}.")


def main():
    parser = argparse.ArgumentParser(description="Synthetic Invoice Dataset Generator CLI")
    parser.add_argument("--split", type=str, default="dev", choices=["dev", "val", "heldout"], help="Dataset split name")
    parser.add_argument("--n", type=int, default=10, help="Number of documents to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory path")
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else Path(f"data/{args.split}")
    generate_dataset_split(args.split, args.n, args.seed, out_dir)


if __name__ == "__main__":
    main()
