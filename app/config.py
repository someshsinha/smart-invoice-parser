"""
Global configuration and tuning thresholds.
All magic numbers used throughout extraction and parsing are defined here.
"""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
SAMPLES_DIR = BASE_DIR / "samples"

# Service parameters
HOST = "0.0.0.0"
PORT = 8000
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit (constraint C7 / section 3.5)
PDF_MAGIC_BYTES = b"%PDF-"

# Geometry & reader parameters
LINE_MERGE_Y_TOLERANCE_RATIO = 0.5   # Vertical overlap tolerance relative to word height
CELL_GAP_SPACE_WIDTH_RATIO = 1.5     # Horizontal gap multiplier to split words into separate cells
FRAGMENT_MERGE_GAP_RATIO = 0.3       # Gap multiplier to merge fragmented words on same baseline

# Title & Document-type classification
TITLE_ZONE_Y_MAX_RATIO = 0.30        # Top 30% of page considered for title
TITLE_FONT_SIZE_RATIO = 1.3          # Font size >= 1.3x median considered title candidate

# Fuzzy matching thresholds (RapidFuzz)
VENDOR_BRAND_MATCH_MAX_EDITS = 2     # Max Levenshtein edit distance for distinctive brand token
LABEL_MATCH_MIN_SIMILARITY = 0.85    # Minimum partial/token ratio to consider a candidate label

# Amount & Arithmetic solving
ARITHMETIC_TOLERANCE = 0.01          # Tolerance for subtotal + tax == total check (rule O2)
JPY_CURRENCY_CODE = "JPY"
