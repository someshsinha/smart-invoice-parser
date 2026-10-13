"""
F2: Unicode NFKC normalization, whitespace collapse, punctuation unification.
"""

import unicodedata
import re

def normalize_text(text: str) -> str:
    """Applies NFKC normalization and collapses excessive whitespace."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    # Unify dashes and minus signs
    normalized = re.sub(r"[\u2212\u2013\u2014]", "-", normalized)
    # Collapse multiple whitespaces
    normalized = re.sub(r"[ \t\u00a0]+", " ", normalized)
    return normalized.strip()
