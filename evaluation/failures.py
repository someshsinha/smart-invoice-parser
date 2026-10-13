"""
F17: Failure Analysis and Error Dump.
Formats discrepancy tables between predictions and ground truths for failure triage.
"""

from typing import List, Dict, Any
from evaluation.metrics import FIELDS, compare_field_values


def format_failure_dump(
    predictions: List[Dict[str, Any]],
    ground_truths: List[Dict[str, Any]],
    file_identifiers: List[str],
    max_failures: int = 10,
) -> str:
    """
    Constructs a readable failure dump showing discrepancies.
    """
    lines = []
    lines.append("\n" + "=" * 70)
    lines.append("FAILURE TRIAGE & DISCREPANCY DUMP")
    lines.append("=" * 70)

    total_failures = 0
    failure_entries = []

    for file_id, pred, gt in zip(file_identifiers, predictions, ground_truths):
        doc_discrepancies = []
        for f in FIELDS:
            p_val = pred.get(f)
            g_val = gt.get(f)
            if not compare_field_values(p_val, g_val, f):
                doc_discrepancies.append((f, g_val, p_val))

        if doc_discrepancies:
            total_failures += 1
            if len(failure_entries) < max_failures:
                failure_entries.append((file_id, doc_discrepancies, pred.get("warnings", [])))

    if total_failures == 0:
        lines.append("Zero failures found! 100% exact match across all evaluated documents.")
        return "\n".join(lines)

    lines.append(f"Total documents with discrepancies: {total_failures} (showing first {len(failure_entries)})")
    lines.append("-" * 70)

    for file_id, discrepancies, warnings in failure_entries:
        lines.append(f"Document: {file_id}")
        for field, expected, got in discrepancies:
            lines.append(f"  ❌ {field:15}: Expected: {expected!r} | Got: {got!r}")
        if warnings:
            lines.append(f"  ⚠️ Warnings: {warnings}")
        lines.append("-" * 70)

    return "\n".join(lines)
