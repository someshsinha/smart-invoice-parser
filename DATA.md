# DATA.md: Data Sourcing, Synthetic Modeling & Test Strategy

## 1. Data Sources
The assignment brief provides zero external training or testing datasets, providing only:
- Reference vendor tables (Appendix M: 6 canonical vendors with associated countries and currencies).
- Two text-based example invoices (Appendix N: Northwind Traders and Kestrel Components).

To rigorously evaluate generalisation without memorisation or data leakage, all test documents are programmatically produced using ReportLab in `generator/build_samples.py`.

### Bundled Font & Licences
- **DejaVu Sans TrueType Font** (`generator/fonts/DejaVuSans.ttf`, 742 KB):
  - Permissive licence (Bitstream Vera derivative).
  - Bundled to guarantee full Unicode glyph rendering and extraction fidelity for international currency symbols, including Indian Rupee (`₹`), Euro (`€`), British Pound (`£`), and Japanese Yen (`¥`), avoiding Type-1 font glyph substitution bugs.

---

## 2. Generator Design & Invoice Model
The synthetic invoice generator simulates supplier invoice variation:
1. **Canonical & Decoy Vendors:**
   - Canonical vendors: Northwind Traders (UK), Blue Harbour Logistics (UK), Kestrel Components (US), Meridian Industrial (DE), Sakura Precision (JP), and Pinecrest Packaging (IN).
   - Rendered with varied legal suffixes (`Ltd`, `Inc`, `GmbH`, `KK`, `Pvt Ltd`), casing variations, British vs. American spellings (`Harbour` vs `Harbor`), and address metadata.
   - Two decoy classes:
     - (a) *Different brand with same generic company word* (e.g. `Pinewood Packaging Ltd`) $\rightarrow$ labelled as `unknown`.
     - (b) *Same brand token with conflicting generic company word* (e.g. `Northwind Logistics`) $\rightarrow$ labelled as `unknown` with a resemblance warning.
   - Brand-only letterheads (e.g. `NORTHWIND LTD`) $\rightarrow$ mapped to canonical name with brand-only warning.
2. **Layout Families:**
   - Classic UK letterhead with right-aligned totals (`northwind_1042.pdf`).
   - US inline layout with multi-field horizontal lines (`Reference # KC-0311 Dated 9/3/26`) and column header traps (`kestrel_0311.pdf`).
   - German DIN format with dot dates and comma decimals (`meridian_german.pdf`).
   - Unknown vendor with INR currency and absence of payment terms (`unknown_vendor.pdf`).
3. **Paired Ground Truth Derivation:**
   - Each generated PDF has a companion `.json` file containing the exact expected 8 fields, derived directly from the underlying structured data model prior to PDF canvas drawing.

---

## 3. Benchmark Results (Canonical Sample Fixtures)

Evaluated via `python -m evaluation.run --dir samples`:

```text
Total Documents Evaluated : 4
Overall Exact Match Score : 100.00%
Latency Percentiles (CPU) : p50 = 12.7ms | p95 = 30.4ms | max = 30.4ms

Field              | Exact Match Accuracy
vendor             | 100.00%
invoice_number     | 100.00%
invoice_date       | 100.00%
due_date           | 100.00%
currency           | 100.00%
subtotal           | 100.00%
tax                | 100.00%
total              | 100.00%
```

*(Note: While these scores achieve 100% on the canonical examples, performance on unseen hidden invoices from diverse real-world vendors will naturally encounter edge cases. The service is built with conservative fallback rules and diagnostic warnings to gracefully surface ambiguities rather than fail silently.)*

---

## 4. What We Expect to Break on Real Data
In production environments with real-world supplier documents, we expect the following edge cases to challenge extraction:
1. **Scanned Bitmaps & Image PDFs:** Invoices scanned from paper without a text layer. (Per the problem brief, scanned/handwritten documents are out of scope; our service safely detects this and returns HTTP 200 with all nulls and a descriptive warning).
2. **Missing or Corrupt `ToUnicode` CMaps:** PDFs using custom embedded fonts where characters render visually on screen but extract as arbitrary unicode codepoints or private-use areas.
3. **Ambiguous Dates from Unknown Vendors:** Numeric dates such as `06/07/2026` from suppliers not present in the canonical vendor list, where neither address nor currency indicates national origin.
4. **Multi-Currency Invoices:** Invoices that list foreign line items and convert to a domestic payment currency on the same page.
5. **Complex Multi-Tier Deposits / Retainers:** Complex balance sheets where line items, previous deposits, early payment discounts, and freight fees produce multiple competing "total" amounts.
6. **Rotated Text & Diagonal Watermarks:** Total amounts rendered vertically or rotated along table borders.

---

## 5. Test Design Rationale
- **Offline Network Isolation:** Tests enforce zero network calls using an automated pytest socket blocker (`tests/conftest.py`).
- **Appendix O Business Rules Verification:** Every rule (O1 terms precedence, O2 arithmetic preservation, O3 currency fallback, O4 non-invoice short-circuit, O5 JPY `.00`) has dedicated automated regression tests.
- **Trap Avoidance:** Automated tests verify that table column headers (`Particulars Total`) are never chosen as the invoice total, and customer names (`Bruviti`) are never chosen as the vendor.
