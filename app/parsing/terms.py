"""
Payment terms parser (Rule O1).
Parses payment terms expressions (Net 30, due in 30 days, within 14 days, due on receipt) into day offsets.
"""

from typing import Optional, Tuple
import re

TERMS_PATTERNS = [
    # Net 30, Net-30, Net: 30, N30 (lookahead prevents matching currency like Net 361.60)
    (r"(?i)\b(?:net|n)\s*[-:]?\s*(\d{1,3})\b(?![.,]\d)", "Net {n}"),
    # due in 30 days
    (r"(?i)\bdue\s+in\s+(\d{1,3})\s+days?\b", "due in {n} days"),
    # payable within 30 days, within 30 days, innerhalb von 30 tagen
    (r"(?i)\b(?:payable\s+within|within|innerhalb\s+von)\s+(\d{1,3})\s+(?:days?|tagen)\b", "within {n} days"),
    # German: Zahlungsziel 30 Tage
    (r"(?i)\bzahlungsziel\s*[:\-]?\s*(\d{1,3})\s*(?:tage|tagen)?\b", "Zahlungsziel {n} Tage"),
    # 2/10 Net 30
    (r"(?i)\d+/\d+\s+net\s+(\d{1,3})\b", "Net {n}"),
    # 30 days net, 30 days from invoice, 30 days
    (r"(?i)\b(\d{1,3})\s*days?\s*(?:net|from|after|of)?\b", "{n} days"),

]

IMMEDIATE_PATTERNS = [
    r"(?i)\bdue\s+(?:on|upon)\s+receipt\b",
    r"(?i)\bupon\s+receipt\b",
    r"(?i)\bimmediate(?:ly)?\b",
    r"(?i)\bsofort\b",
]


def parse_payment_terms(text: str) -> Optional[Tuple[int, str]]:
    """
    Extracts payment terms from text.
    Returns:
        (offset_days: int, raw_terms_string: str) or None
    """
    if not text:
        return None

    # Check immediate terms (due on receipt -> 0 days)
    for pat in IMMEDIATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            return 0, m.group(0)

    for pat, display_template in TERMS_PATTERNS:
        m = re.search(pat, text)
        if m:
            days = int(m.group(1))
            # Reject unreasonable terms (> 180 days)
            if 0 <= days <= 180:
                raw_match = m.group(0)
                raw_lower = raw_match.lower()
                if "net" in raw_lower:
                    formatted_terms = f"Net {days}"
                elif "within" in raw_lower:
                    formatted_terms = f"within {days} days"
                elif "due in" in raw_lower:
                    formatted_terms = f"due in {days} days"
                else:
                    formatted_terms = raw_match.strip()
                return days, formatted_terms


    return None
