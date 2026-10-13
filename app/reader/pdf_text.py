"""
PDF Text Reader with Geometry (F1).
Extracts words, lines, and cells with bounding boxes and font sizes from digital PDFs using PyMuPDF.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import pymupdf as fitz
from app.reader.normalize import normalize_text


@dataclass
class TextWord:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float
    page_idx: int

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)


@dataclass
class TextCell:
    text: str
    words: List[TextWord]
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float
    page_idx: int


@dataclass
class TextLine:
    text: str
    cells: List[TextCell]
    words: List[TextWord]
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float
    page_idx: int


@dataclass
class ParsedPage:
    page_idx: int
    width: float
    height: float
    lines: List[TextLine]
    full_text: str


@dataclass
class ParsedDocument:
    pages: List[ParsedPage]
    full_text: str
    has_text: bool


def extract_document_text(pdf_bytes: bytes) -> ParsedDocument:
    """
    Parses PDF bytes into a ParsedDocument containing geometric words, lines, and cells.
    Raises ValueError if PDF is corrupted or cannot be read.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Corrupt or unreadable PDF: {str(e)}")

    if doc.is_encrypted:
        raise ValueError("Encrypted PDFs are not supported.")

    parsed_pages: List[ParsedPage] = []
    total_words_count = 0
    doc_text_parts: List[str] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        rect = page.rect
        page_width = rect.width
        page_height = rect.height

        # Extract words: (x0, y0, x1, y1, word, block_no, line_no, word_no)
        raw_words = page.get_text("words")
        if not raw_words:
            parsed_pages.append(
                ParsedPage(
                    page_idx=page_idx,
                    width=page_width,
                    height=page_height,
                    lines=[],
                    full_text="",
                )
            )
            continue

        # Extract span font sizes from text dict for accurate typography information
        # Map (block_no, line_no, word_no) or approximate bboxes to font sizes
        page_dict = page.get_text("dict")
        bbox_font_sizes: List[Tuple[float, float, float, float, float]] = []
        for block in page_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        span_bbox = span["bbox"]
                        span_size = float(span.get("size", 10.0))
                        bbox_font_sizes.append(
                            (span_bbox[0], span_bbox[1], span_bbox[2], span_bbox[3], span_size)
                        )

        # Build TextWord objects
        words: List[TextWord] = []
        for w in raw_words:
            x0, y0, x1, y1, text = float(w[0]), float(w[1]), float(w[2]), float(w[3]), w[4]
            clean_word = normalize_text(text)
            if not clean_word:
                continue

            # Find matching font size from spans (matching vertical proximity)
            font_size = 10.0
            for sbx0, sby0, sbx1, sby1, size in bbox_font_sizes:
                if abs(y0 - sby0) < 4.0 and (sbx0 <= x0 + 2.0 and sbx1 >= x1 - 2.0):
                    font_size = size
                    break

            words.append(
                TextWord(
                    text=clean_word,
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    font_size=font_size,
                    page_idx=page_idx,
                )
            )

        total_words_count += len(words)
        if not words:
            parsed_pages.append(
                ParsedPage(
                    page_idx=page_idx,
                    width=page_width,
                    height=page_height,
                    lines=[],
                    full_text="",
                )
            )
            continue

        # Geometry-aware clustering of words into lines
        lines = _cluster_words_into_lines(words, page_idx)
        page_text = "\n".join(line.text for line in lines)
        doc_text_parts.append(page_text)

        parsed_pages.append(
            ParsedPage(
                page_idx=page_idx,
                width=page_width,
                height=page_height,
                lines=lines,
                full_text=page_text,
            )
        )

    doc.close()
    has_text = total_words_count > 0
    full_text = "\n\n".join(doc_text_parts)

    return ParsedDocument(pages=parsed_pages, full_text=full_text, has_text=has_text)


def _cluster_words_into_lines(words: List[TextWord], page_idx: int) -> List[TextLine]:
    """
    Groups words into lines using vertical overlap, sorts words left-to-right,
    and splits lines into cells based on horizontal gaps.
    """
    if not words:
        return []

    # Sort primarily by vertical coordinate (top to bottom)
    sorted_words = sorted(words, key=lambda w: (w.y0, w.x0))

    # Cluster words where vertical centers are within tolerance
    line_clusters: List[List[TextWord]] = []
    for word in sorted_words:
        word_cy = (word.y0 + word.y1) / 2.0
        word_h = max(6.0, word.height)
        matched_cluster = None

        for cluster in line_clusters:
            cluster_cys = [(w.y0 + w.y1) / 2.0 for w in cluster]
            cluster_avg_cy = sum(cluster_cys) / len(cluster_cys)
            cluster_avg_h = sum(w.height for w in cluster) / len(cluster)
            tol = max(4.0, cluster_avg_h * 0.45)
            if abs(word_cy - cluster_avg_cy) <= tol:
                matched_cluster = cluster
                break

        if matched_cluster is not None:
            matched_cluster.append(word)
        else:
            line_clusters.append([word])

    # Sort clusters top to bottom by average y0
    line_clusters.sort(key=lambda cluster: sum(w.y0 for w in cluster) / len(cluster))

    result_lines: List[TextLine] = []
    for cluster in line_clusters:
        # Sort words left-to-right
        sorted_cluster = sorted(cluster, key=lambda w: w.x0)

        # Split cluster into cells if horizontal gap is significant (e.g. gap > 12 pt or 1.8x word height)
        cells: List[TextCell] = []
        current_cell_words: List[TextWord] = [sorted_cluster[0]]

        for i in range(1, len(sorted_cluster)):
            prev_word = sorted_cluster[i - 1]
            curr_word = sorted_cluster[i]
            gap = curr_word.x0 - prev_word.x1
            avg_h = (prev_word.height + curr_word.height) / 2.0
            # A gap > 14 pts or > 1.4 * height indicates separate columnar cells
            if gap > max(14.0, avg_h * 1.4):
                cell_text = " ".join(w.text for w in current_cell_words)
                cells.append(
                    TextCell(
                        text=cell_text,
                        words=current_cell_words,
                        x0=current_cell_words[0].x0,
                        y0=min(w.y0 for w in current_cell_words),
                        x1=current_cell_words[-1].x1,
                        y1=max(w.y1 for w in current_cell_words),
                        font_size=max(w.font_size for w in current_cell_words),
                        page_idx=page_idx,
                    )
                )
                current_cell_words = [curr_word]
            else:
                current_cell_words.append(curr_word)

        if current_cell_words:
            cell_text = " ".join(w.text for w in current_cell_words)
            cells.append(
                TextCell(
                    text=cell_text,
                    words=current_cell_words,
                    x0=current_cell_words[0].x0,
                    y0=min(w.y0 for w in current_cell_words),
                    x1=current_cell_words[-1].x1,
                    y1=max(w.y1 for w in current_cell_words),
                    font_size=max(w.font_size for w in current_cell_words),
                    page_idx=page_idx,
                )
            )

        line_text = "   ".join(c.text for c in cells)
        line_x0 = min(w.x0 for w in sorted_cluster)
        line_y0 = min(w.y0 for w in sorted_cluster)
        line_x1 = max(w.x1 for w in sorted_cluster)
        line_y1 = max(w.y1 for w in sorted_cluster)
        line_font_size = max(w.font_size for w in sorted_cluster)

        result_lines.append(
            TextLine(
                text=line_text,
                cells=cells,
                words=sorted_cluster,
                x0=line_x0,
                y0=line_y0,
                x1=line_x1,
                y1=line_y1,
                font_size=line_font_size,
                page_idx=page_idx,
            )
        )

    return result_lines
