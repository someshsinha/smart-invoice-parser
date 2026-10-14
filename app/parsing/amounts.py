"""
F7: Monetary amount parser (Decimal).
Locale-aware parsing for US/UK (1,234.56), German (1.234,56), Indian (1,23,456.00), and JPY amounts.
Ignores currency symbols/codes and filters out percentage tokens.
"""

from typing import Optional, List, Tuple
import re
from decimal import Decimal, ROUND_HALF_UP

CURRENCY_STRIP_REGEX = r"(?i)\b(?:GBP|USD|EUR|JPY|INR|CAD|AUD|CHF|SEK|NOK|NZD|SGD|Rs\.?|US\$)\b|[£$€¥₹￥円]"
PERCENTAGE_REGEX = r"\d+(?:[.,]\d+)?\s*%"


def is_percentage_token(text: str) -> bool:
    """Returns True if the string represents a percentage rather than an amount."""
    return bool(re.search(PERCENTAGE_REGEX, text))


def parse_money_amount(
    text: str,
    currency_hint: Optional[str] = None,
    decimal_separator_hint: Optional[str] = None,
) -> Optional[float]:
    """
    Parses a string token into a 2-decimal rounded float.
    Returns None if text cannot be parsed as a monetary number.
    """
    if not text:
        return None

    # Exclude percentages (e.g. "VAT 20%", "Sales tax 7.25%")
    if is_percentage_token(text):
        return None

    # Exclude dates (e.g. 14.10.2026, 2026-10-14, 03/09/2026)
    if re.search(r"\b\d{1,4}[./\-]\d{1,2}[./\-]\d{2,4}\b", text):
        return None

    # Strip currency codes and symbols
    clean = re.sub(CURRENCY_STRIP_REGEX, "", text).strip()

    # If non-currency alphabetic characters remain, this is not a pure monetary number
    if re.search(r"[a-zA-Z]", clean):
        return None
    # Strip wrapping parentheses for positive numbers or keep track if negative
    is_negative = False
    if clean.startswith("(") and clean.endswith(")"):
        is_negative = True
        clean = clean[1:-1].strip()
    elif clean.startswith("-"):
        is_negative = True
        clean = clean[1:].strip()
    elif clean.endswith("-"):
        is_negative = True
        clean = clean[:-1].strip()

    # Find the numeric part (digits, commas, dots, spaces, apostrophes)
    num_match = re.search(r"\d[\d.,'\s\u00a0]*", clean)
    if not num_match:
        return None

    raw_num = num_match.group(0).strip().replace(" ", "").replace("\u00a0", "").replace("'", "")
    if not raw_num:
        return None

    has_dot = "." in raw_num
    has_comma = "," in raw_num

    standardized = ""
    if has_dot and has_comma:
        # Last separator is the decimal point
        last_dot = raw_num.rfind(".")
        last_comma = raw_num.rfind(",")
        if last_dot > last_comma:
            # 1,234.56 (US / UK / IN)
            standardized = raw_num.replace(",", "")
        else:
            # 1.234,56 (German / European)
            standardized = raw_num.replace(".", "").replace(",", ".")
    elif has_comma and not has_dot:
        # Only comma present
        comma_count = raw_num.count(",")
        if comma_count > 1:
            # 1,000,000 (thousands separators)
            standardized = raw_num.replace(",", "")
        else:
            # Single comma: e.g. 12,50 or 1,234
            parts = raw_num.split(",")
            if len(parts[1]) == 3 and decimal_separator_hint != ",":
                # Likely thousands separator: 1,000
                standardized = raw_num.replace(",", "")
            else:
                # Decimal separator: 12,50
                standardized = raw_num.replace(",", ".")
    elif has_dot and not has_comma:
        # Only dot present
        dot_count = raw_num.count(".")
        if dot_count > 1:
            # 1.000.000 (German thousands separator)
            standardized = raw_num.replace(".", "")
        else:
            # Single dot: e.g. 361.60 or 1.234 (German thousands)
            parts = raw_num.split(".")
            if len(parts[1]) == 3 and decimal_separator_hint == ",":
                # German thousands separator: 1.200
                standardized = raw_num.replace(".", "")
            else:
                # Standard decimal point
                standardized = raw_num
    else:
        # Pure integer (e.g. JPY amounts)
        standardized = raw_num

    try:
        dec = Decimal(standardized)
        if is_negative:
            dec = -dec

        # JPY has no decimals on invoice, returned as .00 (Rule O5)
        quantized = dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(quantized)
    except Exception:
        return None


def extract_money_tokens_from_line(line_text: str) -> List[Tuple[float, str]]:
    """
    Finds all valid monetary amounts present on a line.
    Returns list of (parsed_float_value, raw_token_str).
    """
    tokens = []
    # Tokenize by whitespace while preserving punctuation
    words = line_text.split()
    for i, w in enumerate(words):
        if is_percentage_token(w):
            continue
        val = parse_money_amount(w)
        if val is not None:
            tokens.append((val, w))
        else:
            # Check combined with next word (e.g. "$ 242.17" or "GBP 433.92")
            if i + 1 < len(words):
                combo = f"{w} {words[i+1]}"
                val_combo = parse_money_amount(combo)
                if val_combo is not None and not is_percentage_token(combo):
                    tokens.append((val_combo, combo))

    return tokens
