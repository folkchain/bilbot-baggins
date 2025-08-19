# -*- coding: utf-8 -*-
import io
import tempfile
import subprocess
from typing import List, Tuple
import re

import pdfplumber
from pypdf import PdfReader

PAGE_BREAK = "\f"


def score_text(s: str) -> float:
    """Score text quality - higher is better."""
    if not s or len(s) < 50:
        return 0.0
    
    n = len(s)
    letters = sum(ch.isalpha() for ch in s)
    spaces = s.count(" ")
    words = s.split()
    
    # Check for jammed text (words too long)
    avg_word_len = sum(len(w) for w in words) / max(1, len(words))
    if avg_word_len > 15:  # Likely jammed
        return 0.1
    
    # Check for broken words like "t he" or "w as"
    broken_patterns = r'\b(t he|w as|i s|a re|h as|h ad|w ith|f rom|t hat|t his)\b'
    broken_count = len(re.findall(broken_patterns, s[:1000], re.IGNORECASE))
    if broken_count > 3:  # Too many broken words
        return 0.2
    
    junk = s.count("\uFFFD") + s.count("�") + s.count("\x00")
    lines = s.splitlines()
    avg_line = (sum(len(l) for l in lines) / max(1, len(lines))) if lines else 0
    
    # Better scoring that penalizes bad spacing
    score = (
        (letters / n) * 0.35 +  # Letters ratio
        (spaces / n) * 0.25 +   # Space ratio (important!)
        (1 - min(avg_word_len, 20) / 20) * 0.20 +  # Penalize long words
        (avg_line / 120) * 0.15 -  # Line length
        (junk / max(1, n)) * 0.30 -  # Junk characters
        (broken_count * 0.05)  # Broken words penalty
    )
    
    return max(0, score)


def fix_extraction_spacing(text: str) -> str:
    """Fix common spacing issues from PDF extraction."""
    # Fix broken common words
    broken_words = {
        r'\bt\s+he\b': 'the',
        r'\bw\s+as\b': 'was',
        r'\bi\s+s\b': 'is',
        r'\ba\s+re\b': 'are',
        r'\bw\s+ere\b': 'were',
        r'\bh\s+as\b': 'has',
        r'\bh\s+ad\b': 'had',
        r'\bh\s+ave\b': 'have',
        r'\bb\s+een\b': 'been',
        r'\bw\s+ith\b': 'with',
        r'\bf\s+rom\b': 'from',
        r'\bt\s+hat\b': 'that',
        r'\bt\s+his\b': 'this',
        r'\bw\s+hat\b': 'what',
        r'\ba\s+nd\b': 'and',
        r'\bf\s+or\b': 'for',
        r'\bn\s+ot\b': 'not',
        r'\bb\s+ut\b': 'but',
        r'\bo\s+f\b': 'of',
        r'\bi\s+n\b': 'in',
        r'\bt\s+o\b': 'to',
        r'\ba\s+t\b': 'at',
        r'\bo\s+n\b': 'on',
        r'\bi\s+t\b': 'it',
        r'\ba\s+s\b': 'as',
        r'\bb\s+y\b': 'by',
        r'\bm\s+y\b': 'my',
        r'\bw\s+e\b': 'we',
        r'\bh\s+e\b': 'he',
        r'\bm\s+e\b': 'me',
        r'\bn\s+o\b': 'no',
        r'\bd\s+o\b': 'do',
        r'\bi\s+f\b': 'if',
    }
    
    for pattern, replacement in broken_words.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Fix jammed words - add spaces at obvious boundaries
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
    
    return text


def extract_with_pymupdf(file_bytes: bytes) -> str:
    """Extract with PyMuPDF/fitz."""
    try:
        import fitz  # PyMuPDF
    except Exception:
        return ""
    
    try:
        pages = []
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page_num, page in enumerate(doc):
                # Try text extraction with different methods
                txt = page.get_text("text") or ""
                
                # If text seems bad, try blocks method
                if len(txt.split()) < 10 and page_num < 3:
                    blocks = page.get_text("blocks")
                    txt = " ".join(block[4] for block in blocks if block[6] == 0)
                
                pages.append(txt.strip())
        
        result = (PAGE_BREAK + "\n").join(pages).strip()
        # Fix spacing issues
        result = fix_extraction_spacing(result)
        return result
    except Exception:
        return ""


def extract_with_pdfplumber(file_bytes: bytes) -> str:
    """Extract with pdfplumber - often better for tables/layout."""
    try:
        pages = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for p in pdf.pages:
                # Use layout mode for better spacing
                txt = p.extract_text(layout=True) or ""
                if not txt:
                    # Fallback to normal extraction
                    txt = p.extract_text() or ""
                pages.append(txt.strip())
        
        result = (PAGE_BREAK + "\n").join(pages).strip()
        result = fix_extraction_spacing(result)
        return result
    except Exception:
        return ""


def extract_with_pypdf(file_bytes: bytes) -> str:
    """Extract with pypdf."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            txt = page.extract_text() or ""
            pages.append(txt.strip())
        
        result = (PAGE_BREAK + "\n").join(pages).strip()
        result = fix_extraction_spacing(result)
        return result
    except Exception:
        return ""


def force_ocr(file_bytes: bytes) -> bytes:
    """
    ALWAYS do OCR with best settings, even if PDF has text.
    Returns OCR'd PDF bytes or empty bytes on failure.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as src, \
             tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as dst:
            src.write(file_bytes)
            src.flush()
            
            # Use --force-ocr to redo OCR even if text exists
            # Use --optimize for better compression
            # Use --deskew to fix tilted scans
            # Use --clean to remove background noise
            cmd = [
                "ocrmypdf",
                "--force-ocr",  # Force OCR even if text layer exists
                "--optimize", "1",  # Optimize PDF
                "--deskew",  # Fix rotation
                "--clean",  # Clean background
                "--quiet",
                src.name,
                dst.name
            ]
            
            # Try with timeout
            subprocess.run(cmd, check=True, timeout=120)
            
            with open(dst.name, "rb") as f:
                return f.read()
    except subprocess.TimeoutExpired:
        # Try simpler OCR without optimization
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as src, \
                 tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as dst:
                src.write(file_bytes)
                src.flush()
                
                cmd = ["ocrmypdf", "--force-ocr", "--quiet", src.name, dst.name]
                subprocess.run(cmd, check=True, timeout=60)
                
                with open(dst.name, "rb") as f:
                    return f.read()
        except Exception:
            return b""
    except Exception:
        return b""


# Keep old name for compatibility but use new implementation
maybe_ocr = force_ocr