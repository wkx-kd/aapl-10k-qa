"""Section-aware text chunking for 10-K documents."""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Default chunking parameters
DEFAULT_CHUNK_SIZE = 1500  # characters
DEFAULT_CHUNK_OVERLAP = 200  # characters
SMALL_SECTION_THRESHOLD = 1500
LARGE_SECTION_THRESHOLD = 10000


def chunk_records(
    records: list[dict],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    """Chunk all records using section-aware strategy.

    Returns list of chunk dicts with metadata.
    """
    all_chunks = []

    for record in records:
        text = record.get("section_text", "").strip()
        if not text:
            continue

        year = record["file_fiscal_year"]
        section_id = record["section_id"]
        section_title = record["section_title"]
        section_category = record.get("section_category", "other")

        text_len = len(text)

        if text_len < SMALL_SECTION_THRESHOLD:
            # Tier 1: Small sections - keep whole
            chunks = [text]
            sub_sections = [None]
        elif text_len < LARGE_SECTION_THRESHOLD:
            # Tier 2: Medium sections - paragraph-based splitting
            chunks, sub_sections = _split_by_paragraphs(
                text, chunk_size, chunk_overlap
            )
        else:
            # Tier 3: Large sections - intelligent sub-section splitting
            chunks, sub_sections = _split_large_section(
                text, section_id, chunk_size, chunk_overlap
            )

        for i, (chunk_text, sub_section) in enumerate(
            zip(chunks, sub_sections)
        ):
            chunk_id = f"{year}_s{section_id:02d}_c{i:03d}"
            all_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "year": year,
                    "section_id": section_id,
                    "section_title": section_title,
                    "section_category": section_category,
                    "sub_section": sub_section,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "text": chunk_text,
                }
            )

    logger.info(
        f"Created {len(all_chunks)} chunks from {len(records)} records"
    )
    return all_chunks


def _split_by_paragraphs(
    text: str, chunk_size: int, overlap: int
) -> tuple[list[str], list[Optional[str]]]:
    """Split text by paragraph boundaries with overlap."""
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    sub_sections: list[Optional[str]] = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            sub_sections.append(None)
            # Keep overlap from end of current chunk
            if overlap > 0:
                current_chunk = current_chunk[-overlap:] + "\n\n" + para
            else:
                current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        sub_sections.append(None)

    return chunks, sub_sections


def _split_large_section(
    text: str,
    section_id: int,
    chunk_size: int,
    overlap: int,
) -> tuple[list[str], list[Optional[str]]]:
    """Split large sections using sub-section detection."""
    # Detect sub-section headers based on section type
    if section_id == 3:  # Risk Factors
        return _split_risk_factors(text, chunk_size, overlap)
    elif section_id == 11:  # MD&A
        return _split_by_headers(text, chunk_size, overlap)
    elif section_id == 13:  # Financial Statements (Item 8)
        return _split_financial_statements(text, chunk_size, overlap)
    else:
        return _split_by_headers(text, chunk_size, overlap)


def _split_risk_factors(
    text: str, chunk_size: int, overlap: int
) -> tuple[list[str], list[Optional[str]]]:
    """Split risk factors by individual risk headings."""
    # Risk factor headings are typically bold/emphasized lines
    # Pattern: lines that end with certain patterns or are short standalone paragraphs
    lines = text.split("\n")
    sections = []
    current_section = ""
    current_heading: Optional[str] = None

    for line in lines:
        stripped = line.strip()
        # Detect heading: short line (< 200 chars), not empty, may end with period or not
        is_heading = (
            stripped
            and len(stripped) < 200
            and not stripped[0].isdigit()
            and (
                stripped.endswith(".")
                or stripped.endswith(":")
                or (len(stripped) > 20 and stripped[0].isupper() and "\t" not in stripped)
            )
            and len(stripped.split()) > 3
        )

        if is_heading and current_section and len(current_section) > 500:
            sections.append((current_section.strip(), current_heading))
            current_section = stripped + "\n"
            current_heading = stripped[:100]
        else:
            current_section += line + "\n"
            if current_heading is None and stripped:
                current_heading = stripped[:100]

    if current_section.strip():
        sections.append((current_section.strip(), current_heading))

    # Further split any sections that are too large
    chunks = []
    sub_sections: list[Optional[str]] = []
    for section_text, heading in sections:
        if len(section_text) > chunk_size * 2:
            sub_chunks, sub_subs = _split_by_paragraphs(
                section_text, chunk_size, overlap
            )
            for sc in sub_chunks:
                chunks.append(sc)
                sub_sections.append(heading)
        else:
            chunks.append(section_text)
            sub_sections.append(heading)

    return chunks, sub_sections


def _split_by_headers(
    text: str, chunk_size: int, overlap: int
) -> tuple[list[str], list[Optional[str]]]:
    """Split text by detected header patterns."""
    # Common header patterns in 10-K
    header_pattern = re.compile(
        r"^(?:[A-Z][A-Za-z\s,&'/-]+(?:\n|$))"  # Title case headers
        r"|^(?:[A-Z]{2,}[A-Z\s,&'/-]*(?:\n|$))"  # ALL CAPS headers
        r"|^(?:Note\s+\d+)"  # Note headers
        r"|^(?:\d+\.\s+[A-Z])",  # Numbered headers
        re.MULTILINE,
    )

    matches = list(header_pattern.finditer(text))

    if not matches or len(matches) < 2:
        return _split_by_paragraphs(text, chunk_size, overlap)

    sections = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        heading = match.group().strip()[:100]
        if section_text:
            sections.append((section_text, heading))

    # Include text before the first header
    if matches[0].start() > 100:
        pre_text = text[: matches[0].start()].strip()
        if pre_text:
            sections.insert(0, (pre_text, None))

    # Further split large sections
    chunks = []
    sub_sections: list[Optional[str]] = []
    for section_text, heading in sections:
        if len(section_text) > chunk_size * 2:
            sub_chunks, _ = _split_by_paragraphs(
                section_text, chunk_size, overlap
            )
            for sc in sub_chunks:
                chunks.append(sc)
                sub_sections.append(heading)
        else:
            chunks.append(section_text)
            sub_sections.append(heading)

    return chunks, sub_sections


def _split_financial_statements(
    text: str, chunk_size: int, overlap: int
) -> tuple[list[str], list[Optional[str]]]:
    """Split Item 8 financial statements by Note boundaries and statement headers."""
    # Split by "Note X" headers and "CONSOLIDATED" statement headers
    split_pattern = re.compile(
        r"(?=\bNote\s+\d+\b)"
        r"|(?=CONSOLIDATED\s+(?:STATEMENTS?|BALANCE))",
        re.IGNORECASE,
    )

    parts = split_pattern.split(text)
    parts = [p.strip() for p in parts if p.strip()]

    chunks = []
    sub_sections: list[Optional[str]] = []

    for part in parts:
        heading_match = re.match(
            r"(Note\s+\d+[^\n]*|CONSOLIDATED[^\n]*)", part, re.IGNORECASE
        )
        heading = heading_match.group()[:100] if heading_match else None

        if len(part) > chunk_size * 2:
            sub_chunks, _ = _split_by_paragraphs(
                part, chunk_size, overlap
            )
            for sc in sub_chunks:
                chunks.append(sc)
                sub_sections.append(heading)
        else:
            chunks.append(part)
            sub_sections.append(heading)

    return chunks, sub_sections
