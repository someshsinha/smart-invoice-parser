# Code Tour: Smart Invoice Parser

This document provides a concise architectural guide for each module in the repository.

## Module Map

- `app/main.py`: FastAPI service entrypoint. Manages lifespan warmup, `/health`, `/extract`, and static UI serving.
- `app/schemas.py`: Pydantic models enforcing the exact 8-field JSON API response schema.
- `app/config.py`: Centralized constants, regexes, and coordinate thresholds (all magic numbers documented).
- `app/pipeline.py`: Pipeline orchestrator connecting Reader -> Normalization -> Classification -> Extraction -> Cross-field Constraint Solving -> Response.
- `app/reader/pdf_text.py`: Geometry-aware PDF text extraction with PyMuPDF; extracts words, bboxes, font metrics, builds reading-order lines, and splits horizontal gaps into cells.
- `app/reader/normalize.py`: Unicode NFKC normalization, whitespace collapse, punctuation unification.
- `app/knowledge/`: Canonical vendor profiles (Appendix M), label synonym lexicons (Appendix B), locale rules (Appendix A), and currency symbols/codes.
- `app/parsing/`: Format-agnostic parsers for ISO/regional dates, decimal money amounts, and payment terms (e.g. Net 30).
- `app/extract/`: Domain extractors for doc-type, vendor, geometry-aware candidate pairing, invoice numbers, dates, amounts, currencies, confidence calibration, and diagnostic warnings.
- `generator/`: Synthetic invoice generator using ReportLab across diverse layout families with exact ground truth.
- `evaluation/`: Offline evaluation harness testing exact-match metrics, latency, and confidence calibration.
- `tests/`: Comprehensive offline test suite (unit, golden, business rules O1-O5, metamorphic, negative, API).
