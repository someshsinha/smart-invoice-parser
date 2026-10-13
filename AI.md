# AI Usage Disclosure

## Tools Used
- **Tool:** Antigravity AI Coding Assistant / Gemini 3.8 Flash
- **Purpose:** Planning, implementation assistance, debugging, and test generation.

## How AI Was Used

| Area | AI assistance | My responsibility |
|---|---|---|
| Planning | Helped break down the assignment requirements and PRD into modular features | Reviewed priorities against the official assignment brief |
| Implementation | Suggested and generated code for geometry-aware PDF reading, parsing, extractors, and FastAPI endpoints | Reviewed every line of code, checked variable bindings, regexes, and coordinate math |
| Testing | Suggested pytest test cases for edge cases, date formats, and Rule O1–O5 compliance | Reviewed test intent, verified assertions, ran offline test suite, and investigated failures |
| Debugging | Interpreted regex edge cases, character encoding issues (TrueType glyphs), and test failures | Verified fixes by re-running targeted tests |
| Documentation | Helped draft documentation (README, DATA, NOTES, CODE_TOUR) | Checked all claims, numbers, and commands against the actual implementation |

## Verification
- **Test Command Executed:** `pytest -q`
  - Result: `50 passed in 0.52s` (100% pass rate, offline socket blocker active).
- **Evaluation Command Executed:** `python -m evaluation.run --dir samples`
  - Result: `100.00% exact match` across all 8 fields, `p50 latency = 10.4ms`.
- **Manual Checks Performed:**
  - Verified `GET /health` returns `200 {"status": "ok"}`.
  - Verified `POST /extract` handles multipart uploads, returns 400 on missing/non-PDF files, and parses sample PDFs.
  - Verified interactive single-page web UI at `http://localhost:8000/`.
- **Known Limitations:**
  - Scanned bitmap PDFs without a text layer are intentionally out of scope and return null fields with an informative warning.
  - Truly ambiguous numeric dates (e.g. `06/07/2026`) from unknown vendors rely on document fallback heuristics.

## Human Review
- Reviewed and verified directory structure, requirements, schemas, offline test fixtures, and endpoints.
- Read through all parsing logic, regexes, and geometry extraction functions to ensure full comprehension and defense capability during interview review.

## Limitations
AI-generated suggestions may contain mistakes. Code and tests were checked to the extent documented above. Passing tests demonstrate compliance on evaluated layouts, but variations on unseen layouts should be continually monitored in production.
