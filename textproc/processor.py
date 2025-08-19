# -*- coding: utf-8 -*-
from typing import List, Tuple

from .extractors import (
    PAGE_BREAK,
    score_text,
    extract_with_pymupdf,
    extract_with_pdfplumber,
    extract_with_pypdf,
    maybe_ocr,
)
from . import cleaners as C
from . import chunking as K


class TextProcessor:
    """Handles text extraction, cleaning, chunking, and stats."""

    # -------- Reading --------

    @staticmethod
    def read_text_file(file_bytes: bytes) -> str:
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="ignore")

    @staticmethod
    def read_pdf_file(file_bytes: bytes) -> str:
        # Native extraction
        native = []
        for fn in (extract_with_pymupdf, extract_with_pdfplumber, extract_with_pypdf):
            txt = fn(file_bytes)
            native.append((txt, score_text(txt)))
        native_txt, native_score = max(native, key=lambda t: t[1]) if native else ("", 0.0)

        # OCR path
        ocr_txt, ocr_score = "", 0.0
        ocr_pdf = maybe_ocr(file_bytes)
        if ocr_pdf:
            for fn in (extract_with_pymupdf, extract_with_pdfplumber, extract_with_pypdf):
                ocr_txt = fn(ocr_pdf)
                if ocr_txt:
                    break
            ocr_score = score_text(ocr_txt)

        best_txt = native_txt if native_score >= ocr_score else ocr_txt
        return best_txt.strip()

    # -------- Cleaning (TTS‑focused) --------

    @staticmethod
    def clean_text(text: str) -> str:
        # Page-aware first pass for PDFs
        text = C.strip_running_headers_and_footers(text)

        # 1) Fix linebreak hyphens/dashes/soft hyphens/kiyeok FIRST
        text = C.normalize_linebreak_hyphens(text)

        # 2) Strip underscores and unreadables/ornamentals
        text = C.strip_underscores_and_unreadables(text)

        # 3) Remove all quotation marks, KEEP apostrophes for contractions
        text = C.strip_all_quotes_keep_apostrophes(text)

        # 4) Remove TOC/headers/footers/page numbers/URLs/emails/citations/markers/captions
        text = C.remove_unwanted(text)

        # 5) Drop likely footnote blocks at page bottoms
        text = C.drop_footnotes_at_bottom(text)

        # 6) Join wrapped lines (after hyphen fix)
        text = C.join_wrapped_lines(text)

        # 7) Ellipses -> single period
        text = C.normalize_ellipses_to_period(text)

        # 8) Ranges: small numbers to words; larger numeric -> 'to'
        text = C.tts_number_ranges(text)

        # 9) Punctuation shaping for TTS (dashes->commas, colons->commas except times)
        text = C.tts_punctuation_shaping(text)

        # 10) Whitespace & punctuation normalization, collapse blank lines
        text = C.clean_whitespace_and_punct(text)

        # 11) OCR nuisances (spaced letters + digit-in-word fixes, common word fixes)
        text = C.ocr_spaced_letters(text)
        text = C.ocr_digit_in_word_fixes(text)
        text = C.ocr_common_word_fixes(text)

        # 12) Acronyms without dots
        text = C.collapse_dotted_acronyms(text)

        # Remove internal page breaks now that cleanup is done
        return text.replace(PAGE_BREAK, "\n").strip()

    # -------- Chunking & Stats --------

    @staticmethod
    def smart_split_into_chunks(text: str, max_length: int = 2000) -> List[str]:
        return K.smart_split_into_chunks(text, max_length)

    @staticmethod
    def get_text_stats(text: str) -> dict:
        return K.get_text_stats(text)
