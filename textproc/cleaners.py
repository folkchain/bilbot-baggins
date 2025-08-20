# -*- coding: utf-8 -*-
import re

# ============================================================================
# PRE-COMPILED REGEX PATTERNS (Module Level for Performance)
# ============================================================================

# Zero-width characters and control chars (use single backslashes in raw strings)
_ZW = re.compile(r"[\u200B\u200C\u200D\u2060\ufeff]")
_CTRL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

# Hyphen-like characters
# Removed invalid ranges and unrelated codepoints; kept practical dash/minus forms
_HYPHEN_CHARS = r"[-\u00AD\u2010\u2011\u2012\u2013\u2014\u2015\u2212\u2043\u05BE\u1400\u1806\u2E3A\u2E3B\uFE63\uFF0D\u30A0]"
_HYPHEN_RE = re.compile(_HYPHEN_CHARS)

# Line break hyphenation patterns
_HYPHEN_LINEBREAK_RE = re.compile(rf"([A-Za-z]){_HYPHEN_CHARS}\n([A-Za-z])")
_HYPHEN_MIDLINE_RE = re.compile(rf"(\b\w+){_HYPHEN_CHARS}\s+(\w+\b)")
_HYPHEN_SUFFIX_RE = re.compile(
    rf"([a-z]){_HYPHEN_CHARS}(ture|tion|ment|ness|ing|ed|er|est|ly|ity|ous|ive|ful|less|able|ible)(\s|$)",
    re.IGNORECASE,
)

# Footnote patterns
_INLINE_FOOTNOTE_PATTERNS = [
    (re.compile(r"\[\s*\d+\s*\]"), ""),  # [1] [23]
    (re.compile(r"\(\s*\d+\s*\)"), ""),  # (1) (23)
    (re.compile(r"([.!?,;:])\s*(\d{1,3})(?![\d-])\b"), r"\1"),  # punctuation+number
    (
        re.compile(r"[\u00B9\u00B2\u00B3\u2070-\u2079\u2020\u2021]+"),
        "",
    ),  # superscripts/daggers
]

# p. 12, pp. 12–14, (p. iv), etc., with optional parens and trailing punctuation
_PAGE_CITATION_RE = re.compile(
    r"""(?ix)                # flags: ignore case, verbose
        \(?                  # optional opening parenthesis
        \s*                  # optional whitespace
        p{1,2}\.             # 'p.' or 'pp.'
        \s*                  # optional whitespace
        (?:\d+|[ivxlcdm]+)   # page number (digits or roman)
        (?:\s*[-–—]\s*(?:\d+|[ivxlcdm]+))?  # optional range
        \s*                  # optional whitespace
        \)?                  # optional closing parenthesis
        (?:\s*[.,;:])?       # optional trailing punctuation
    """,
    re.VERBOSE | re.IGNORECASE,
)

_FOOTNOTE_START_RE = re.compile(r"^\s*(?:\d{1,3}[.)]|[*\u2020\u2021])\s+")

# Citation patterns
_URL_RE = re.compile(r"https?://[^\s]+")
_WWW_RE = re.compile(r"www\.[^\s]+")
_EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
_CITATION_RE = re.compile(r"\([A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s+\d{4}\)")

# Citation line prefixes (compiled with case-insensitive flag)
_CITATION_LINE_PATTERNS = [
    re.compile(r"^op\.?\s*cit\.?", re.I),
    re.compile(r"^ibid\.?", re.I),
    re.compile(r"^loc\.?\s*cit\.?", re.I),
    re.compile(r"^cf\.?", re.I),
    re.compile(r"^et\s+al\.?", re.I),
    re.compile(r"^supra\.?", re.I),
    re.compile(r"^infra\.?", re.I),
    re.compile(r"^passim\.?", re.I),
    re.compile(r"^ff\.?", re.I),
    re.compile(r"^see\s+(also\s+)?", re.I),
    re.compile(r"^nota\s+bene\.?", re.I),
    re.compile(r"^n\.?b\.?", re.I),
    re.compile(r"^vide\.?", re.I),
    re.compile(r"^viz\.?", re.I),
    re.compile(r"^i\.?e\.?", re.I),
    re.compile(r"^e\.?g\.?", re.I),
]

