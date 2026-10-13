"""
F4: Vendor Resolver (Appendix M).
Resolves supplier header text against the six canonical vendors, handles brand token gating,
rejects decoys, excludes customer (Bruviti), and assigns calibrated confidence.
"""

from typing import Tuple, List, Optional
import re
from rapidfuzz.distance import Levenshtein
from app.reader.pdf_text import ParsedDocument, TextLine
from app.knowledge.vendors import CANONICAL_VENDORS, CUSTOMER_NAME_TOKENS
from app.extract.warnings import (
    warn_unknown_vendor,
    warn_brand_only_vendor,
    warn_vendor_resembles,
)

LEGAL_SUFFIXES = [
    r"\bltd\b", r"\blimited\b", r"\binc\b", r"\bincorporated\b", r"\bcorp\b",
    r"\bcorporation\b", r"\bgmbh\b", r"\bkk\b", r"\bk\.k\.\b", r"\bkabushiki kaisha\b",
    r"\bpvt\b", r"\bprivate\b", r"\bllp\b", r"\bplc\b", r"\bco\b", r"\bcompany\b",
    r"\bthe\b"
]

CUSTOMER_BLOCK_HEADERS = [
    r"\bbill\s*to\b", r"\bbilled\s*to\b", r"\bsold\s*to\b", r"\bship\s*to\b",
    r"\bcustomer\b", r"\binvoice\s*to\b", r"\bkunde\b", r"\brechnungsempfänger\b",
    r"お客様"
]


def clean_vendor_text(text: str) -> str:
    """Normalizes candidate vendor text by lowercasing, stripping punctuation, and removing legal suffixes."""
    text = text.lower()
    text = text.replace("&", " and ")
    # Normalize spelling variations (e.g. Harbor -> Harbour)
    text = re.sub(r"\bharbor\b", "harbour", text)
    # Strip common punctuation
    text = re.sub(r"[,\.:|/\-_()]+", " ", text)
    # Remove legal suffixes
    for suffix_pat in LEGAL_SUFFIXES:
        text = re.sub(suffix_pat, " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def resolve_vendor(doc: ParsedDocument) -> Tuple[str, float, List[str]]:
    """
    Extracts and resolves the canonical vendor name from the document.
    Returns:
        (canonical_name_or_unknown: str, confidence: float, warnings: List[str])
    """
    if not doc.pages or not doc.has_text:
        return "unknown", 0.0, [warn_unknown_vendor()]

    first_page = doc.pages[0]
    page_height = first_page.height

    # 1. Filter out customer block lines and Bruviti lines
    in_customer_block = False
    candidate_lines: List[TextLine] = []

    for line in first_page.lines:
        line_lower = line.text.lower()

        # Check if line contains customer markers (Bruviti)
        if any(c_tok in line_lower for c_tok in CUSTOMER_NAME_TOKENS):
            continue

        # Check for start of customer/ship-to/bill-to block
        if any(re.search(pat, line_lower) for pat in CUSTOMER_BLOCK_HEADERS):
            in_customer_block = True
            continue

        # Customer block typically ends after 4-5 lines or when a section header starts
        if in_customer_block:
            if line.y0 > (page_height * 0.5) or re.search(r"\b(item|qty|description|total|subtotal)\b", line_lower):
                in_customer_block = False
            else:
                continue

        # Vendor header is typically in the top 35% of page 1
        if line.y0 <= (page_height * 0.35):
            candidate_lines.append(line)

    # If top region didn't match, also inspect first 6 lines of page 1 regardless of coordinates
    if not candidate_lines:
        candidate_lines = first_page.lines[:6]

    # 2. Check candidate lines against Canonical Vendors
    best_match: Optional[str] = None
    best_conf = 0.0
    warnings: List[str] = []

    # All candidate text snippets
    extracted_candidates = []
    for line in candidate_lines:
        cleaned = clean_vendor_text(line.text)
        if cleaned:
            extracted_candidates.append(cleaned)
        # Also include individual cells if cells exist
        for cell in line.cells:
            cleaned_cell = clean_vendor_text(cell.text)
            if cleaned_cell and cleaned_cell not in extracted_candidates:
                extracted_candidates.append(cleaned_cell)

    for cand in extracted_candidates:
        cand_tokens = cand.split()
        if not cand_tokens:
            continue

        for canonical_name, meta in CANONICAL_VENDORS.items():
            brand_token = meta["brand_token"]
            generic_word = meta["generic_word"]

            # Compute brand distance
            brand_words = brand_token.split()
            # Check if brand_token (single or multi-word) matches candidate tokens
            brand_match_distance = 99
            if len(brand_words) == 1:
                # Minimum Levenshtein distance across any token in candidate
                brand_distances = [Levenshtein.distance(brand_token, tok) for tok in cand_tokens]
                brand_match_distance = min(brand_distances) if brand_distances else 99
            else:
                # Multi-word brand token (e.g. "blue harbour")
                cand_subsequences = [
                    " ".join(cand_tokens[i : i + len(brand_words)])
                    for i in range(len(cand_tokens) - len(brand_words) + 1)
                ]
                if cand_subsequences:
                    brand_match_distance = min(Levenshtein.distance(brand_token, sub) for sub in cand_subsequences)

            if brand_match_distance <= 2:
                # 1. First check if the vendor's own generic word matches
                generic_distances = [Levenshtein.distance(generic_word, tok) for tok in cand_tokens]
                min_generic_dist = min(generic_distances) if generic_distances else 99

                if min_generic_dist <= 2:
                    # Brand token AND own generic word match -> ACCEPT
                    conf = 0.98 if (brand_match_distance == 0 and min_generic_dist == 0) else 0.90
                    return canonical_name, conf, []

                # 2. Own generic word did NOT match: check for conflicting generic words (e.g. Northwind Logistics)
                conflicting_generics = [
                    v_meta["generic_word"]
                    for c_name, v_meta in CANONICAL_VENDORS.items()
                    if c_name != canonical_name
                ]
                has_conflicting_generic = any(
                    min([Levenshtein.distance(cg, tok) for tok in cand_tokens]) <= 1
                    for cg in conflicting_generics
                )

                if has_conflicting_generic:
                    # Conflicting generic word -> Return unknown with warning (§8.3)
                    return "unknown", 0.30, [warn_vendor_resembles(canonical_name)]

                # 3. Generic word absent -> Brand-only match (§8.3)
                return canonical_name, 0.85, [warn_brand_only_vendor(canonical_name)]


    # If no canonical vendor matched, return unknown (§8.3)
    return "unknown", 0.20, [warn_unknown_vendor()]
