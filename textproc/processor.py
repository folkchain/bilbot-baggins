# -*- coding: utf-8 -*-
from typing import List
import re

from .extractors import extract_with_pymupdf, PAGE_BREAK
from . import cleaners as C
from . import chunking as K


class TextProcessor:
    """Lightweight text processor optimized for Streamlit Cloud."""

    @staticmethod
    def read_text_file(file_bytes: bytes) -> str:
        """
        Efficiently read text files with smart encoding detection.
        """
        if not file_bytes:
            return ""

        # Remove BOM if present
        if file_bytes.startswith(b"\xef\xbb\xbf"):  # UTF-8 BOM
            file_bytes = file_bytes[3:]
        elif file_bytes.startswith(b"\xff\xfe"):  # UTF-16 LE BOM
            try:
                return file_bytes.decode("utf-16-le")
            except:
                pass
        elif file_bytes.startswith(b"\xfe\xff"):  # UTF-16 BE BOM
            try:
                return file_bytes.decode("utf-16-be")
            except:
                pass

        # Try encodings in order of likelihood
        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]

        for encoding in encodings:
            try:
                text = file_bytes.decode(encoding)
                # Quick validation - if we see too many replacement chars, try next
                if text.count("�") > len(text) * 0.01:  # More than 1% replacement chars
                    continue
                return text
            except (UnicodeDecodeError, LookupError):
                continue

        # Last resort - decode with error replacement
        return file_bytes.decode("utf-8", errors="replace")

    @staticmethod
    def read_pdf_file(file_bytes: bytes) -> str:
        if not file_bytes or len(file_bytes) < 100:
            return ""
        if not file_bytes.startswith(b"%PDF"):
            return ""
        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > 200:
            return ""

        # Try PyMuPDF first
        try:
            text = extract_with_pymupdf(file_bytes)
            if text and text.strip():
                return text
        except Exception:
            pass

        return ""

    @staticmethod
    def clean_text(
        text: str,
        remove_running_headers: bool = True,
        remove_bottom_footnotes: bool = True,
        is_pdf: bool = True,  # Added this parameter to match app.py
    ) -> str:
        """
        Clean text using the unified cleaning pipeline from cleaners.py
        """
        if not text:
            return ""

        # Determine document type based on is_pdf parameter
        kind = "pdf" if is_pdf else "txt"

        # 1. Perform initial structural cleaning on the raw text.
        text = C.remove_all_quotes(text)
        text = C.fix_line_break_hyphenation(text)
        text = C.remove_bottom_page_numbers(text)

        # 2.
        if remove_running_headers:
            text = C.strip_firstline_headers(text)

        # 3.
        if remove_bottom_footnotes:
            text = C.remove_footnote_markers(text)
            text = C.remove_references(text)
            text = C.remove_citation_lines(text)

        # 4. Clean the actual content.
        text = C.join_paragraphs_smart(text)
        text = C._clean_special_characters(text)
        text = C.fix_punctuation_spacing(text)

        # 5. Perform a final validation check.
        text = C._remove_midtext_roman_runs(text)

        # 6. Finally, flatten the text.
        text = C.final_flatten(text)

        return text.strip()

    @staticmethod
    def smart_split_into_chunks(text: str, max_length: int = 2200) -> List[str]:
        """Direct pass-through to chunking module."""
        return K.smart_split_into_chunks(text, max_length)

    @staticmethod
    def get_text_stats(text: str) -> dict:
        """Direct pass-through to chunking module."""
        return K.get_text_stats(text)