# Quote characters pattern — complete, single character class
_QUOTES_RE = re.compile(
    r"""["'`´“”‘’\u2018\u2019\u201A\u201B\u201C\u201D\u201E\u201F
         \u00AB\u00BB\u2039\u203A\u301D\u301E\uFF02\u02DD
         \u2032\u2035\u00B4\u02B9\u05F4]""",
    re.VERBOSE,
)

# Special characters to remove
_SPECIAL_CHARS_RE = re.compile(r"[+*~|^]+")
_ELLIPSIS_RE = re.compile(r"\.{2,}|…")
_EMPTY_BRACKETS_RE = re.compile(r"\(\s*\)|\[\s*\]|\{\s*\}")

# Punctuation spacing patterns
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.!?;:])")
_PUNCT_NEEDS_SPACE_RE = re.compile(r"([,.!?;:])([A-Za-z0-9])")
_MULTI_PUNCT_RE = re.compile(r"([,.!?;:])[,.!?;:]+")

# Whitespace normalization
_WHITESPACE_RE = re.compile(r"\s+")

# Page number patterns
_PAGE_NUMBER_RE = re.compile(r"^\d+$")
_ROMAN_PAGE_RE = re.compile(r"^[divxlcdm]+$", re.IGNORECASE)

# --- TXT-specific line patterns ---
# (keep your imports and compiled regexes above intact)

# Isolated page numbers or roman numerals (commonly dumped into TXT exports)
_TXT_PAGE_NUM_RE = re.compile(r"^\s*(\d{1,4}|[ivxlcdm]{1,6})\s*$", re.IGNORECASE)

# Slash headings like "The Image as Guide / 17" or "20 / The Hero…"
_TXT_SLASH_HDR_RE = re.compile(r"^\s*(?:\d{1,4}\s*/\s*.+|.+\s*/\s*\d{1,4})\s*$")

# Classic footnote line starters in body text
_TXT_FOOTNOTE_LINE_RE = re.compile(r"^\s*(?:\d{1,3}[.)]|[*\u2020\u2021])\s+")

# Use real form-feed and newline characters
PAGE_BREAK = "\f"


def strip_firstline_headers(text: str) -> str:
    """Remove first line headers from pages - optimized."""
    if not text:
        return ""
    pages = text.split(PAGE_BREAK) if PAGE_BREAK in text else [text]
    cleaned_pages = []
    for page in pages:
        lines = page.strip().split("\n")
        if not lines:
            continue
        first_idx = next((i for i, line in enumerate(lines) if line.strip()), -1)
        if first_idx != -1:
            first_line = lines[first_idx].strip()
            if (
                (_ROMAN_PAGE_RE.match(first_line) and len(first_line.split()) == 1)
                or (
                    re.search(r"\b(Chapter|Page|Years)\b", first_line, re.I)
                    and re.search(r"\d", first_line)
                )
                or (
                    len(first_line.split()) < 10
                    and not first_line.endswith((".", "!", "?"))
                )
            ):
                lines.pop(first_idx)
        cleaned_pages.append("\n".join(lines))
    return (
        PAGE_BREAK.join(cleaned_pages)
        if PAGE_BREAK in text
        else "\n".join(cleaned_pages)
    )


def remove_bottom_page_numbers(text: str) -> str:
    """Remove page numbers at end of pages - optimized."""
    if not text:
        return ""
    pages = text.split(PAGE_BREAK) if PAGE_BREAK in text else [text]
    cleaned_pages = []
    for page in pages:
        lines = page.strip().split("\n")
        if not lines:
            continue
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip():
                if _PAGE_NUMBER_RE.match(lines[i].strip()):
                    lines.pop(i)
                break
        cleaned_pages.append("\n".join(lines))
    return (
        PAGE_BREAK.join(cleaned_pages)
        if PAGE_BREAK in text
        else "\n".join(cleaned_pages)
    )


def fix_line_break_hyphenation(text: str) -> str:
    """Fix hyphenated words - optimized with single pass."""
    if not text:
        return ""
    text = _HYPHEN_LINEBREAK_RE.sub(r"\1\2", text)
    text = _HYPHEN_MIDLINE_RE.sub(r"\1\2", text)
    text = _HYPHEN_SUFFIX_RE.sub(r"\1\2\3", text)
    return text


