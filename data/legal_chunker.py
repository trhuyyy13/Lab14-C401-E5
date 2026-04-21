import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ARTICLE_PATTERN = re.compile(r"^\s*Điều\s+(\d+)\s*\.\s*(.*)$", re.IGNORECASE)
CHAPTER_PATTERN = re.compile(r"^\s*CHƯƠNG[_\s]*([IVXLC0-9]+)\s*$", re.IGNORECASE)
CHARTER_START_PATTERN = re.compile(
    r"^\s*1\s*\.\s*Bảo_hiểm_y_tế quy_định trong Điều_lệ này", re.IGNORECASE
)
CLAUSE_PATTERN = re.compile(r"(?m)^\s*(\d+)\s*\.\s+")
POINT_PATTERN = re.compile(r"(?m)^\s*([a-zđ])\s*\)\s+")


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split_by_pattern(text: str, pattern: re.Pattern[str]) -> List[Tuple[Optional[str], str]]:
    matches = list(pattern.finditer(text))
    if not matches:
        return [(None, text.strip())]

    parts: List[Tuple[Optional[str], str]] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        label = match.group(1)
        part_text = text[start:end].strip()
        if part_text:
            parts.append((label, part_text))
    return parts


def _sliding_windows(text: str, chunk_size: int, overlap: int) -> List[str]:
    if len(text) <= chunk_size:
        return [text]

    step = max(1, chunk_size - overlap)
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += step
    return chunks


def _build_chunk(
    article_number: int,
    article_title: str,
    body_text: str,
    chapter: Optional[str],
    chapter_title: Optional[str],
    clause: Optional[str] = None,
    point: Optional[str] = None,
    part: Optional[int] = None,
) -> Dict[str, Any]:
    id_parts = [f"art_{article_number:02d}"]
    if clause:
        id_parts.append(f"clause_{clause}")
    if point:
        id_parts.append(f"point_{point}")
    if part and part > 1:
        id_parts.append(f"part_{part}")
    chunk_id = "_".join(id_parts)

    header = f"Điều {article_number}. {article_title}".strip()
    text = _normalize_whitespace(f"{header}\n{body_text}")

    return {
        "id": chunk_id,
        "text": text,
        "metadata": {
            "doc_id": "legal_bhyt_2005",
            "chapter": chapter,
            "chapter_title": chapter_title,
            "article": str(article_number),
            "article_title": article_title,
            "clause": clause,
            "point": point,
            "parent_article_id": f"art_{article_number:02d}",
        },
    }


def _chunk_article(
    article_number: int,
    article_title: str,
    article_text: str,
    chapter: Optional[str],
    chapter_title: Optional[str],
    max_chars: int,
    overlap_chars: int,
    split_threshold_chars: int,
) -> List[Dict[str, Any]]:
    article_text = article_text.strip()
    if not article_text:
        return []

    if len(article_text) <= split_threshold_chars:
        return [
            _build_chunk(
                article_number=article_number,
                article_title=article_title,
                body_text=article_text,
                chapter=chapter,
                chapter_title=chapter_title,
            )
        ]

    max_chunks_per_article = 4
    clause_parts = _split_by_pattern(article_text, CLAUSE_PATTERN)

    segments: List[tuple[Optional[str], str]] = []
    for clause_label, clause_text in clause_parts:
        clean_text = clause_text.strip()
        if not clean_text:
            continue

        if len(clean_text) <= max_chars:
            segments.append((clause_label, clean_text))
            continue

        for window in _sliding_windows(clean_text, max_chars, overlap_chars):
            segments.append((clause_label, window))

    if not segments:
        return [
            _build_chunk(
                article_number=article_number,
                article_title=article_title,
                body_text=article_text,
                chapter=chapter,
                chapter_title=chapter_title,
            )
        ]

    packed: List[tuple[Optional[str], str]] = []
    current_label: Optional[str] = None
    current_text = ""

    for clause_label, seg_text in segments:
        candidate = f"{current_text}\n{seg_text}".strip() if current_text else seg_text
        if current_text and len(candidate) > max_chars:
            packed.append((current_label, current_text))
            current_label = clause_label
            current_text = seg_text
        else:
            if current_label is None:
                current_label = clause_label
            current_text = candidate

    if current_text:
        packed.append((current_label, current_text))

    while len(packed) > max_chunks_per_article:
        prev_label, prev_text = packed[-2]
        _, last_text = packed[-1]
        packed[-2] = (prev_label, f"{prev_text}\n{last_text}".strip())
        packed.pop()

    chunks: List[Dict[str, Any]] = []
    for idx, (clause_label, content) in enumerate(packed, start=1):
        chunks.append(
            _build_chunk(
                article_number=article_number,
                article_title=article_title,
                body_text=content,
                chapter=chapter,
                chapter_title=chapter_title,
                clause=clause_label,
                part=idx if len(packed) > 1 else None,
            )
        )

    return chunks


