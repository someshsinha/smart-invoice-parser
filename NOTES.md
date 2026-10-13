# NOTES.md: Architectural Decisions, Trade-offs, and Cuts

## 1. Core Architectural Approach: Rules + Geometry + Constraint Solving
We deliberately selected a deterministic rules-and-geometry approach with exact constraint solving over machine learning or deep neural networks for the following reasons:
1. **Strict Offline Requirement (C1):** Zero network connectivity allowed at runtime.
2. **Sub-Second Latency (C2):** Processing completes in < 300 ms on a standard laptop CPU without GPU acceleration.
3. **Zero Pre-supplied Training Data (C11):** Complex neural models overfit synthetic distributions; deterministic geometric heuristics generalize across unseen layouts.
4. **Explainability & Verification:** Every extracted field carries clear geometric and lexical provenance, enabling rapid debugging and total interview transparency.

## 2. Key Decisions & Tie-Breaking Logic
- **Geometry-Aware Token Grouping:** Words are clustered into lines by vertical coordinate proximity and partitioned into cells where horizontal space exceeds 1.5x median character width. This handles multi-field inline rows (`Reference # KC-0311 Dated 9/3/26`).
- **Vendor Brand Token Gating:** A candidate matches a canonical vendor only if its distinctive brand token matches within 2 edit distances AND generic words either match or are absent. Conflicting generic words (e.g. `Northwind Logistics`) map to `unknown` to prevent false positives.
- **Ambiguous Date Disambiguation (Appendix M):** Ambiguous numeric dates (`03/09/2026`) are resolved using the vendor's country (UK, DE, JP, IN -> day-first; US -> month-first) and flagged with a descriptive warning.
- **Arithmetic Constraint Solving (Rule O2):** Subtotal, tax, and total candidates are jointly evaluated against $subtotal + tax = total$. If no combination matches within 0.01 tolerance, printed values are returned unmodified along with an arithmetic mismatch warning.
- **Document Type Classification (Rule O4):** Documents identified as quotations, delivery notes, purchase orders, or account statements immediately short-circuit to return `null` for all extraction fields with an informative warning.

## 3. What Was Cut and Why
- **Heavy Neural Sentence Embeddings:** Dropped to eliminate startup warmup latency, dependency bloat, and avoid exceeding file-size constraints.
- **Machine Learning Re-Ranker (P2):** Dropped in favor of transparent rule scoring; logistic regression re-rankers offered marginal gains on synthetic data while increasing risk of layout distribution shift.
- **Japanese Character OCR / Kanji Lexicons (P2):** Invoices with Japanese Kanji headers are evaluated via normalized text when present, but full CJK font embedding in ReportLab was restricted to keep repository size lean (< 5 MB).

## 4. Future Enhancements
- Support for multi-lingual OCR pipelines (e.g., Tesseract or lightweight ONNX models) for scanned or faxed documents.
- Interactive user feedback loop for active learning and lexicon refinement on real-world edge cases.
