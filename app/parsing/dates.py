"""
F6: Format-agnostic date parser with ambiguity detection and country-based disambiguation.
Supports ISO, UK/US slash dates, German dot dates, month names, and 2-digit years.
"""

from typing import Optional, Tuple
import re
from datetime import date
from app.extract.warnings import warn_ambiguous_date

MONTH_NAMES = {
    # English
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3, "mär": 3, "mrz": 3, "märz": 3,
    "apr": 4, "april": 4,
    "may": 5, "mai": 5,
    "jun": 6, "june": 6, "juni": 6,
    "jul": 7, "july": 7, "juli": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "okt": 10, "oktober": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12, "dez": 12, "dezember": 12,
}


def parse_two_digit_year(yr: int) -> int:
    """Expands 2-digit years (00-69 -> 2000s, 70-99 -> 1900s)."""
    return 2000 + yr if yr <= 69 else 1900 + yr


def parse_date_string(
    raw_text: str,
    date_order: str = "DMY",
    country: str = "United Kingdom",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses a raw date string into an ISO YYYY-MM-DD date.
    Returns:
        (iso_date: Optional[str], ambiguity_warning: Optional[str])
    """
    if not raw_text:
        return None, None

    cleaned = raw_text.strip().rstrip(".,;:")
    # Strip ordinal suffixes: 1st, 2nd, 3rd, 4th -> 1, 2, 3, 4
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", cleaned, flags=re.IGNORECASE)

    # 1. Check named months: e.g. "3 Sep 2026", "Sep 3, 2026", "03-Sep-2026", "3. September 2026"
    month_name_match = re.search(
        r"\b(?:(\d{1,2})[\s\-./]+)?([A-Za-zäöüÄÖÜ]{3,9})[\s\-./,]+(?:(\d{1,2})[\s\-./,]+)?(\d{2,4})\b",
        cleaned,
    )
    if month_name_match:
        d1, month_str, d2, year_str = month_name_match.groups()
        m_lower = month_str.lower().rstrip(".")
        if m_lower in MONTH_NAMES:
            month = MONTH_NAMES[m_lower]
            day_str = d1 if d1 else d2
            if day_str and year_str:
                day = int(day_str)
                yr = int(year_str)
                if yr < 100:
                    yr = parse_two_digit_year(yr)
                try:
                    dt = date(yr, month, day)
                    return dt.isoformat(), None
                except ValueError:
                    pass

    # 2. Check year-first formats: YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD, YYYYMMDD
    y_first = re.search(r"\b(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})\b", cleaned)
    if y_first:
        yr = int(y_first.group(1))
        m = int(y_first.group(2))
        d = int(y_first.group(3))
        try:
            return date(yr, m, d).isoformat(), None
        except ValueError:
            pass

    # Compact 8-digit: YYYYMMDD
    compact = re.search(r"\b(\d{4})(\d{2})(\d{2})\b", cleaned)
    if compact:
        yr = int(compact.group(1))
        m = int(compact.group(2))
        d = int(compact.group(3))
        try:
            return date(yr, m, d).isoformat(), None
        except ValueError:
            pass

    # 3. Numeric formats: D/M/Y or M/D/Y (with /, ., or -)
    num_match = re.search(r"\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\b", cleaned)
    if num_match:
        part1 = int(num_match.group(1))
        part2 = int(num_match.group(2))
        yr = int(num_match.group(3))
        if yr < 100:
            yr = parse_two_digit_year(yr)

        # Disambiguation logic
        # If one group > 12, that group MUST be the day
        if part1 > 12 and part2 <= 12:
            try:
                return date(yr, part2, part1).isoformat(), None
            except ValueError:
                pass
        elif part2 > 12 and part1 <= 12:
            try:
                return date(yr, part1, part2).isoformat(), None
            except ValueError:
                pass
        elif part1 <= 12 and part2 <= 12:
            # Both groups <= 12!
            # If parts are equal (e.g. 05/05/2026), it is not ambiguous
            if part1 == part2:
                try:
                    return date(yr, part1, part2).isoformat(), None
                except ValueError:
                    pass

            # Genuinely ambiguous: decide by vendor country / date_order
            is_us = (date_order == "MDY") or (country == "United States")
            if is_us:
                m = part1
                d = part2
                order_name = "month"
            else:
                d = part1
                m = part2
                order_name = "day"

            try:
                dt = date(yr, m, d)
                warning = warn_ambiguous_date(num_match.group(0), order_name, country)
                return dt.isoformat(), warning
            except ValueError:
                # If invalid in preferred order, try alternate order
                try:
                    dt = date(yr, d, m)
                    return dt.isoformat(), None
                except ValueError:
                    pass

    return None, None
