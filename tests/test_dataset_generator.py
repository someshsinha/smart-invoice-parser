import pytest
from pathlib import Path
import json
import random
from generator.make_dataset import generate_dataset_split, sample_invoice_data
from generator.noise import generate_distractors
from generator.vocab import sample_line_items
from app.pipeline import process_invoice_pdf


def test_vocab_and_noise_utilities():
    rng = random.Random(42)
    items = sample_line_items(rng, n=3)
    assert len(items) == 3
    for desc, price in items:
        assert isinstance(desc, str) and len(desc) > 0
        assert isinstance(price, float) and price > 0.0

    distractors = generate_distractors(rng)
    assert isinstance(distractors, list)
    assert len(distractors) > 0


def test_make_dataset_reproducibility():
    rng1 = random.Random(1234)
    data1 = sample_invoice_data(rng1)

    rng2 = random.Random(1234)
    data2 = sample_invoice_data(rng2)

    assert data1["ground_truth"] == data2["ground_truth"]
    assert data1["inv_num"] == data2["inv_num"]


def test_generate_dataset_split_execution(tmp_path: Path):
    generate_dataset_split("test_split", n_docs=4, seed=99, out_dir=tmp_path)

    pdf_files = sorted(list(tmp_path.glob("*.pdf")))
    json_files = sorted(list(tmp_path.glob("*.json")))

    assert len(pdf_files) == 4
    assert len(json_files) == 4

    for j_path in json_files:
        with open(j_path, "r", encoding="utf-8") as f:
            gt = json.load(f)
        for key in ["vendor", "invoice_number", "invoice_date", "due_date", "currency", "subtotal", "tax", "total", "warnings"]:
            assert key in gt

    # Ensure PDFs can be processed without runtime exceptions
    for p_path in pdf_files:
        pdf_bytes = p_path.read_bytes()
        response, _ = process_invoice_pdf(pdf_bytes)
        assert response.vendor is not None
        assert 0.0 <= response.confidence.vendor <= 1.0
