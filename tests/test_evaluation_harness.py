import pytest
from pathlib import Path
from evaluation.metrics import compute_evaluation_metrics, compare_field_values
from evaluation.failures import format_failure_dump
from evaluation.run import run_evaluation


def test_compare_field_values():
    # Null handling
    assert compare_field_values(None, None, "due_date") is True
    assert compare_field_values("2026-09-03", None, "due_date") is False
    assert compare_field_values(None, "2026-09-03", "due_date") is False

    # Amounts tolerance
    assert compare_field_values(361.60, 361.6, "subtotal") is True
    assert compare_field_values(361.60, 361.605, "subtotal") is True
    assert compare_field_values(361.60, 362.00, "subtotal") is False

    # Strings trim
    assert compare_field_values(" NW-1042 ", "NW-1042", "invoice_number") is True
    assert compare_field_values("NW-1042", "NW-1043", "invoice_number") is False


def test_compute_evaluation_metrics():
    preds = [
        {"vendor": "Northwind Traders", "total": 100.0, "invoice_number": "1"},
        {"vendor": "Kestrel Components", "total": 200.0, "invoice_number": "2"},
    ]
    gt = [
        {"vendor": "Northwind Traders", "total": 100.0, "invoice_number": "1"},
        {"vendor": "Kestrel Components", "total": 200.0, "invoice_number": "DIFFERENT"},
    ]

    metrics = compute_evaluation_metrics(preds, gt)
    assert metrics["total_documents"] == 2
    assert metrics["field_accuracy"]["vendor"] == 1.0
    assert metrics["field_accuracy"]["total"] == 1.0
    assert metrics["field_accuracy"]["invoice_number"] == 0.5


def test_failure_dump_formatting():
    preds = [{"vendor": "Northwind Traders", "invoice_number": "NW-WRONG"}]
    gt = [{"vendor": "Northwind Traders", "invoice_number": "NW-1042"}]

    dump = format_failure_dump(preds, gt, ["sample1.pdf"], max_failures=5)
    assert "sample1.pdf" in dump
    assert "invoice_number" in dump
    assert "NW-WRONG" in dump
    assert "NW-1042" in dump


def test_run_evaluation_on_samples_directory():
    samples_dir = Path(__file__).resolve().parent.parent / "samples"
    metrics = run_evaluation(samples_dir, show_failures=0)

    assert metrics["total_documents"] >= 4
    assert metrics["overall_accuracy"] == 1.0
    for field, acc in metrics["field_accuracy"].items():
        assert acc == 1.0, f"Field {field} did not achieve 100% on samples"


def test_compute_calibration_metrics():
    from evaluation.calibration import compute_calibration_metrics
    samples_dir = Path(__file__).resolve().parent.parent / "samples"
    brier, ece, bins = compute_calibration_metrics(samples_dir)
    assert 0.0 <= brier <= 1.0
    assert 0.0 <= ece <= 1.0
    assert len(bins) == 5

