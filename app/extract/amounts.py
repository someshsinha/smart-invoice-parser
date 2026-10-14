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
    line_item_candidates: List[AmountCandidate] = []

    warnings: List[str] = []

    metadata_labels = (
        LABELS["invoice_date"] + LABELS["due_date"] + LABELS["terms"] +
        LABELS["invoice_number"] + LABELS["exclude_invoice_number"] + LABELS["customer_block_markers"]
    )

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

            # 1. Check Subtotal (Tier 1 explicit labels)
            matched_subtotal = False
            for lbl in LABELS["subtotal"]:
                end_b = r"\b" if lbl[-1].isalnum() else r"(?=[^a-zA-Z0-9]|$)"
                m = re.search(rf"\b{re.escape(lbl)}{end_b}", line_lower)
                if m:
                    val, raw_tok = _extract_amount_after_label(line, m.end(), decimal_hint)
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
                        matched_subtotal = True
                        break

            # 2. Check Tax / VAT / GST
            matched_tax = False
            if not matched_subtotal:
                for lbl in LABELS["tax"]:
                    end_b = r"\b" if lbl[-1].isalnum() else r"(?=[^a-zA-Z0-9]|$)"
                    m = re.search(rf"\b{re.escape(lbl)}{end_b}", line_lower)
                    if m:
                        val, raw_tok = _extract_amount_after_label(line, m.end(), decimal_hint)
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
                            matched_tax = True
                            break

            # 3. Check Total (Tiered matching)
            matched_total = False
            if not matched_subtotal and not matched_tax:
                is_t1 = any(re.search(rf"\b{re.escape(lbl)}\b", line_lower) for lbl in LABELS["total_t1"])
                is_t2 = any(re.search(rf"\b{re.escape(lbl)}\b", line_lower) for lbl in LABELS["total_t2"])
                is_t3 = any(re.search(rf"\b{re.escape(lbl)}\b", line_lower) for lbl in LABELS["total_t3"])

                if is_t1 or is_t2 or is_t3:
                    tier = 1 if is_t1 else (2 if is_t2 else 3)
                    base_score = 0.95 if is_t1 else (0.90 if is_t2 else 0.82)
                    lbl_matched = None
                    for t_list in [LABELS["total_t1"], LABELS["total_t2"], LABELS["total_t3"]]:
                        for lbl in t_list:
                            end_b = r"\b" if lbl[-1].isalnum() else r"(?=[^a-zA-Z0-9]|$)"
                            m = re.search(rf"\b{re.escape(lbl)}{end_b}", line_lower)
                            if m:
                                lbl_matched = m
                                break
                        if lbl_matched:
                            break

                    if lbl_matched:
                        val, raw_tok = _extract_amount_after_label(line, lbl_matched.end(), decimal_hint)
                    else:
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
                        matched_total = True

            # 4. Check potential body line item
            if not matched_subtotal and not matched_tax and not matched_total:
                is_meta = any(re.search(rf"\b{re.escape(lbl)}\b", line_lower) for lbl in metadata_labels)
                if not is_meta:
                    val, raw_tok = _extract_amount_from_line(line, decimal_hint)
                    if val is not None:
                        line_item_candidates.append(
                            AmountCandidate(
                                field="subtotal",
                                value=val,
                                raw_text=raw_tok,
                                label_text=line_text,
                                tier=3,
                                score=0.75,
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

    # If no explicit subtotal label was found, consider body line items (and their sum) as Tier 3 candidates
    all_subtotal_candidates = list(subtotal_candidates)
    if not subtotal_candidates and line_item_candidates:
        all_subtotal_candidates.extend(line_item_candidates)
        if len(line_item_candidates) > 1:
            line_item_sum = round(sum(c.value for c in line_item_candidates), 2)
            all_subtotal_candidates.append(
                AmountCandidate(
                    field="subtotal",
                    value=line_item_sum,
                    raw_text="summed_items",
                    label_text="Sum of line items",
                    tier=3,
                    score=0.78,
                    line_y0=line_item_candidates[0].line_y0,
                    page_idx=line_item_candidates[0].page_idx,
                )
            )

    # 4. Arithmetic Constraint Solver (Rule O2)
    # Search for (subtotal, tax, total) combinations satisfying: abs(s + t - tot) <= 0.01
    best_triple = None
    best_triple_score = -1.0

    # Sort candidates by tier and score
    all_subtotal_candidates.sort(key=lambda c: (c.tier, -c.score))
    tax_candidates.sort(key=lambda c: (c.tier, -c.score))
    total_candidates.sort(key=lambda c: (c.tier, -c.score))

    if tax_candidates:
        for s_cand in all_subtotal_candidates[:6]:
            for t_cand in tax_candidates[:4]:
                for tot_cand in total_candidates[:4]:
                    diff = abs((s_cand.value + t_cand.value) - tot_cand.value)
                    if diff <= ARITHMETIC_TOLERANCE:
                        triple_score = s_cand.score + t_cand.score + tot_cand.score + (1.0 / tot_cand.tier) + (1.0 / s_cand.tier)
                        if triple_score > best_triple_score:
                            best_triple_score = triple_score
                            best_triple = (s_cand, t_cand, tot_cand)
    else:
        # No tax printed: test pairs where subtotal == total
        for s_cand in all_subtotal_candidates[:6]:
            for tot_cand in total_candidates[:4]:
                diff = abs(s_cand.value - tot_cand.value)
                if diff <= ARITHMETIC_TOLERANCE:
                    triple_score = s_cand.score + tot_cand.score + (1.0 / tot_cand.tier) + (1.0 / s_cand.tier)
                    if triple_score > best_triple_score:
                        best_triple_score = triple_score
                        best_triple = (s_cand, None, tot_cand)

    # If consistent triple found -> choose it and calibrate confidence
    if best_triple is not None:
        s_res, t_res, tot_res = best_triple
        t_val = t_res.value if t_res else None
        t_conf = 0.97 if t_res else 0.0
        # If subtotal came from line items verified by arithmetic, confidence is calibrated to 0.94
        s_conf = 0.97 if s_res.tier == 1 else 0.94
        return (
            s_res.value, s_conf,
            t_val, t_conf,
            tot_res.value, 0.97,
            warnings,
        )

    # If no triple is consistent within 0.01 (Rule O2)
    # Only return subtotal candidate if it came from an explicit Tier 1 label!
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


def _extract_amount_after_label(line: TextLine, end_idx: int, decimal_hint: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    """
    Extracts the monetary amount appearing after a label on a line.
    Prefers the right-most non-percentage numeric cell/token that appears after the label.
    """
    after_text = line.text[end_idx:].strip()
    after_text = re.sub(r"^[:\-=\s]+", "", after_text).strip()
    if not after_text:
        return None, None

    words = after_text.split()
    for i in range(len(words) - 1, -1, -1):
        w = words[i]
        if is_percentage_token(w):
            continue
        amt = parse_money_amount(w, decimal_separator_hint=decimal_hint)
        if amt is not None:
            return amt, w
        if i > 0:
            combo = f"{words[i-1]} {w}"
            amt_combo = parse_money_amount(combo, decimal_separator_hint=decimal_hint)
            if amt_combo is not None and not is_percentage_token(combo):
                return amt_combo, combo

    return None, None


def _extract_amount_from_line(line: TextLine, decimal_hint: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    """
    Extracts the monetary amount from a line.
    Prefers the right-most non-percentage numeric cell/token.
    """
    words = line.text.split()
    for i in range(len(words) - 1, -1, -1):
        w = words[i]
        if is_percentage_token(w):
            continue
        amt = parse_money_amount(w, decimal_separator_hint=decimal_hint)
        if amt is not None:
            return amt, w
        if i > 0:
            combo = f"{words[i-1]} {w}"
            amt_combo = parse_money_amount(combo, decimal_separator_hint=decimal_hint)
            if amt_combo is not None and not is_percentage_token(combo):
                return amt_combo, combo

    return None, None
