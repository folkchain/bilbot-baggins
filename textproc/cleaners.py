# -*- coding: utf-8 -*-
import re

# ============================================================================
# PRE-COMPILED REGEX PATTERNS (Module Level for Performance)
# ============================================================================

# Zero-width characters and control chars (use single backslashes in raw strings)
_ZW = re.compile(r"[\u200B\u200C\u200D\u2060\ufeff]")
_CTRL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

# Hyphen-like characters
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

# p. 12, pp. 12–14, (p. iv), etc.
_PAGE_CITATION_RE = re.compile(
    r"""(?ix)
        \(?
        \s*
        p{1,2}\.
        \s*
        (?:\d+|[ivxlcdm]+)
        (?:\s*[-–—]\s*(?:\d+|[ivxlcdm]+))?
        \s*
        \)?
        (?:\s*[.,;:])?
    """,
    re.VERBOSE | re.IGNORECASE,
)

_FOOTNOTE_START_RE = re.compile(r"^\s*(?:\d{1,3}[.)]|[*\u2020\u2021])\s+")

# Citation patterns
_URL_RE = re.compile(r"https?://[^\s]+")
_WWW_RE = re.compile(r"www\.[^\s]+")
_EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
_CITATION_RE = re.compile(r"\([A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s+\d{4}\)")

# Citation line prefixes
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

_FOOTNOTE_INLINE_RE = re.compile(
    r"\s*\d{1,3}(?![0-9-])\b"  # Standalone numbers (e.g., "31")
    r"|[(][\w\s,.]+[)]"  # Simple citations (e.g., "(ed.)")
)


def _remove_inline_footnotes(text: str) -> str:
    """Remove inline footnote markers and citations."""
    return _FOOTNOTE_INLINE_RE.sub("", text)


# Remove curly/smart quotes etc. Keep ASCII apostrophe ' for contractions.
_QUOTES_RE = re.compile(
    r"[\"`´“”‘’\u2018\u2019\u201A\u201B\u201C\u201D\u201E\u201F\u00AB\u00BB\u2039\u203A\u301D\u301E\uFF02\u02DD\u2032\u2035\u00B4\u02B9\u05F4]"
)

# Clause dashes of any kind (but NOT numeric ranges)
_DASH_CLAUSE_RE = re.compile(r"(?<!\d)\s*[–—-]\s*(?!\d)")

