"""
F21: Confidence Calibration Analysis.
Calculates Brier score, Expected Calibration Error (ECE), and binned reliability diagrams.
Verifies that model confidence accurately mirrors empirical prediction accuracy.
"""

from typing import Dict, List, Any, Tuple
from pathlib import Path
import json
import argparse
from app.pipeline import process_invoice_pdf
from evaluation.metrics import compare_field_values

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


def compute_calibration_metrics(
    eval_dir: Path,
) -> Tuple[float, float, List[Dict[str, Any]]]:
    """
    Computes Brier Score, ECE, and binned calibration stats for all evaluated fields.
    """
    pdf_files = sorted(list(eval_dir.glob("*.pdf")))
    if not pdf_files:
        raise ValueError(f"No PDF files found in directory {eval_dir}")

    predictions: List[Tuple[float, int]] = []  # (confidence, is_correct)

    for pdf_path in pdf_files:
        json_path = pdf_path.with_suffix(".json")
        if not json_path.exists():
            continue

        with open(json_path, "r", encoding="utf-8") as f:
            gt = json.load(f)

        pdf_bytes = pdf_path.read_bytes()
        resp, _ = process_invoice_pdf(pdf_bytes)

        conf_dict = resp.confidence.model_dump()
        resp_dict = resp.model_dump()

        for field in FIELDS:
            gt_val = gt.get(field)
            pred_val = resp_dict.get(field)
            conf_val = conf_dict.get(field, 0.0)

            is_correct = 1 if compare_field_values(pred_val, gt_val, field) else 0
            predictions.append((conf_val, is_correct))

    total_n = len(predictions)
    if total_n == 0:
        return 0.0, 0.0, []

    # 1. Brier Score = (1/N) * sum((p - y)^2)
    brier_score = sum((p - y) ** 2 for p, y in predictions) / total_n

    # 2. Binned Reliability (5 bins: [0, 0.2), [0.2, 0.4), [0.4, 0.6), [0.6, 0.8), [0.8, 1.0])
    bin_edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0001]
    bins_data = []
    ece = 0.0

    for i in range(len(bin_edges) - 1):
        low, high = bin_edges[i], bin_edges[i + 1]
        bin_preds = [item for item in predictions if low <= item[0] < high]
        bin_count = len(bin_preds)

        if bin_count > 0:
            avg_conf = sum(p for p, _ in bin_preds) / bin_count
            avg_acc = sum(y for _, y in bin_preds) / bin_count
            gap = abs(avg_acc - avg_conf)
            ece += (bin_count / total_n) * gap
        else:
            avg_conf = 0.0
            avg_acc = 0.0
            gap = 0.0

        bins_data.append({
            "bin_range": f"[{low:.1f}, {min(1.0, high):.1f})",
            "count": bin_count,
            "avg_confidence": avg_conf,
            "accuracy": avg_acc,
            "gap": gap,
        })

    return brier_score, ece, bins_data


def print_calibration_report(
    eval_dir: Path, brier: float, ece: float, bins: List[Dict[str, Any]]
):
    print("\n" + "=" * 70)
    print("CONFIDENCE CALIBRATION & RELIABILITY REPORT")
    print("=" * 70)
    print(f"Evaluated Directory           : {eval_dir}")
    print(f"Overall Brier Score (MSE)     : {brier:.4f}  (Optimal: 0.0000)")
    print(f"Expected Calibration Error    : {ece*100:.2f}%")
    print("-" * 70)
    print(f"{'Confidence Bin':<16} | {'Count':<6} | {'Avg Conf':<10} | {'Empirical Acc':<14} | {'Gap'}")
    print("-" * 70)
    for b in bins:
        if b["count"] > 0:
            print(
                f"{b['bin_range']:<16} | {b['count']:<6} | {b['avg_confidence']*100:>7.2f}%   | "
                f"{b['accuracy']*100:>11.2f}%   | {b['gap']*100:>5.2f}%"
            )
        else:
            print(f"{b['bin_range']:<16} | {0:<6} | {'N/A':<10} | {'N/A':<14} | N/A")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Evaluate model confidence calibration")
    parser.add_argument("--dir", type=str, default="data/dev", help="Directory with PDF and JSON pairs")
    args = parser.parse_args()

    eval_dir = Path(args.dir)
    brier, ece, bins = compute_calibration_metrics(eval_dir)
    print_calibration_report(eval_dir, brier, ece, bins)


if __name__ == "__main__":
    main()
