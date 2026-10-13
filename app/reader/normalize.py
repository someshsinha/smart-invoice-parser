"""
Text normalization helper (F2).
Handles Unicode NFKC normalization, whitespace collapsing, and dash unification.
"""

import unicodedata
import re


def normalize_text(text: str) -> str:
    """
    Applies NFKC normalization, unifies dashes/minus signs, and collapses excess whitespace.
    Preserves alphanumeric casing and punctuation.
    """
    if not text:
        return ""
    # NFKC normalizes full-width digits, ligatures, and compatibility characters
    normalized = unicodedata.normalize("NFKC", text)
    # Unify various unicode dashes and minus signs into standard ASCII minus '-'
    normalized = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]", "-", normalized)
    # Replace non-breaking spaces and thin spaces with standard space
    normalized = re.sub(r"[\u00a0\u2002\u2003\u2009\u202f]", " ", normalized)
    # Collapse multiple consecutive whitespace characters
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()
