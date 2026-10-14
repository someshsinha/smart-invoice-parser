# Smart Invoice Parser (Bruviti Campus Drive 2026 - Use Case 3)

A high-performance, deterministic, 100% offline invoice field extraction service built with Python and FastAPI. Extracts eight canonical invoice header fields with calibrated confidence scores and diagnostic verification warnings.

---

## 1. Quick Start (The One Command)

To install dependencies and start the service on port 8000 from a fresh clone:

```bash
pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Health Check

Verify the service is ready:
```bash
curl http://localhost:8000/health
```
Response:
```json
{"status": "ok"}
```

### Web Interface

Open your browser at:
```text
http://localhost:8000/
```
The single-page web UI provides interactive drag-and-drop PDF extraction, pre-bundled sample invoices, field cards with confidence progress bars, verification warning boxes, and raw JSON copying.

---

## 2. API Contract & Extraction Endpoint

### Extract Invoice Fields (`POST /extract`)

Upload a supplier invoice PDF using multipart form-data (part name `file`):

```bash
curl -X POST -F "file=@samples/northwind_1042.pdf" http://localhost:8000/extract
```

Example JSON response:
```json
{
  "vendor": "Northwind Traders",
  "invoice_number": "NW-1042",
  "invoice_date": "2026-09-03",
  "due_date": "2026-10-03",
  "currency": "GBP",
  "subtotal": 361.6,
  "tax": 72.32,
  "total": 433.92,
  "confidence": {
    "vendor": 0.95,
    "invoice_number": 0.95,
    "invoice_date": 0.92,
    "due_date": 0.9,
    "currency": 0.95,
    "subtotal": 0.97,
    "tax": 0.97,
    "total": 0.97
  },
  "warnings": []
}
```

### Response Schema Fields
- `vendor` (`string`): One of the six canonical vendor names from Appendix M, or `"unknown"`.
- `invoice_number` (`string` or `null`): Exactly as printed, trimmed, case and hyphens preserved.
- `invoice_date` (`string` or `null`): ISO `YYYY-MM-DD`.
- `due_date` (`string` or `null`): ISO `YYYY-MM-DD`. Converted from payment terms (e.g. `Net 30`) if only terms are printed.
- `currency` (`string` or `null`): ISO 4217 code (`GBP`, `USD`, `EUR`, `JPY`, `INR`), or `null` if unidentifiable or non-invoice.
- `subtotal` (`number` or `null`): Pre-tax amount, two decimals, no thousands separators.
- `tax` (`number` or `null`): Total tax amount on invoice, or `null` if absent or non-invoice.
- `total` (`number` or `null`): Amount payable, or `null` if absent or non-invoice.
- `confidence` (`object`): Calibrated float between `0.0` and `1.0` for each of the eight fields. Null fields receive `0.0`.
- `warnings` (`array of strings`): Diagnostic warnings explaining ambiguities, terms derivation, or arithmetic mismatches.

---

## 3. Running the Test Suite (100% Offline)

Install development dependencies and run the offline test suite:

```bash
pip install -r requirements-dev.txt && pytest -q
```

All 94 tests run strictly without network access, enforced by an automated socket blocker in `tests/conftest.py`.

---

## 4. Evaluation Benchmark & Latency Profiling

Run the offline evaluation harness across the canonical test fixtures:

```bash
python -m evaluation.run --dir samples
```

Sample output:
```text
======================================================================
INVOICE EXTRACTION EVALUATION REPORT (EXACT MATCH)
======================================================================
Total Documents Evaluated : 4
Overall Exact Match Score : 100.00%
Latency Percentiles (CPU) : p50 = 12.7ms | p95 = 30.4ms | max = 30.4ms
----------------------------------------------------------------------
Field              | Exact Match Accuracy  
----------------------------------------------------------------------
vendor             | 100.00%  ████████████████████
invoice_number     | 100.00%  ████████████████████
invoice_date       | 100.00%  ████████████████████
due_date           | 100.00%  ████████████████████
currency           | 100.00%  ████████████████████
subtotal           | 100.00%  ████████████████████
tax                | 100.00%  ████████████████████
total              | 100.00%  ████████████████████
----------------------------------------------------------------------
Zero failures found! 100% exact match across all evaluated documents.
```

---

## 5. Repository Layout

```text
├── README.md               # Quickstart, API contract, and operational guide
├── DATA.md                 # Data sourcing, generator design, and failure modes
├── NOTES.md                # Architectural decisions, trade-offs, and cuts (<= 1 page)
├── AI.md                   # AI usage disclosure and transparency documentation
├── requirements.txt        # Pinned runtime dependencies
├── requirements-dev.txt    # Pinned development and testing dependencies
├── pytest.ini              # Pytest configuration
├── static/
│   └── index.html          # Single-page offline web UI
├── samples/                # Bundled sample PDFs with paired ground-truth JSON
├── app/
│   ├── main.py             # FastAPI entrypoint, healthcheck, and error handling
│   ├── schemas.py          # Pydantic response models
│   ├── config.py           # Documented thresholds and configuration constants
│   ├── pipeline.py         # Pipeline orchestrator
│   ├── reader/             # Geometry-aware text extraction and normalization
│   ├── knowledge/          # Canonical vendor profiles, lexicons, locales, currencies
│   ├── parsing/            # Date, amount, and payment terms parsers
│   └── extract/            # Field extractors, arithmetic solver, confidence model
├── generator/              # ReportLab synthetic invoice and sample generator
├── evaluation/             # Exact-match metric calculation and benchmark CLI
├── tests/                  # Offline unit, rule, and golden test suites
└── docs/
    └── CODE_TOUR.md        # Architectural module overview
```
