# -*- coding: utf-8 -*-
from typing import List
import re

from .extractors import (
    PAGE_BREAK,
    score_text,
    extract_with_pymupdf,
    extract_with_pdfplumber,
    extract_with_pypdf,
    force_ocr,
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
        """
        Enhanced PDF reading that prioritizes OCR for better quality.
        """
        # (The content of this method is correct, no changes needed here)
        # ... (rest of the read_pdf_file method)
         # --- File Type Verification ---
        if not file_bytes.startswith(b'%PDF-'):
            print("ERROR: Uploaded file is not a valid PDF.")
            # Use st.error in app.py, but here we return empty and handle it there
            return "ERROR: Not a valid PDF file."
        
        native_results = []
        
        txt = extract_with_pdfplumber(file_bytes)
        if txt:
            native_results.append((txt, score_text(txt), "pdfplumber"))
        
        txt = extract_with_pymupdf(file_bytes)
        if txt:
            native_results.append((txt, score_text(txt), "pymupdf"))
        
        txt = extract_with_pypdf(file_bytes)
        if txt:
            native_results.append((txt, score_text(txt), "pypdf"))
        
        if native_results:
            best_native = max(native_results, key=lambda x: x[1])
            native_txt, native_score, native_method = best_native
        else:
            native_txt, native_score, native_method = "", 0.0, "none"
        
        ocr_txt, ocr_score = "", 0.0
        print("Running OCR for best quality text extraction...")
        ocr_pdf = force_ocr(file_bytes)
        
        if ocr_pdf:
            ocr_results = []
            
            txt = extract_with_pdfplumber(ocr_pdf)
            if txt:
                ocr_results.append((txt, score_text(txt)))
            
            txt = extract_with_pymupdf(ocr_pdf)
            if txt:
                ocr_results.append((txt, score_text(txt)))
            
            txt = extract_with_pypdf(ocr_pdf)
            if txt:
                ocr_results.append((txt, score_text(txt)))
            
            if ocr_results:
                ocr_txt, ocr_score = max(ocr_results, key=lambda x: x[1])
        
        if ocr_score > native_score * 1.1:
            print(f"Using OCR result (score: {ocr_score:.2f})")
            best_txt = ocr_txt
        else:
            print(f"Using native {native_method} (score: {native_score:.2f})")
            best_txt = native_txt
        
        if best_txt:
            sample = best_txt[:500]
            words = sample.split()
            if words:
                avg_word_len = sum(len(w) for w in words) / len(words)
                if avg_word_len > 12:
                    print("Warning: Text may have spacing issues, applying fixes...")
                    best_txt = re.sub(r'([a-z])([A-Z])', r'\1 \2', best_txt)
                    best_txt = re.sub(r'([.!?])([A-Z])', r'\1 \2', best_txt)
        
        return best_txt.strip()

    # -------- Cleaning --------

    # CORRECT INDENTATION STARTS HERE
    @staticmethod
    def clean_text(
        text: str,
        remove_running_headers: bool = True,
        remove_bottom_footnotes: bool = True,
    ) -> str:
        """
        Clean text for TTS using a streamlined and robust pipeline.
        """
        if not text:
            return ""

        # 1. Perform initial structural cleaning on the raw text.
        text = C.remove_all_quotes(text)
        text = C.fix_line_break_hyphenation(text)
        text = C.remove_bottom_page_numbers(text)
        if remove_running_headers:
            text = C.strip_firstline_headers(text)

        # 3. Remove non-content elements.
        if remove_bottom_footnotes:
            text = C.remove_footnote_markers(text)
        text = C.remove_references(text)
        text = C.remove_citation_lines(text)

        # 4. Clean the actual content.
        text = C.join_paragraphs_smart(text)
        text = C.clean_special_characters(text)
        text = C.fix_punctuation_spacing(text)
        
        # 5. Perform a final validation check.
        text = C.validate_and_fix_spacing(text)
        
        # 6. Finally, flatten the text.
        text = C.final_flatten(text)
        
        return text.strip()

    # -------- Chunking & Stats --------

    @staticmethod
    def smart_split_into_chunks(text: str, max_length: int = 2200) -> List[str]:
        return K.smart_split_into_chunks(text, max_length)

    @staticmethod
    def get_text_stats(text: str) -> dict:
        return K.get_text_stats(text)