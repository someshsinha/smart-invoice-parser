"""
F11: Amount Extractor with Arithmetic Constraint Solving (Rule O2 & Rule O5).
Extracts subtotal, tax, and total candidates using geometry and tiered labels,
tests candidate combinations against subtotal + tax == total,
and enforces Rule O2 error reporting without modifying printed numbers.
"""

from typing import Tuple, Optional, List, Dict
import re
from dataclasses import dataclass
from app.reader.pdf_text import ParsedDocument, TextLine
from app.knowledge.vendors import CANONICAL_VENDORS
from app.knowledge.labels import LABELS
from app.parsing.amounts import parse_money_amount, is_percentage_token
from app.extract.warnings import warn_arithmetic_mismatch
from app.config import ARITHMETIC_TOLERANCE


@dataclass
class AmountCandidate:
    field: str
    value: float
    raw_text: str
    label_text: str
    tier: int  # 1 (strongest) to 4
    score: float
    line_y0: float
    page_idx: int


def extract_amounts(
    doc: ParsedDocument,
    vendor_name: str,
) -> Tuple[Optional[float], float, Optional[float], float, Optional[float], float, List[str]]:
    """
    Extracts subtotal, tax, and total, solving the arithmetic constraint (Rule O2).
    Returns:
        (subtotal, subtotal_conf, tax, tax_conf, total, total_conf, warnings)
    """
    if not doc.pages or not doc.has_text:
        return None, 0.0, None, 0.0, None, 0.0, []

    vendor_meta = CANONICAL_VENDORS.get(vendor_name, {})
    decimal_hint = vendor_meta.get("decimal_style") or ("." if vendor_name != "Meridian Industrial" else ",")

    subtotal_candidates: List[AmountCandidate] = []
    tax_candidates: List[AmountCandidate] = []
    total_candidates: List[AmountCandidate] = []

    warnings: List[str] = []

    # Process all pages (totals are typically on the last page or page 1)
    for page in doc.pages:
        # Detect table column headers to exclude (e.g. "Particulars   Total" or "Item Qty Price Amount")
        column_header_y_ranges = []
        for line in page.lines:
            line_lower = line.text.lower()
            header_tokens = [t for t in ["item", "qty", "quantity", "particulars", "description", "unit price"] if t in line_lower]
            if len(header_tokens) >= 2 or ("particulars" in line_lower and "total" in line_lower):
                column_header_y_ranges.append((line.y0 - 2.0, line.y1 + 2.0))

        for line in page.lines:
            line_text = line.text
            line_lower = line_text.lower()

            # Skip table column header lines
            if any(y0 <= line.y0 <= y1 for y0, y1 in column_header_y_ranges):
                continue

            # Skip header metadata lines (invoice date, due date, invoice no)
            if any(re.search(rf"\b{lbl}\b", line_lower) for lbl in LABELS["invoice_date"] + LABELS["due_date"] + LABELS["invoice_number"]):
                # Unless the line explicitly contains total / subtotal
                if not any(re.search(rf"\b{lbl}\b", line_lower) for lbl in ["subtotal", "sub total", "total", "balance due", "amount due"]):
                    continue

            # 1. Check Subtotal
            if any(re.search(rf"\b{lbl}\b", line_lower) for lbl in LABELS["subtotal"]):
                # Don't match if it's "total excl" or similar unless it doesn't match total
                val, raw_tok = _extract_amount_from_line(line, decimal_hint)
                if val is not None:
                    subtotal_candidates.append(
                        AmountCandidate(
                            field="subtotal",
                            value=val,
                            raw_text=raw_tok,
                            label_text=line_text,
                            tier=1,
                            score=0.92,
                            line_y0=line.y0,
                            page_idx=page.page_idx,
                        )
                    )

            # 2. Check Tax / VAT / GST
            if any(re.search(rf"\b{lbl}\b", line_lower) for lbl in LABELS["tax"]):
                # Ensure not a subtotal line like "Total excl VAT"
                if not any(re.search(rf"\b{lbl}\b", line_lower) for lbl in LABELS["subtotal"]):
                    val, raw_tok = _extract_amount_from_line(line, decimal_hint)
                    if val is not None:
                        tax_candidates.append(
                            AmountCandidate(
                                field="tax",
                                value=val,
                                raw_text=raw_tok,
                                label_text=line_text,
                                tier=1,
                                score=0.92,
                                line_y0=line.y0,
                                page_idx=page.page_idx,
                            )
                        )

            # 3. Check Total (Tiered matching)
            # Tier 1: amount due, balance due, total due, amount payable, total payable, zu zahlen
            is_t1 = any(re.search(rf"\b{lbl}\b", line_lower) for lbl in LABELS["total_t1"])
            # Tier 2: grand total, invoice total, total incl, gesamtbetrag, rechnungsbetrag
            is_t2 = any(re.search(rf"\b{lbl}\b", line_lower) for lbl in LABELS["total_t2"])
            # Tier 3: bare total
            is_t3 = any(re.search(rf"\b{lbl}\b", line_lower) for lbl in LABELS["total_t3"]) and not any(re.search(rf"\b{lbl}\b", line_lower) for lbl in LABELS["subtotal"])

            if is_t1 or is_t2 or is_t3:
                tier = 1 if is_t1 else (2 if is_t2 else 3)
                base_score = 0.95 if is_t1 else (0.90 if is_t2 else 0.82)
                val, raw_tok = _extract_amount_from_line(line, decimal_hint)
                if val is not None:
                    total_candidates.append(
                        AmountCandidate(
                            field="total",
                            value=val,
                            raw_text=raw_tok,
                            label_text=line_text,
                            tier=tier,
                            score=base_score,
                            line_y0=line.y0,
                            page_idx=page.page_idx,
                        )
                    )

    # Handle multiple tax lines (e.g. CGST + SGST or multi-rate VAT)
    if len(tax_candidates) > 1:
        summed_tax = round(sum(c.value for c in tax_candidates), 2)
        # Add combined tax candidate
        tax_candidates.append(
            AmountCandidate(
                field="tax",
                value=summed_tax,
                raw_text="summed_taxes",
                label_text="Multiple tax components sum",
                tier=1,
                score=0.90,
                line_y0=tax_candidates[0].line_y0,
                page_idx=tax_candidates[0].page_idx,
            )
        )

    # 4. Arithmetic Constraint Solver (Rule O2)
    # Search for (subtotal, tax, total) triples satisfying: abs(s + t - tot) <= 0.01
    best_triple = None
    best_triple_score = -1.0

    # Sort candidates by tier and score
    subtotal_candidates.sort(key=lambda c: (c.tier, -c.score))
    tax_candidates.sort(key=lambda c: (c.tier, -c.score))
    total_candidates.sort(key=lambda c: (c.tier, -c.score))

    for s_cand in subtotal_candidates[:4]:
        for t_cand in tax_candidates[:4]:
            for tot_cand in total_candidates[:4]:
                diff = abs((s_cand.value + t_cand.value) - tot_cand.value)
                if diff <= ARITHMETIC_TOLERANCE:
                    triple_score = s_cand.score + t_cand.score + tot_cand.score + (1.0 / (tot_cand.tier))
                    if triple_score > best_triple_score:
                        best_triple_score = triple_score
                        best_triple = (s_cand, t_cand, tot_cand)

    # If consistent triple found -> choose it and boost confidence
    if best_triple is not None:
        s_res, t_res, tot_res = best_triple
        return (
            s_res.value, 0.97,
            t_res.value, 0.97,
            tot_res.value, 0.97,
            warnings,
        )

    # If no triple is consistent within 0.01 (Rule O2)
    # Return best individual candidates based on labels, and add warning
    s_val = subtotal_candidates[0].value if subtotal_candidates else None
    s_conf = subtotal_candidates[0].score if subtotal_candidates else 0.0

    t_val = tax_candidates[0].value if tax_candidates else None
    t_conf = tax_candidates[0].score if tax_candidates else 0.0

    tot_val = total_candidates[0].value if total_candidates else None
    tot_conf = total_candidates[0].score if total_candidates else 0.0

    # Check if all three exist but arithmetic failed (Rule O2 condition)
    if s_val is not None and t_val is not None and tot_val is not None:
        diff = abs((s_val + t_val) - tot_val)
        if diff > ARITHMETIC_TOLERANCE:
            # Rule O2: Return printed values and add warning; do not fix arithmetic!
            warnings.append(warn_arithmetic_mismatch(s_val, t_val, tot_val))
            # Cap confidence at 0.60 per PRD §13
            s_conf = min(s_conf, 0.60)
            t_conf = min(t_conf, 0.60)
            tot_conf = min(tot_conf, 0.60)

    return s_val, s_conf, t_val, t_conf, tot_val, tot_conf, warnings


def _extract_amount_from_line(line: TextLine, decimal_hint: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    """
    Extracts the monetary amount from a line.
    Prefers the right-most non-percentage numeric cell/token.
    """
    # First inspect cells from right to left
    for cell in reversed(line.cells):
        words = cell.text.split()
        for i in range(len(words) - 1, -1, -1):
            w = words[i]
            if is_percentage_token(w):
                continue
            amt = parse_money_amount(w, decimal_separator_hint=decimal_hint)
            if amt is not None:
                return amt, w
            # Check combined with previous word (e.g. "GBP 433.92" or "$ 242.17")
            if i > 0:
                combo = f"{words[i-1]} {w}"
                amt_combo = parse_money_amount(combo, decimal_separator_hint=decimal_hint)
                if amt_combo is not None and not is_percentage_token(combo):
                    return amt_combo, combo

    return None, None
