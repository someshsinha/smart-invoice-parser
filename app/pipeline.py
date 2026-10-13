"""
Pipeline orchestrator.
Coordinates the extraction stages from raw PDF bytes to InvoiceExtractionResponse.
"""

import time
from typing import Optional, Tuple
from app.schemas import InvoiceExtractionResponse, FieldConfidence
from app.reader.pdf_text import extract_document_text
from app.extract.doctype import classify_document_type
from app.extract.vendor import resolve_vendor
from app.extract.dates import extract_dates
from app.extract.amounts import extract_amounts
from app.extract.currency import extract_currency
from app.extract.invoice_number import extract_invoice_number
from app.extract.confidence import calibrate_confidences


def process_invoice_pdf(pdf_bytes: bytes, debug: bool = False) -> Tuple[InvoiceExtractionResponse, Optional[dict]]:
    """
    Process raw PDF bytes through extraction stages:
    Reader -> Normalizer -> DocType (Rule O4) -> Vendor (Appendix M) -> Candidates -> Parsers -> Solver -> Confidence.
    """
    t0 = time.perf_counter()

    # 1. Geometry-aware text extraction
    parsed_doc = extract_document_text(pdf_bytes)
    t_reader = time.perf_counter()

    # 2. Check for scanned / empty text layer (§3.5)
    if not parsed_doc.has_text:
        debug_info = {
            "has_text": False,
            "timings_ms": {"reader": round((t_reader - t0) * 1000, 2), "total": round((time.perf_counter() - t0) * 1000, 2)},
        } if debug else None
        return InvoiceExtractionResponse(
            vendor="unknown",
            invoice_number=None,
            invoice_date=None,
            due_date=None,
            currency=None,
            subtotal=None,
            tax=None,
            total=None,
            confidence=FieldConfidence(),
            warnings=["No text layer found; scanned documents are out of scope."],
            debug=debug_info,
        ), debug_info

    # 3. Resolve Vendor (F4)
    vendor, vendor_conf, vendor_warnings = resolve_vendor(parsed_doc)

    # 4. Classify Document Type (Rule O4)
    is_invoice, doc_type, doctype_warning = classify_document_type(parsed_doc)
    if not is_invoice:
        warnings = [doctype_warning] if doctype_warning else []
        warnings.extend(vendor_warnings)
        confidence = FieldConfidence(vendor=vendor_conf)
        debug_info = {
            "doc_type": doc_type,
            "is_invoice": False,
            "timings_ms": {"reader": round((t_reader - t0) * 1000, 2), "total": round((time.perf_counter() - t0) * 1000, 2)},
        } if debug else None
        response = InvoiceExtractionResponse(
            vendor=vendor,
            invoice_number=None,
            invoice_date=None,
            due_date=None,
            currency=None,
            subtotal=None,
            tax=None,
            total=None,
            confidence=confidence,
            warnings=warnings,
            debug=debug_info,
        )
        return response, debug_info

    # 5. Extract Dates & Payment Terms (Rule O1)
    inv_date, inv_date_conf, due_date, due_date_conf, date_warnings = extract_dates(parsed_doc, vendor)

    # 6. Extract Invoice Number (F9)
    inv_num, inv_num_conf, inv_num_warnings = extract_invoice_number(parsed_doc)

    # 7. Extract Amounts with Arithmetic Solver (Rule O2 & Rule O5)
    subtotal, sub_conf, tax, tax_conf, total, tot_conf, amount_warnings = extract_amounts(parsed_doc, vendor)

    # 8. Extract Currency (Rule O3 & Rule O5)
    currency, curr_conf, curr_warnings = extract_currency(parsed_doc, vendor)

    all_warnings = vendor_warnings + date_warnings + inv_num_warnings + amount_warnings + curr_warnings

    # 9. Compute Calibrated Confidences (F13)
    confidence = calibrate_confidences(
        vendor=vendor,
        invoice_number=inv_num,
        invoice_date=inv_date,
        due_date=due_date,
        currency=currency,
        subtotal=subtotal,
        tax=tax,
        total=total,
        warnings=all_warnings,
        has_text=parsed_doc.has_text,
    )

    t_end = time.perf_counter()

    debug_info = None
    if debug:
        arithmetic_match = (
            subtotal is not None and tax is not None and total is not None
            and abs(round(subtotal + tax, 2) - round(total, 2)) < 0.01
        )
        debug_info = {
            "timings_ms": {
                "reader": round((t_reader - t0) * 1000, 2),
                "extraction": round((t_end - t_reader) * 1000, 2),
                "total": round((t_end - t0) * 1000, 2),
            },
            "document": {
                "page_count": len(parsed_doc.pages),
                "line_count": sum(len(p.lines) for p in parsed_doc.pages),
                "is_invoice": is_invoice,
                "doc_type": doc_type,
            },
            "arithmetic": {
                "subtotal": subtotal,
                "tax": tax,
                "calculated_sum": round(subtotal + tax, 2) if (subtotal is not None and tax is not None) else None,
                "printed_total": total,
                "is_balanced": arithmetic_match,
            },
            "provenance": {
                "vendor": vendor,
                "invoice_number": inv_num,
                "invoice_date": inv_date,
                "due_date": due_date,
                "currency": currency,
                "total": total,
            },
        }

    response = InvoiceExtractionResponse(
        vendor=vendor,
        invoice_number=inv_num,
        invoice_date=inv_date,
        due_date=due_date,
        currency=currency,
        subtotal=subtotal,
        tax=tax,
        total=total,
        confidence=confidence,
        warnings=all_warnings,
        debug=debug_info,
    )
    return response, debug_info




