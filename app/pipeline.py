"""
Pipeline orchestrator.
Coordinates the extraction stages from raw PDF bytes to InvoiceExtractionResponse.
"""

from typing import Optional, Tuple
from app.schemas import InvoiceExtractionResponse, FieldConfidence


def process_invoice_pdf(pdf_bytes: bytes, debug: bool = False) -> Tuple[InvoiceExtractionResponse, Optional[dict]]:
    """
    Process raw PDF bytes through the extraction stages:
    Reader -> Normalizer -> DocType -> Vendor -> Candidates -> Parsers -> Solver -> Confidence.
    """
    # Baseline stub implementation for Phase 0
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
        warnings=["Pipeline stub initialized."],
        debug={"stub": True} if debug else None,
    )
    return response, ({"stub": True} if debug else None)
