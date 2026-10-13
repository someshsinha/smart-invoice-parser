"""
F8: Geometry-Aware Candidate Extraction.
Extracts label-value candidates across three spatial relationships:
1. Same cell / same line (to the right of label)
2. Right-hand cell on the same horizontal row (nearest cell with vertical overlap)
3. Label above value (tabular header row with values underneath within 3 line heights)
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import re
from rapidfuzz import fuzz
from app.reader.pdf_text import ParsedDocument, TextLine, TextCell


@dataclass
class GeometricCandidate:
    field_name: str
    value_text: str
    label_text: str
    label_strength: float
    relation: str  # 'same_cell', 'same_line', 'right_cell', 'below_row', 'fallback'
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    page_idx: int
    score: float


def find_label_matches_in_text(
    text: str,
    label_lexicon: List[str],
    min_similarity: float = 0.88,
) -> List[Tuple[str, int, int, float]]:
    """
    Finds exact and fuzzy label matches in a text string.
    Returns:
        List of (matched_label, start_idx, end_idx, similarity_score)
    """
    text_lower = text.lower()
    matches = []

    for lbl in label_lexicon:
        lbl_lower = lbl.lower()
        # 1. Exact regex search with word boundaries
        for m in re.finditer(rf"\b{re.escape(lbl_lower)}\b", text_lower):
            matches.append((lbl, m.start(), m.end(), 1.0))

    if matches:
        return matches

    # 2. Fuzzy search across sliding n-grams if no exact match found
    words = text_lower.split()
    for lbl in label_lexicon:
        lbl_words = lbl.lower().split()
        n = len(lbl_words)
        for i in range(len(words) - n + 1):
            window = " ".join(words[i : i + n])
            sim = fuzz.ratio(window, lbl.lower()) / 100.0
            if sim >= min_similarity:
                # Approximate start/end indices in original text
                start_idx = text_lower.find(window)
                if start_idx != -1:
                    matches.append((lbl, start_idx, start_idx + len(window), sim))

    return matches


def extract_field_candidates(
    doc: ParsedDocument,
    field_name: str,
    label_lexicon: List[str],
    exclude_labels: Optional[List[str]] = None,
) -> List[GeometricCandidate]:
    """
    Extracts geometric candidates for a field using same-line, right-cell, and label-above relationships.
    """
    if not doc.pages or not doc.has_text:
        return []

    candidates: List[GeometricCandidate] = []
    exclude_list = exclude_labels or []

    for page in doc.pages:
        lines = page.lines
        for line_idx, line in enumerate(lines):
            line_text = line.text
            line_lower = line_text.lower()

            # Skip lines matching explicit exclusion patterns
            if any(re.search(rf"\b{re.escape(ex.lower())}\b", line_lower) for ex in exclude_list):
                continue

            # Check for label matches on the line
            label_matches = find_label_matches_in_text(line_text, label_lexicon)
            if not label_matches:
                continue

            # Process each matched label on the line
            for matched_lbl, start_idx, end_idx, lbl_strength in label_matches:
                # -------------------------------------------------------------
                # Relation 1: Same Line / Same Cell to the Right
                # -------------------------------------------------------------
                after_label = line_text[end_idx:].strip()
                # Clean leading colon, hash, or hyphens
                after_label_clean = re.sub(r"^[:#.\-\s]+", "", after_label).strip()
                if after_label_clean:
                    # Take first segment (up to next large gap or next label)
                    first_token = after_label_clean.split("   ")[0].strip()
                    if first_token:
                        candidates.append(
                            GeometricCandidate(
                                field_name=field_name,
                                value_text=first_token,
                                label_text=matched_lbl,
                                label_strength=lbl_strength,
                                relation="same_line",
                                bbox=(line.x0, line.y0, line.x1, line.y1),
                                page_idx=page.page_idx,
                                score=0.95 * lbl_strength,
                            )
                        )

                # -------------------------------------------------------------
                # Relation 2: Right-hand Cell on the Same Line
                # -------------------------------------------------------------
                # Find cell containing the label
                for cell_idx, cell in enumerate(line.cells):
                    cell_lower = cell.text.lower()
                    if matched_lbl.lower() in cell_lower:
                        # Value in the adjacent right cell
                        if cell_idx + 1 < len(line.cells):
                            right_cell = line.cells[cell_idx + 1]
                            val_clean = re.sub(r"^[:#.\-\s]+", "", right_cell.text).strip()
                            if val_clean:
                                candidates.append(
                                    GeometricCandidate(
                                        field_name=field_name,
                                        value_text=val_clean,
                                        label_text=matched_lbl,
                                        label_strength=lbl_strength,
                                        relation="right_cell",
                                        bbox=(right_cell.x0, right_cell.y0, right_cell.x1, right_cell.y1),
                                        page_idx=page.page_idx,
                                        score=0.93 * lbl_strength,
                                    )
                                )

                # -------------------------------------------------------------
                # Relation 3: Label Above Value (Table Header Row)
                # -------------------------------------------------------------
                # Check line immediately underneath within 3 line heights
                line_h = max(10.0, line.y1 - line.y0)
                for next_idx in range(line_idx + 1, min(len(lines), line_idx + 3)):
                    next_line = lines[next_idx]
                    vert_distance = next_line.y0 - line.y1
                    if 0 <= vert_distance <= (line_h * 2.5):
                        # Find cell in next_line with horizontal overlap
                        for next_cell in next_line.cells:
                            # Calculate horizontal overlap with current line / cell
                            overlap = max(0.0, min(line.x1, next_cell.x1) - max(line.x0, next_cell.x0))
                            if overlap > 10.0:
                                val_clean = next_cell.text.strip()
                                if val_clean:
                                    candidates.append(
                                        GeometricCandidate(
                                            field_name=field_name,
                                            value_text=val_clean,
                                            label_text=matched_lbl,
                                            label_strength=lbl_strength,
                                            relation="below_row",
                                            bbox=(next_cell.x0, next_cell.y0, next_cell.x1, next_cell.y1),
                                            page_idx=page.page_idx,
                                            score=0.88 * lbl_strength,
                                        )
                                    )

    return candidates
