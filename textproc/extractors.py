# -*- coding: utf-8 -*-
import io
import re
from typing import Optional

import fitz  # PyMuPDF

PAGE_BREAK = "\f"

# Pre-compiled patterns for performance
_BROKEN_WORDS = re.compile(
    r"\b(t\s+he|w\s+as|i\s+s|a\s+re|h\s+as|h\s+ad|w\s+ith|f\s+rom|t\s+hat|t\s+his)\b",
    re.IGNORECASE,
)
_WORD_BOUNDARIES = re.compile(r"([a-z])([A-Z])")
_SENTENCE_BOUNDARIES = re.compile(r"([.!?])([A-Z])")

# Additional broken-word fixes compiled once (items not already covered by _BROKEN_WORDS)
_BROKEN_WORD_FIXES = [
    (re.compile(r"\bw\s+ere\b", re.IGNORECASE), "were"),
    (re.compile(r"\bh\s+ave\b", re.IGNORECASE), "have"),
    (re.compile(r"\bb\s+een\b", re.IGNORECASE), "been"),
    (re.compile(r"\bw\s+hat\b", re.IGNORECASE), "what"),
    (re.compile(r"\ba\s+nd\b", re.IGNORECASE), "and"),
    (re.compile(r"\bf\s+or\b", re.IGNORECASE), "for"),
    (re.compile(r"\bn\s+ot\b", re.IGNORECASE), "not"),
    (re.compile(r"\bb\s+ut\b", re.IGNORECASE), "but"),
    (re.compile(r"\bo\s+f\b", re.IGNORECASE), "of"),
    (re.compile(r"\bi\s+n\b", re.IGNORECASE), "in"),
    (re.compile(r"\bt\s+o\b", re.IGNORECASE), "to"),
    (re.compile(r"\ba\s+t\b", re.IGNORECASE), "at"),
    (re.compile(r"\bo\s+n\b", re.IGNORECASE), "on"),
    (re.compile(r"\bi\s+t\b", re.IGNORECASE), "it"),
    (re.compile(r"\ba\s+s\b", re.IGNORECASE), "as"),
    (re.compile(r"\bb\s+y\b", re.IGNORECASE), "by"),
    (re.compile(r"\bm\s+y\b", re.IGNORECASE), "my"),
    (re.compile(r"\bw\s+e\b", re.IGNORECASE), "we"),
    (re.compile(r"\bh\s+e\b", re.IGNORECASE), "he"),
    (re.compile(r"\bm\s+e\b", re.IGNORECASE), "me"),
    (re.compile(r"\bn\s+o\b", re.IGNORECASE), "no"),
    (re.compile(r"\bd\s+o\b", re.IGNORECASE), "do"),
    (re.compile(r"\bi\s+f\b", re.IGNORECASE), "if"),
]


def fix_extraction_spacing(text: str) -> str:
    """Fix common spacing issues from PDF extraction."""
    if not text:
        return ""

    # First pass: collapse spaces in the most common broken words handled by _BROKEN_WORDS.
    # Since this alternation matches forms like "t he" or "w as", removing spaces in the match yields the intended word.
    text = _BROKEN_WORDS.sub(lambda m: m.group(0).replace(" ", ""), text)

    # Second pass: handle the rest via compiled patterns
    for pat, replacement in _BROKEN_WORD_FIXES:
        text = pat.sub(replacement, text)

    # Fix jammed words - add spaces at obvious boundaries using compiled patterns
    text = _WORD_BOUNDARIES.sub(r"\1 \2", text)
    text = _SENTENCE_BOUNDARIES.sub(r"\1 \2", text)

    return text


def extract_with_pymupdf(file_bytes: bytes) -> str:
    try:
        doc = fitz.open("pdf", file_bytes)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"  # "text" for reading order
        doc.close()
        return fix_extraction_spacing(text.strip())
    except Exception:
        return ""
