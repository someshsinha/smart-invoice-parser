# DATA.md: Data Sourcing, Synthetic Generation & Test Strategy

## 1. Data Sources
The assignment brief provides zero external training or testing datasets, supplying only:
- Reference vendor tables (Appendix M: 6 canonical vendors with associated countries and currencies).
- Two text-based example invoices (Appendix N: Northwind Traders and Kestrel Components).

To rigorously evaluate generalisation without memorisation or data leakage, all training and evaluation data is synthetically produced using a custom programmatic generator (`generator/`) built with ReportLab.

### Fonts & Licences
- Bundled font: DejaVu Sans (free licence, Bitstream Vera derivative) to support symbols including Rupee (`₹`), Euro (`€`), Pound (`£`), and Yen (`¥`).

---

## 2. Generator Design & Invoice Model
The synthetic invoice generator simulates real-world supplier invoice heterogeneity:
1. **Canonical & Decoy Vendors:**
   - 6 canonical vendors rendered with varied legal suffixes (`Ltd`, `Inc`, `GmbH`, `KK`, `Pvt Ltd`), letter casing, British vs. American spelling (`Harbour` vs `Harbor`), and typos (1-2 edits).
   - Brand-only letterheads (e.g. `NORTHWIND LTD`).
   - Two decoy classes: (a) different brand with same generic word (e.g. `Pinewood Packaging Ltd`), and (b) same brand with conflicting generic word (e.g. `Northwind Logistics`). Both are labelled as `unknown`.
2. **Layout Families:**
   - Diverse geometric structures including classic UK letterhead, inline US blocks, multi-column meta tables, German DIN-5008 layouts, Japanese year-first layouts, and Indian GST layouts with multi-tax splits (CGST + SGST).
3. **Disjoint Lexicon Pools (`dev` vs `test`):**
   - Field label synonyms are partitioned into disjoint pools (`dev` and `test`) to guarantee that evaluation against held-out splits measures genuine generalization rather than keyword memorization.
4. **Noise Simulation:**
   - Shuffled drawing orders, fragmented text elements, variable spacing, watermarks (`PAID`), and distractor reference numbers (PO, IBAN, VAT/GSTIN).
5. **Ground Truth Derivation:**
   - Generated directly from structured invoice objects prior to PDF compilation to ensure 100% exact ground truth.

---

## 3. Dataset Splits
- `dev`: Layout families L1 to L8 with `dev` label pool (used for iterative algorithm design).
- `val`: Fresh seeds across L1 to L8 for threshold calibration.
- `heldout`: Unseen layout families (L9 to L12) and unseen `test` label pool (evaluated only for final benchmarking).

---

## 4. What We Expect to Break on Real Data
- **Scanned or bitmap images:** Invoices without a selectable text layer (per the problem brief, scanned/handwritten documents are out of scope).
- **Corrupt font encodings:** PDFs with missing or non-standard `ToUnicode` CMaps where glyphs decode into incorrect characters.
- **Complex multi-currency items:** Invoices listing conversion rates and line items in multiple currencies simultaneously.
- **Ambiguous dates without country context:** Unknown vendors with dates like `06/07/2026` where neither invoice nor vendor indicates nationality.
- **Rotated or vertical text tables:** Invoices with vertically oriented totals or table columns.
