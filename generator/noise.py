"""
Generator Noise Models (PRD §8.6).
Injects realistic variations: font families, coordinate jitter, and distractor reference numbers.
"""

import random
from typing import Dict, Any, List

DISTRACTOR_PATTERNS = [
    ("Purchase Order", "PO-{n}"),
    ("Order No", "ORD-{n}"),
    ("Customer Ref", "CUST-{n}"),
    ("VAT No", "GB {n} 4567 89"),
    ("GSTIN", "29AAAAA{n}A1Z5"),
    ("IBAN", "GB29 NWBK 6016 {n}"),
]

AVAILABLE_FONTS = ["DejaVuSans", "Helvetica", "Times-Roman", "Courier"]


def generate_distractors(rng: random.Random) -> List[str]:
    """Generates 1-3 distractor reference lines to stress-test extractor filtering."""
    distractors = []
    num_to_add = rng.randint(1, 3)
    sample = rng.sample(DISTRACTOR_PATTERNS, num_to_add)
    for lbl, template in sample:
        n = rng.randint(1000, 99999)
        distractors.append(f"{lbl}: {template.format(n=n)}")
    return distractors


def get_random_font(rng: random.Random) -> str:
    """Selects a font from the available safe font pool."""
    return rng.choice(AVAILABLE_FONTS)
