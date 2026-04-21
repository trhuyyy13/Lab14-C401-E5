import re
import unicodedata
from typing import Dict, List


def clean_raw_text(text: str) -> str:
    """Clean legal text before chunking.

    - Remove XML/HTML-like tags.
    - Replace underscores with spaces.
    - Normalize Unicode and whitespace.
    - Remove stray zero-width/control characters.
    """
    cleaned = text or ""
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = cleaned.replace("_", " ")
    cleaned = cleaned.replace("\u200b", " ").replace("\ufeff", " ")
    cleaned = unicodedata.normalize("NFKC", cleaned)
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def split_semantic_chunks(text: str, source_name: str, max_chars: int = 2500) -> List[Dict[str, str]]:
    """Clean text first, then split into semantic chunks aligned with article boundaries."""
    clean_text = clean_raw_text(text)
    article_matches = list(re.finditer(r"(?=Điều\s+\d+\s*\.)", clean_text))
    sections: List[str] = []

    if article_matches:
        starts = [m.start() for m in article_matches]
        if starts[0] > 0:
            sections.append(clean_text[:starts[0]].strip())
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(clean_text)
            section = clean_text[start:end].strip()
            if section:
                sections.append(section)
    else:
        sections = [clean_text]

    chunks: List[Dict[str, str]] = []
    idx = 1
    for section in sections:
        if not section:
            continue
        if len(section) <= max_chars:
            chunks.append(
                {
                    "id": f"{source_name}#chunk_{idx:03d}",
                    "source": source_name,
                    "text": section,
                }
            )
            idx += 1
            continue

        sentences = re.split(r"(?<=[.!?])\s+", section)
        buffer = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(buffer) + len(sentence) + 1 <= max_chars:
                buffer = f"{buffer} {sentence}".strip()
            else:
                if buffer:
                    chunks.append(
                        {
                            "id": f"{source_name}#chunk_{idx:03d}",
                            "source": source_name,
                            "text": buffer.strip(),
                        }
                    )
                    idx += 1
                buffer = sentence
        if buffer:
            chunks.append(
                {
                    "id": f"{source_name}#chunk_{idx:03d}",
                    "source": source_name,
                    "text": buffer.strip(),
                }
            )
            idx += 1

    return chunks