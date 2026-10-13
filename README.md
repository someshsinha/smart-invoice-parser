# Smart Invoice Parser (Bruviti Campus Drive 2026 - Use Case 3)

A fast, robust, 100% offline digital invoice field extraction service built with Python, FastAPI, and geometry-aware rule-based heuristics. Extracts eight canonical invoice fields with confidence scores and diagnostic warnings.

---

## 1. Quick Start (The One Command)

To install dependencies and start the service on port 8000 from a fresh clone:

```bash
pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Health Check

Verify the service is running:
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
The single-page web UI allows interactive drag-and-drop PDF extraction, sample inspection, confidence inspection, and raw JSON viewing.

---

## 2. API Usage

### Extract Invoice Fields (`POST /extract`)

Upload a PDF invoice using multipart form-data (part name `file`):

```bash
curl -X POST -F "file=@path/to/invoice.pdf" http://localhost:8000/extract
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
    "vendor": 0.98,
    "invoice_number": 0.95,
    "invoice_date": 0.9,
    "due_date": 0.9,
    "currency": 0.95,
    "subtotal": 0.97,
    "tax": 0.97,
    "total": 0.97
  },
  "warnings": []
}
```

---

## 3. Running the Test Suite (100% Offline)

Install development dependencies and run tests:

```bash
pip install -r requirements-dev.txt && pytest -q
```

All tests are verified to execute strictly offline with an active socket blocker.

---

## 4. Evaluation and Synthetic Dataset Generation

To generate the synthetic dataset splits:
```bash
python -m generator.make_dataset --split dev --n 600 --seed 1
```

To run the offline evaluation harness against a split:
```bash
python -m evaluation.run --split dev
```

---

## 5. Repository Layout

```text
├── README.md               # Quickstart, API contract, and operational instructions
├── DATA.md                 # Data sourcing, generator design, and failure modes
├── NOTES.md                # Architectural decisions, trade-offs, and cuts (<= 1 page)
├── AI.md                   # AI tool usage attribution and transparency
├── requirements.txt        # Pinned runtime dependencies
├── requirements-dev.txt    # Pinned development and testing dependencies
├── pytest.ini              # Pytest configuration
├── static/
│   └── index.html          # Single-page offline web UI
├── samples/                # Bundled sample PDFs for manual testing
├── app/
│   ├── main.py             # FastAPI entrypoint and routes
│   ├── schemas.py          # Pydantic response models
│   ├── config.py           # Thresholds and configuration
│   ├── pipeline.py         # Pipeline orchestrator
│   ├── reader/             # Geometry-aware text extraction and normalization
│   ├── knowledge/          # Canonical vendor profiles, lexicons, locales
│   ├── parsing/            # Date, amount, and payment terms parsers
│   └── extract/            # Field extractors, arithmetic solver, confidence model
├── generator/              # ReportLab synthetic invoice generation
├── evaluation/             # Evaluation metrics and benchmark harness
├── tests/                  # Offline test suite
└── docs/
    └── CODE_TOUR.md        # Architectural module overview
```