def join_paragraphs_smart(text: str) -> str:
    """Join lines into paragraphs - optimized (PDF/page-based)."""
    if not text:
        return ""
    text = text.replace("\f", "\n\n")
    paragraphs = text.split("\n\n")
    cleaned = []
    for p in paragraphs:
        p = p.strip()
        if p:
            cleaned.append(_WHITESPACE_RE.sub(" ", p.replace("\n", " ")))
    return "\n\n".join(cleaned)


def _detect_repeated_headers(lines, min_hits: int = 3) -> set[str]:
    """Find short lines that repeat like running headers in TXT dumps."""
    from collections import Counter

    cand = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if len(s) <= 80 and not s.endswith((".", "!", "?", ":", ";")):
            if not _TXT_PAGE_NUM_RE.match(s):
                cand.append(s)
    freq = Counter(cand)
    return {s for s, n in freq.items() if n >= min_hits}


def clean_txt_headers_and_footnotes(text: str) -> str:
    """
    TXT cleaner (no page breaks). Removes:
      - repeated running headers
      - isolated page numbers (arabic/roman)
      - slash headings ('Title / 23' or '20 / Title')
      - classic footnote starters ('12) ...', '† ...')
      - inline page citations '(p. 12)', '(pp. 12–14)'
    """
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _PAGE_CITATION_RE.sub("", text)
    lines = text.split("\n")
    headers = _detect_repeated_headers(lines)

    cleaned = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            cleaned.append(ln)
            continue
        if s in headers:
            continue
        if _TXT_PAGE_NUM_RE.match(s):
            prev_blank = (i - 1 < 0) or (not lines[i - 1].strip())
            next_blank = (i + 1 >= len(lines)) or (not lines[i + 1].strip())
            if prev_blank or next_blank:
                continue
        if _TXT_SLASH_HDR_RE.match(s):
            continue
        if _TXT_FOOTNOTE_LINE_RE.match(s):
            prev_blank = (i - 1 < 0) or (not lines[i - 1].strip())
            if prev_blank or len(s.split()) <= 14:
                continue
        cleaned.append(ln)

    out = "\n".join(cleaned)
    for pattern, replacement in _INLINE_FOOTNOTE_PATTERNS:
        out = pattern.sub(replacement, out)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


