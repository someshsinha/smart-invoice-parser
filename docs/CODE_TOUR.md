# CODE_TOUR.md: Technical Architecture & Module Walkthrough

This document is a 1-page guide to the codebase architecture, request flow, and extension patterns.

---

## 1. Request Flow (End-to-End)

```text
POST /extract (PDF bytes)
   │
   ├─► 1. app/reader/pdf_text.py      : PyMuPDF words -> vertical line clustering -> horizontal cell splitting
   ├─► 2. app/reader/normalize.py     : Unicode NFKC, whitespace collapse, punctuation unification
   ├─► 3. app/extract/doctype.py      : Title-zone classification (Rule O4 short-circuit if non-invoice)
   ├─► 4. app/extract/vendor.py       : Appendix M fuzzy brand-token gating & decoy rejection
   ├─► 5. app/extract/candidates.py   : Spatial candidate generation (same_line, right_cell, below_row)
   ├─► 6. app/extract/dates.py        : Regional format parsing & Net N payment terms solver (Rule O1)
   ├─► 7. app/extract/amounts.py      : Multi-tax summing & subtotal + tax = total solver (Rules O2, O5)
   ├─► 8. app/extract/currency.py     : Totals-proximity symbol ranking & vendor fallback (Rule O3)
   ├─► 9. app/extract/invoice_number.py: Distractor filtering (PO/VAT/IBAN) & prefix preservation
   └─► 10. app/extract/confidence.py  : Explainable formula scoring & centralized warnings catalog
```

---

## 2. Module Map (3-Line Specifications)

### `app/reader/pdf_text.py`
- **What it does:** Extracts words with physical $(x_0, y_0, x_1, y_1)$ bounding boxes and font sizes from PDF streams.
- **Algorithm worth knowing:** Geometry-first clustering — sorts words top-to-bottom, clusters by vertical baseline overlap ($\Delta y \le 0.5 \times \text{height}$), and splits lines into distinct cells wherever horizontal whitespace gap exceeds $1.4 \times$ character height.
- **Failure mode:** Scanned PDFs with no digital text layer return `has_text=False` (gracefully caught under PRD §3.5).

### `app/extract/doctype.py`
- **What it does:** Distinguishes invoices from quotations, delivery notes, purchase orders, and statements (Rule O4).
- **Algorithm worth knowing:** Title-zone keyword gating — searches the top 35% of page 1 and large-font lines, distinguishing standalone titles (e.g. `STATEMENT`) from cross-reference fields (e.g. `Purchase Order: PO-998877`).
- **Failure mode:** Non-invoice documents with misleading body text like `original invoice ref` are protected by checking only the header/title zone.

### `app/extract/vendor.py`
- **What it does:** Resolves vendor identity to one of the 6 canonical names (Appendix M) or `"unknown"`.
- **Algorithm worth knowing:** Two-stage brand-token gating — requires brand token match (Levenshtein distance $\le 2$) AND verifies that generic words (`Logistics` vs `Traders`) do not conflict; excludes customer (`Bruviti`) lines.
- **Failure mode:** Decoy vendors with matching brand tokens but conflicting generics (e.g. `Northwind Logistics`) map to `unknown`.

### `app/extract/candidates.py`
- **What it does:** Generates candidate values for fields using spatial geometric relationships to label lexicons.
- **Algorithm worth knowing:** Tri-directional spatial search — tests (1) same line after label, (2) right-hand cell on same horizontal row, and (3) cell below label within $2.5 \times$ line height with horizontal coordinate overlap.
- **Failure mode:** Column headers in line-item tables (e.g. `Total`) are penalized if surrounded by item table headers (`Qty`, `Price`).

### `app/parsing/dates.py` & `app/extract/dates.py`
- **What it does:** Parses ambiguous dates and computes due dates from payment terms (`Net N`) under Rule O1.
- **Algorithm worth knowing:** Locale-guided disambiguation — resolves `03/09/2026` as day-first for UK/DE/JP/IN and month-first for US; applies terms addition (`inv_date + N days`) unless printed due date is present.
- **Failure mode:** Conflicting printed due date vs terms gives precedence to printed date with an explicit warning.

### `app/extract/amounts.py`
- **What it does:** Extracts subtotal, tax, and total with multi-tax summing and arithmetic constraint solving.
- **Algorithm worth knowing:** Tiered arithmetic solver — tests candidate triples against $|subtotal + tax - total| < 0.01$; if violated, preserves printed values without correction (Rule O2) and emits arithmetic warning.
- **Failure mode:** Percentage strings (e.g. `VAT 20%`) are explicitly stripped from amount candidate pools.

### `app/extract/confidence.py`
- **What it does:** Emits calibrated confidence probabilities in $[0.0, 1.0]$ for all 8 fields.
- **Algorithm worth knowing:** Feature-based calibration — boosts arithmetic-validated totals to $0.97$, caps unverified totals at $0.60$, penalizes ambiguous dates to $0.80$, assigns $0.0$ to nulls.
- **Failure mode:** Overconfident guessing on missing fields is prevented by strictly anchoring null confidences to $0.0$.

---

## 3. How to Read Evidence & Debug Mode (`?debug=1`)

Passing `?debug=1` (or `?debug=true`) to `POST /extract` reveals the internal extraction state:
```json
{
  "debug": {
    "timings_ms": { "reader": 4.1, "extraction": 7.3, "total": 11.4 },
    "document": { "page_count": 1, "line_count": 24, "is_invoice": true, "doc_type": "invoice" },
    "arithmetic": { "subtotal": 361.6, "tax": 72.32, "calculated_sum": 433.92, "printed_total": 433.92, "is_balanced": true },
    "provenance": { "vendor": "Northwind Traders", "invoice_number": "NW-1042", "total": 433.92 }
  }
}
```

---

## 4. How to Add a New Vendor or Label

### Adding a New Vendor:
1. Open `app/knowledge/vendors.py`.
2. Add an entry to `CANONICAL_VENDORS`:
   ```python
   "Acme Industrial": {
       "country": "United States",
       "currency": "USD",
       "date_order": "MDY",
       "brand_token": "acme",
       "generic_tokens": ["industrial", "corp", "inc"],
       "aliases": ["acme industrial llc", "acme industrial inc"],
   }
   ```
3. Run `pytest tests/test_doctype_and_vendor.py` to verify brand-gating.

### How to Add a New Label:
1. Open `app/knowledge/labels.py`.
2. Append the regex to the appropriate field list (`INVOICE_NUMBER_LABELS`, `TOTAL_LABELS`, etc.):
   ```python
   TOTAL_LABELS.append(r"\bfactura total\b")
   ```
3. Run `pytest -q` to verify non-regression.
