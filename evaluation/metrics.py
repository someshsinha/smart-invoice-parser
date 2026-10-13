"""
F17: Evaluation Metrics (Exact Match after Normalization).
Implements the official evaluation metric specified in Section 3 of the brief:
Exact match per field after normalisation:
- dates as ISO (YYYY-MM-DD)
- amounts to two decimals (float comparison within 0.01)
- vendor as canonical name (or 'unknown')
- strings trimmed exactly
- nullable fields: None == None is correct
"""

from typing import List, Dict, Any, Tuple
import math

FIELDS = [
    "vendor",
    "invoice_number",
    "invoice_date",
    "due_date",
    "currency",
    "subtotal",
    "tax",
    "total",
]


def compare_field_values(pred_val: Any, gt_val: Any, field_name: str) -> bool:
    """
    Compares predicted vs ground truth value under normalization rules.
    """
    # Both None -> exact match
    if pred_val is None and gt_val is None:
        return True
    if pred_val is None or gt_val is None:
        return False

    # Amounts: numeric comparison within 0.01 tolerance
    if field_name in ("subtotal", "tax", "total"):
        try:
            p_float = float(pred_val)
            g_float = float(gt_val)
            return abs(p_float - g_float) <= 0.01
        except (ValueError, TypeError):
            return False

    # Strings: exact comparison after trim
    return str(pred_val).strip() == str(gt_val).strip()


def compute_evaluation_metrics(
    predictions: List[Dict[str, Any]],
    ground_truths: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Computes exact-match metrics overall and per field, plus per-vendor breakdowns.
    Returns:
        {
            "total_documents": int,
            "overall_accuracy": float,
            "field_accuracy": {field: float},
            "vendor_breakdown": {vendor: {"total": int, "accuracy": float}},
        }
    """
    total_docs = len(predictions)
    if total_docs == 0:
        return {
            "total_documents": 0,
            "overall_accuracy": 0.0,
            "field_accuracy": {f: 0.0 for f in FIELDS},
            "vendor_breakdown": {},
        }

    field_correct_counts = {f: 0 for f in FIELDS}
    vendor_stats: Dict[str, Dict[str, int]] = {}

    for pred, gt in zip(predictions, ground_truths):
        gt_vendor = gt.get("vendor", "unknown")
        if gt_vendor not in vendor_stats:
            vendor_stats[gt_vendor] = {"correct_fields": 0, "total_fields": 0}

        for f in FIELDS:
            p_val = pred.get(f)
            g_val = gt.get(f)

            is_correct = compare_field_values(p_val, g_val, f)
            if is_correct:
                field_correct_counts[f] += 1
                vendor_stats[gt_vendor]["correct_fields"] += 1

            vendor_stats[gt_vendor]["total_fields"] += 1

    field_accuracy = {
        f: round(field_correct_counts[f] / total_docs, 4) for f in FIELDS
    }
    overall_accuracy = round(sum(field_accuracy.values()) / len(FIELDS), 4)

    vendor_breakdown = {}
    for v_name, stats in vendor_stats.items():
        tot = stats["total_fields"]
        corr = stats["correct_fields"]
        vendor_breakdown[v_name] = {
            "total_docs": tot // len(FIELDS),
            "accuracy": round(corr / tot, 4) if tot > 0 else 0.0,
        }

    return {
        "total_documents": total_docs,
        "overall_accuracy": overall_accuracy,
        "field_accuracy": field_accuracy,
        "vendor_breakdown": vendor_breakdown,
    }
