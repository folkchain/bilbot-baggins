# -*- coding: utf-8 -*-
from typing import List

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
        native = []
        for fn in (extract_with_pymupdf, extract_with_pdfplumber, extract_with_pypdf):
            txt = fn(file_bytes)
            native.append((txt, score_text(txt)))
        native_txt, native_score = max(native, key=lambda t: t[1]) if native else ("", 0.0)

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
    def clean_text(
        text: str,
        remove_running_headers: bool = True,
        remove_bottom_footnotes: bool = True,
    ) -> str:
        """
        Clean for TTS.
        - remove_running_headers: remove ONLY the first non-empty line per page if header-like (safer).
        - remove_bottom_footnotes: drop likely footnote blocks near page bottoms.
        Superscript/endnote markers are ALWAYS removed so they don't get read.
        """
        # Page-aware first pass (optional header removal)
        if remove_running_headers:
            text = C.strip_firstline_headers(text)

        # Fix hyphen/dash linebreaks before joining
        text = C.normalize_linebreak_hyphens(text)

        # Strip unreadables; keep italics (we don't touch italics anywhere)
        text = C.strip_underscores_and_unreadables(text)

        # Remove all quotes; keep apostrophes
        text = C.strip_all_quotes_keep_apostrophes(text)

        # Drop URLs/emails/citations/footnote markers/captions
        text = C.remove_unwanted(text)

        # Optional: bottom footnotes near page ends
        if remove_bottom_footnotes:
            text = C.drop_footnotes_at_bottom(text)

        # Remove known running header leftovers in case they slipped through
        if remove_running_headers:
            text = C.remove_known_header_lines(text)
            text = C.remove_all_caps_lines(text)

        # Join safe single newlines (leave paragraph breaks; final flatten below)
        text = C.join_wrapped_lines(text)

        # Ellipses -> period
        text = C.normalize_ellipses_to_period(text)

        # Number ranges
        text = C.tts_number_ranges(text)

        # Punctuation shaping
        text = C.tts_punctuation_shaping(text)
        text = C.smooth_article_commas(text)

        # NEW: remove hyphens/dashes between words (letter-letter only)
        text = C.dehyphenate_word_compounds(text)

        # Ensure missing spaces after punctuation and at digit/letter seams
        text = C.ensure_punctuation_spacing(text)

        # OCR nuisance fixes
        text = C.ocr_spaced_letters(text)
        text = C.ocr_digit_in_word_fixes(text)
        text = C.ocr_common_word_fixes(text)

        # Whitespace normalize (pre-flatten)
        text = C.clean_whitespace_and_punct(text)

        # FINAL: flatten to one single paragraph
        text = C.final_flatten_to_single_paragraph(text)
        return text

    # -------- Chunking & Stats --------

    @staticmethod
    def smart_split_into_chunks(text: str, max_length: int = 2200) -> List[str]:
        return K.smart_split_into_chunks(text, max_length)

    @staticmethod
    def get_text_stats(text: str) -> dict:
        return K.get_text_stats(text)