# Running header prefix at page start, even if fused with body text
_RUNNING_HEADER_PREFIX_RE = re.compile(
    r"^(?:CHAPTER\s+[IVXLCDM\d]+(?:\s+[A-Za-z][\w\-]{0,20}){0,4}"
    r"|[A-Z][A-Z &\-\.:]{3,80}"
    r"|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s+(?=[A-Z])"
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
_TXT_PAGE_NUM_RE = re.compile(r"^\s*(\d{1,4}|[ivxlcdm]{1,6})\s*$", re.IGNORECASE)
_TXT_SLASH_HDR_RE = re.compile(r"^\s*(?:\d{1,4}\s*/\s*.+|.+\s*/\s*\d{1,4})\s*$")
_TXT_FOOTNOTE_LINE_RE = re.compile(r"^\s*(?:\d{1,3}[.)]|[*\u2020\u2021])\s+")

# Use real form-feed and newline characters
PAGE_BREAK = "\f"

# --- Extra compiled patterns (new) ---
# Unicode "letter" class using stdlib re (no \p needed)
_LETTER_CLASS = r"[^\W\d_]"  # matches any Unicode letter; excludes digits and "_"
# Hyphen/em-dash between letters only (don’t touch numbers/dates)
_DASH_JOINED_WORDS_RE = re.compile(rf"(?<={_LETTER_CLASS})[-–—](?={_LETTER_CLASS})")
# em-dash between numbers (numeric ranges) → en dash "–"
_EMDASH_NUM_RANGE_RE = re.compile(r"(?<=\d)\s*—\s*(?=\d)")
# raw slashes and square brackets to drop in one pass
_BRACKETS_SLASH_RE = re.compile(r"[\\/[\]]")
# underscores → space
_UNDERSCORES_RE = re.compile(r"_+")
# runs of roman numerals in body text (2+ tokens) → remove
_ROMAN_RUN_RE = re.compile(
    r"(?:^|\s)(?:[IVXLCDM]{1,6})(?:\s+[IVXLCDM]{1,6}){1,}(?=\s|[.,;:!?]|$)"
)
# hyphen/dash between digits (for numeric ranges)
_HYPHEN_BETWEEN_DIGITS_RE = re.compile(r"(?<=\d)[-\u2010-\u2015\u2212](?=\d)")

# --- Extra compiled helpers to replace prior ad-hoc calls ---
_HARD_WRAP_JOIN_RE = re.compile(r"\s*\n\s*")  # used to join hard wraps in TXT
_MULTI_BLANKLINES_RE = re.compile(r"\n{3,}")  # collapse 3+ blank lines → 2
# Common running-header lead words at start of line
_HDR_KEYWORDS_RE = re.compile(
    r"^\s*(?:chapter|ch\.|part|book|section|sec\.|page|pp\.|volume|vol\.|no\.|number|issue|table|figure|fig\.)\b",
    re.IGNORECASE,
)
_HAS_DIGIT_RE = re.compile(r"\d")

# ============================================================================
# CORE UTILITIES
# ============================================================================


def simple_tts_clean(text: str) -> str:
    """Minimal pre-clean step: strip control chars, zero-width spaces, normalize whitespace."""
    if not text:
        return ""
    text = _ZW.sub("", text)
    text = _CTRL.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def strip_firstline_headers(text: str) -> str:
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

            # NEW: remove a header prefix even if the header is fused to body text
            m = _RUNNING_HEADER_PREFIX_RE.match(first_line)
            if m:
                first_line = first_line[m.end() :].lstrip()
                lines[first_idx] = first_line

            # Existing heuristics: pop obvious header-only first lines
            if (
                (_ROMAN_PAGE_RE.match(first_line) and len(first_line.split()) == 1)
                or (
                    _HDR_KEYWORDS_RE.search(first_line)
                    and _HAS_DIGIT_RE.search(first_line)
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


def final_flatten(text: str) -> str:
    """Flattens the entire text into a single, space-separated paragraph."""
    return re.sub(r"\s+", " ", text).strip()


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


def fix_punctuation_spacing(text: str) -> str:
    """Normalize punctuation spacing."""
    if not text:
        return ""
    text = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
    text = _PUNCT_NEEDS_SPACE_RE.sub(r"\1 \2", text)
    text = _MULTI_PUNCT_RE.sub(r"\1", text)
    return text


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines into single spaces, strip edges."""
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", text).strip()


def remove_footnote_markers(text: str) -> str:
    """Remove inline footnote markers and page-citation stubs."""
    if not text:
        return ""
    for pattern, replacement in _INLINE_FOOTNOTE_PATTERNS:
        text = pattern.sub(replacement, text)
    text = _PAGE_CITATION_RE.sub("", text)
    pages = text.split(PAGE_BREAK) if PAGE_BREAK in text else [text]
    cleaned_pages = []
    for page in pages:
        lines = page.splitlines()
        cut = len(lines)
        for i in range(len(lines) - 1, max(-1, len(lines) - 15), -1):
            if _FOOTNOTE_START_RE.match(lines[i]):
                if len(lines) - i <= 14 or i >= int(0.75 * len(lines)):
                    cut = i
                    break
        cleaned_pages.append("\n".join(lines[:cut]).rstrip())
    return (
        PAGE_BREAK.join(cleaned_pages)
        if PAGE_BREAK in text
        else "\n".join(cleaned_pages)
    )


def remove_all_quotes(text: str) -> str:
    if not text:
        return ""
    return _QUOTES_RE.sub("", text)


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


# ----------------------------------------------------------------------------
# Small helpers using compiled patterns (new)
# ----------------------------------------------------------------------------
def _clean_special_characters(text: str) -> str:
    """
    Normalize hyphens, handle em-dashes, drop quotes/brackets/slashes/underscores,
    and remove ellipses & empty brackets.
    """
    if not text:
        return ""
    # normalize hyphens; drop soft hyphen
    text = _HYPHEN_RE.sub("-", text).replace("\u00ad", "")
    # numeric ranges: various dashes between digits → en dash
    text = _HYPHEN_BETWEEN_DIGITS_RE.sub("–", text)
    text = _EMDASH_NUM_RANGE_RE.sub("–", text)  # 12—15 → 12–15
    # clause pause dash (—, –, -) → ", "  (but numeric ranges handled above)
    text = _DASH_CLAUSE_RE.sub(", ", text)
    # [ ] \ / → space
    text = _BRACKETS_SLASH_RE.sub(" ", text)
    # underscores → space
    text = _UNDERSCORES_RE.sub(" ", text)
    # remove special ascii garnish
    text = _SPECIAL_CHARS_RE.sub("", text)
    # ... and … ; empty () [] {}
    text = _ELLIPSIS_RE.sub("", text)
    text = _EMPTY_BRACKETS_RE.sub("", text)
    return text


def _remove_midtext_roman_runs(text: str) -> str:
    """Remove sequences like 'IV VII VIII …' in running text (keeps single tokens)."""
    if not text:
        return ""
    return _ROMAN_RUN_RE.sub(" ", text)
