"""
F17: Evaluation Runner CLI.
Runs the real pipeline in-process over a set of PDFs, measures exact-match accuracy
and latency, and prints formatted evaluation tables.
"""

import argparse
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from app.pipeline import process_invoice_pdf
from evaluation.metrics import compute_evaluation_metrics, FIELDS
from evaluation.failures import format_failure_dump


def run_evaluation(
    eval_dir: Path,
    show_failures: int = 10,
) -> Dict[str, Any]:
    """
    Evaluates all PDF/JSON pairs in eval_dir against the pipeline.
    """
    if not eval_dir.exists():
        raise FileNotFoundError(f"Evaluation directory not found: {eval_dir}")

    pdf_files = sorted(list(eval_dir.glob("*.pdf")))
    if not pdf_files:
        raise ValueError(f"No PDF files found in {eval_dir}")

    predictions: List[Dict[str, Any]] = []
    ground_truths: List[Dict[str, Any]] = []
    file_identifiers: List[str] = []
    latencies: List[float] = []

    print(f"\nEvaluating {len(pdf_files)} documents from {eval_dir}...")

    for pdf_path in pdf_files:
        json_path = pdf_path.with_suffix(".json")
        if not json_path.exists():
            continue

        gt_data = json.loads(json_path.read_text(encoding="utf-8"))
        pdf_bytes = pdf_path.read_bytes()

        # Measure in-process pipeline request latency
        start_time = time.perf_counter()
        response, _ = process_invoice_pdf(pdf_bytes)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        latencies.append(duration_ms)
        pred_dict = response.model_dump(exclude_none=False)

        predictions.append(pred_dict)
        ground_truths.append(gt_data)
        file_identifiers.append(pdf_path.name)

    # Compute Metrics
    metrics = compute_evaluation_metrics(predictions, ground_truths)

    # Compute Latency Percentiles
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p_max = max(latencies)

    # Print Formatted Results
    print("\n" + "=" * 70)
    print("INVOICE EXTRACTION EVALUATION REPORT (EXACT MATCH)")
    print("=" * 70)
    print(f"Total Documents Evaluated : {metrics['total_documents']}")
    print(f"Overall Exact Match Score : {metrics['overall_accuracy'] * 100:.2f}%")
    print(f"Latency Percentiles (CPU) : p50 = {p50:.1f}ms | p95 = {p95:.1f}ms | max = {p_max:.1f}ms")
    print("-" * 70)
    print(f"{'Field':<18} | {'Exact Match Accuracy':<22}")
    print("-" * 70)
    for field in FIELDS:
        acc = metrics["field_accuracy"][field]
        bar = "█" * int(acc * 20)
        print(f"{field:<18} | {acc * 100:>6.2f}%  {bar}")
    print("-" * 70)

    print("\nPER-VENDOR BREAKDOWN:")
    print("-" * 70)
    print(f"{'Vendor':<28} | {'Docs':<6} | {'Accuracy':<10}")
    print("-" * 70)
    for v_name, v_stat in metrics["vendor_breakdown"].items():
        print(f"{v_name:<28} | {v_stat['total_docs']:<6} | {v_stat['accuracy'] * 100:>6.2f}%")
    print("=" * 70)

    # Failure Dump
    if show_failures > 0:
        failure_dump = format_failure_dump(predictions, ground_truths, file_identifiers, max_failures=show_failures)
        print(failure_dump)

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Invoice Field Extraction Evaluation Harness")
    parser.add_argument("--dir", type=str, default="samples", help="Path to evaluation directory with PDF and JSON files")
    parser.add_argument("--split", type=str, default=None, help="Split name (dev, val, heldout)")
    parser.add_argument("--show-failures", type=int, default=10, help="Max failure discrepancies to display")
    args = parser.parse_args()

    eval_dir = Path(f"data/{args.split}") if args.split else Path(args.dir)
    run_evaluation(eval_dir, show_failures=args.show_failures)


if __name__ == "__main__":
    main()