def build_legal_chunks_from_text(
    text: str,
    max_chars: int = 1000,
    overlap_chars: int = 100,
    split_threshold_chars: int = 1300,
) -> List[Dict[str, Any]]:
    raw_lines = [line.rstrip() for line in text.splitlines()]

    start_idx: Optional[int] = None
    for idx, line in enumerate(raw_lines):
        if CHARTER_START_PATTERN.match(line.strip()):
            start_idx = idx
            break

    lines = raw_lines[start_idx:] if start_idx is not None else raw_lines

    chunks: List[Dict[str, Any]] = []
    current_chapter: Optional[str] = "I"
    current_chapter_title: Optional[str] = "QUY_ĐỊNH CHUNG"

    # Văn bản nguồn thiếu header "Điều 1", nên dựng Điều 1 từ đoạn mở đầu
    # bắt đầu tại "1 . Bảo_hiểm_y_tế ..." cho đến trước "Điều 2".
    article_number: Optional[int] = 1
    article_title: str = "Mục_tiêu và tính_chất của bảo_hiểm_y_tế"
    article_lines: List[str] = []

    pending_chapter_title = False

    def flush_article() -> None:
        nonlocal chunks, article_number, article_title, article_lines
        if article_number is None:
            return
        body = "\n".join(article_lines).strip()
        chunks.extend(
            _chunk_article(
                article_number=article_number,
                article_title=article_title,
                article_text=body,
                chapter=current_chapter,
                chapter_title=current_chapter_title,
                max_chars=max_chars,
                overlap_chars=overlap_chars,
                split_threshold_chars=split_threshold_chars,
            )
        )
        article_number = None
        article_title = ""
        article_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        chapter_match = CHAPTER_PATTERN.match(stripped)
        if chapter_match:
            flush_article()
            current_chapter = chapter_match.group(1)
            current_chapter_title = None
            pending_chapter_title = True
            continue

        if pending_chapter_title and stripped.isupper() and not ARTICLE_PATTERN.match(stripped):
            current_chapter_title = stripped
            pending_chapter_title = False
            continue
        pending_chapter_title = False

        article_match = ARTICLE_PATTERN.match(stripped)
        if article_match:
            flush_article()
            article_number = int(article_match.group(1))
            article_title = article_match.group(2).strip()
            continue

        if article_number is not None:
            article_lines.append(stripped)

    flush_article()
    return chunks


def load_legal_chunks(
    file_path: str = "data/data_legal.txt",
    max_chars: int = 1000,
    overlap_chars: int = 100,
    split_threshold_chars: int = 1300,
) -> List[Dict[str, Any]]:
    text = Path(file_path).read_text(encoding="utf-8")
    return build_legal_chunks_from_text(
        text,
        max_chars=max_chars,
        overlap_chars=overlap_chars,
        split_threshold_chars=split_threshold_chars,
    )
