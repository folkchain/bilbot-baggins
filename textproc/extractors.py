# -*- coding: utf-8 -*-
import io
import tempfile
import subprocess
from typing import List, Tuple

import pdfplumber
from pypdf import PdfReader

PAGE_BREAK = "\f"


def score_text(s: str) -> float:
    if not s or len(s) < 50:
        return 0.0
    n = len(s)
    letters = sum(ch.isalpha() for ch in s)
    spaces = s.count(" ")
    junk = s.count("\uFFFD") + s.count("�") + s.count("\x00")
    lines = s.splitlines()
    avg_line = (sum(len(l) for l in lines) / max(1, len(lines))) if lines else 0
    return (letters / n) * 0.45 + (spaces / n) * 0.15 + (avg_line / 120) * 0.25 - (junk / max(1, n)) * 0.20


def extract_with_pymupdf(file_bytes: bytes) -> str:
    try:
        import fitz  # PyMuPDF
    except Exception:
        return ""
    try:
        pages = []
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                txt = page.get_text("text") or ""
                pages.append(txt.strip())
        return (PAGE_BREAK + "\n").join(pages).strip()
    except Exception:
        return ""


def extract_with_pdfplumber(file_bytes: bytes) -> str:
    try:
        pages = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for p in pdf.pages:
                pages.append((p.extract_text() or "").strip())
        return (PAGE_BREAK + "\n").join(pages).strip()
    except Exception:
        return ""


def extract_with_pypdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            pages.append((page.extract_text() or "").strip())
        return (PAGE_BREAK + "\n").join(pages).strip()
    except Exception:
        return ""


def maybe_ocr(file_bytes: bytes) -> bytes:
    """
    Try OCR with ocrmypdf. Returns OCR'd PDF bytes or empty bytes on failure.
    Requires system packages: ocrmypdf and tesseract-ocr.
    Uses --force-ocr so bad existing OCR can be replaced.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as src, \
             tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as dst:
            src.write(file_bytes)
            src.flush()
            cmd = ["ocrmypdf", "--force-ocr", "--quiet", src.name, dst.name]
            subprocess.run(cmd, check=True)
            with open(dst.name, "rb") as f:
                return f.read()
    except Exception:
        return b""