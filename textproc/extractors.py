# -*- coding: utf-8 -*-
import io
import re
from typing import Optional

import pdfplumber
from pypdf import PdfReader

PAGE_BREAK = "\\f"

# Pre-compiled patterns for performance
_BROKEN_WORDS = re.compile(
    r"\\b(t he|w as|i s|a re|h as|h ad|w ith|f rom|t hat|t his)\\b", re.IGNORECASE
)
_WORD_BOUNDARIES = re.compile(r"([a-z])([A-Z])")
_SENTENCE_BOUNDARIES = re.compile(r"([.!?])([A-Z])")


def fix_extraction_spacing(text: str) -> str:
    """
    Optimized spacing fix with single-pass operations where possible.
    This is the only post-processing we really need.
    """
    if not text or len(text) < 50:
        return text

    # Fix common broken words in one pass
    text = _BROKEN_WORDS.sub(lambda m: m.group().replace(" ", ""), text)

    # Fix jammed words at boundaries
    text = _WORD_BOUNDARIES.sub(r"\\1 \\2", text)
    text = _SENTENCE_BOUNDARIES.sub(r"\\1 \\2", text)

    return text


def extract_with_pypdf(file_bytes: bytes) -> str:
    """
    Fastest extraction method using pypdf.
    Good for most text-based PDFs.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))

        # Pre-allocate list for better performance
        pages = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())

        if not pages:
            return ""

        # Join pages and fix spacing
        result = (PAGE_BREAK + "\\n").join(pages)
        return fix_extraction_spacing(result)

    except Exception:
        return ""


def extract_with_pdfplumber(file_bytes: bytes) -> str:
    """
    Better quality extraction, especially for tables and complex layouts.
    Slightly slower but more reliable.
    """
    try:
        pages = []

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                # Try layout mode first (better spacing)
                text = page.extract_text(layout=True)

                # Fallback to normal if layout fails
                if not text:
                    text = page.extract_text()

                if text:
                    pages.append(text.strip())

        if not pages:
            return ""

        result = (PAGE_BREAK + "\\n").join(pages)
        return fix_extraction_spacing(result)

    except Exception:
        return ""


# Stub for compatibility if you still have imports elsewhere
def extract_with_pymupdf(file_bytes: bytes) -> str:
    """Removed for Streamlit Cloud compatibility."""
    return ""


def force_ocr(file_bytes: bytes) -> bytes:
    """OCR removed for Streamlit Cloud compatibility."""
    return b""


def score_text(text: str) -> float:
    """Scoring removed for performance."""
    return 0.0