def fix_punctuation_spacing(text: str) -> str:
    """Use existing compiled patterns to normalize punctuation spacing."""
    if not text:
        return ""
    # remove spaces before punctuation
    text = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
    # ensure a single space after punctuation when followed by a word/number
    text = _PUNCT_NEEDS_SPACE_RE.sub(r"\1 \2", text)
    # collapse runs of punctuation like "?!..." to a single mark of the first type
    text = _MULTI_PUNCT_RE.sub(r"\1", text)
    return text


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines into single spaces, strip edges."""
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", text).strip()


def simple_tts_clean(text: str) -> str:
    """Minimal pre-clean step: strip control chars, zero-width spaces, normalize whitespace."""
    if not text:
        return ""
    text = _ZW.sub("", text)  # zero-width chars
    text = _CTRL.sub("", text)  # control chars
    text = _WHITESPACE_RE.sub(" ", text)  # collapse spaces
    return text.strip()


def join_paragraphs_smart_txt(text: str) -> str:
    """Join hard-wrapped lines within paragraphs for TXT, keep blank-line breaks."""
    if not text:
        return ""
    paras = [p.strip() for p in text.split("\n\n")]
    out = []
    for p in paras:
        if not p:
            out.append("")
            continue
        p = re.sub(r"\s*\n\s*", " ", p)
        p = _WHITESPACE_RE.sub(" ", p).strip()
        out.append(p)
    return "\n\n".join(out)


def remove_footnote_markers(text: str) -> str:
    """Remove inline footnote markers and page-citation stubs."""
    if not text:
        return ""
    # Inline markers like [12], (3), punctuation+12, superscripts/daggers
    for pattern, replacement in _INLINE_FOOTNOTE_PATTERNS:
        text = pattern.sub(replacement, text)
    # (p. 12), (pp. 12–14), etc.
    text = _PAGE_CITATION_RE.sub("", text)

    # Also trim short footnote blocks near page bottoms if form-feeds exist
    pages = text.split(PAGE_BREAK) if PAGE_BREAK in text else [text]
    cleaned_pages = []
    for page in pages:
        lines = page.splitlines()
        cut = len(lines)
        # scan up to ~15 lines from bottom
        for i in range(len(lines) - 1, max(-1, len(lines) - 15), -1):
            if _FOOTNOTE_START_RE.match(lines[i]):
                # typical footnote zone: last ~¼ of page or within last 14 lines
                if len(lines) - i <= 14 or i >= int(0.75 * len(lines)):
                    cut = i
                    break
        cleaned_pages.append("\n".join(lines[:cut]).rstrip())
    return (
        PAGE_BREAK.join(cleaned_pages)
        if PAGE_BREAK in text
        else "\n".join(cleaned_pages)
    )


def remove_references(text: str) -> str:
    """Strip URLs, emails, and (Author, 1999)-style parenthetical cites."""
    if not text:
        return ""
    text = _URL_RE.sub("", text)
    text = _WWW_RE.sub("", text)
    text = _EMAIL_RE.sub("", text)
    text = _CITATION_RE.sub("", text)
    return text


def remove_citation_lines(text: str) -> str:
    """Drop lines that begin with scholarly citation prefixes (ibid., cf., etc.)."""
    if not text:
        return ""
    lines = text.split("\n")
    kept = []
    for line in lines:
        s = line.strip()
        if not s:
            kept.append(line)
            continue
        if any(pat.match(s) for pat in _CITATION_LINE_PATTERNS):
            continue
        kept.append(line)
    return "\n".join(kept)


def _looks_paged(text: str) -> bool:
    """Detect whether page-aware logic is safe: real form feeds or very regular page lines."""
    if "\f" in text:
        return True
    lines = text.split("\n")
    hits = 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if _TXT_PAGE_NUM_RE.match(s):
            prev_blank = (i == 0) or (not lines[i - 1].strip())
            next_blank = (i == len(lines) - 1) or (not lines[i + 1].strip())
            if prev_blank or next_blank:
                hits += 1
    return hits >= max(5, len(lines) // 80)  # ~1 marker per 80 lines or at least 5


def clean_document(
    text: str,
    kind: str,
    remove_headers: bool = True,
    remove_footnotes: bool = True,
    *,
    allow_fallback: bool = True,
    fallback_floor_ratio: float = 0.001,  # 0.1% floor
    fallback_abs_min: int = 50,
) -> str:
    """
    Router for TXT vs PDF cleaning.
      - TXT: TXT heuristics (no page logic).
      - PDF: page-aware functions, respecting toggles.
      - Fallback is VERY conservative (only if almost everything got deleted).
    """
    if not text:
        return ""

    original = text
    text = simple_tts_clean(text)  # minimal sanitize

    if kind and kind.lower() == "txt":
        # ---------------- TXT path ----------------
        raw_len = len(text)

        # inline page cites etc.
        text = _PAGE_CITATION_RE.sub("", text)

        # run hyphen fix BEFORE joining so "Emigra-\n tion" -> "Emigration"
        text = fix_line_break_hyphenation(text)

        # structural TXT cleanup you already have
        text = clean_txt_headers_and_footnotes(text)
        text = join_paragraphs_smart_txt(text)

        # remove underscores
        text = re.sub(r"_+", " ", text)

        # domain tweak near the end
        text = re.sub(r"\bforeign-born\b", "foreign born", text, flags=re.IGNORECASE)

        # final polish you already have
        text = fix_punctuation_spacing(text)
        text = normalize_whitespace(text)

        if allow_fallback:
            floor = max(fallback_abs_min, int(fallback_floor_ratio * max(1, raw_len)))
            if len(text.strip()) < floor:
                text = normalize_whitespace(original)

        return text

    else:
        # ---------------- PDF path ----------------
        if remove_headers:
            text = strip_firstline_headers(text)
            text = remove_bottom_page_numbers(text)

        text = fix_line_break_hyphenation(text)

        if remove_footnotes:
            text = remove_footnote_markers(text)
            text = remove_citation_lines(text)
            text = remove_references(text)
        else:
            text = _PAGE_CITATION_RE.sub("", text)

        text = join_paragraphs_smart(text)
        text = fix_punctuation_spacing(text)
        text = normalize_whitespace(text)

        if allow_fallback:
            floor = max(
                fallback_abs_min, int(fallback_floor_ratio * max(1, len(original)))
            )
            if len(text.strip()) < floor:
                text = normalize_whitespace(original)

        return text
