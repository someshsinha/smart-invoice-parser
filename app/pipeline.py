"""
Pipeline orchestrator.
Coordinates the extraction stages from raw PDF bytes to InvoiceExtractionResponse.
"""

from typing import Optional, Tuple
from app.schemas import InvoiceExtractionResponse, FieldConfidence
from app.reader.pdf_text import extract_document_text


def process_invoice_pdf(pdf_bytes: bytes, debug: bool = False) -> Tuple[InvoiceExtractionResponse, Optional[dict]]:
    """
    Process raw PDF bytes through extraction stages:
    Reader -> Normalizer -> DocType -> Vendor -> Candidates -> Parsers -> Solver -> Confidence.
    """
    # 1. Geometry-aware text extraction
    parsed_doc = extract_document_text(pdf_bytes)

    # 2. Check for scanned / empty text layer (§3.5)
    if not parsed_doc.has_text:
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
            debug={"has_text": False} if debug else None,
        ), ({"has_text": False} if debug else None)

    # Temporary baseline stub for documents with text layer
    confidence = FieldConfidence()
    response = InvoiceExtractionResponse(
        vendor="unknown",
        invoice_number=None,
        invoice_date=None,
        due_date=None,
        currency=None,
        subtotal=None,
        tax=None,
        total=None,
        confidence=confidence,
        warnings=[],
        debug={"parsed_lines": len(parsed_doc.pages[0].lines)} if debug and parsed_doc.pages else None,
    )
    return response, ({"text_length": len(parsed_doc.full_text)} if debug else None)
