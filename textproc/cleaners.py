# -*- coding: utf-8 -*-
import re
from .extractors import PAGE_BREAK

# =========================
# Page-aware helpers
# =========================

def _norm_line(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())

def _is_page_num(s: str) -> bool:
    s = s.strip()
    return bool(re.fullmatch(r"[ivxlcdm]+|[0-9]{1,4}", s, flags=re.IGNORECASE))

def _is_header_like(s: str) -> bool:
    s2 = s.strip()
    if len(s2) < 3 or len(s2) > 100:
        return False
    if re.search(r"[.!?]$", s2):
        return False
    letters = sum(ch.isalpha() for ch in s2)
    return letters >= max(10, int(len(s2) * 0.5))

def strip_running_headers_and_footers(text: str) -> str:
    """Remove repeated header/footer lines using page boundaries; fallback removes standalone page numbers."""
    if PAGE_BREAK not in text:
        lines = text.splitlines()
        kept = [ln for ln in lines if not _is_page_num(ln)]
        return "\n".join(kept)

    pages = [p.splitlines() for p in text.split(PAGE_BREAK)]
    freq = {}
    for lines in pages:
        body = [ln for ln in lines if ln.strip()]
        if not body:
            continue
        for seg in body[:3] + body[-5:]:
            n = _norm_line(seg)
            if n:
                freq[n] = freq.get(n, 0) + 1

    candidates = {n for n, c in freq.items() if c >= 3}

    new_pages = []
    for lines in pages:
        out = []
        for ln in lines:
            if not ln.strip():
                out.append(ln)
                continue
            n = _norm_line(ln)
            if n in candidates and _is_header_like(ln):
                continue
            if _is_page_num(ln):
                continue
            out.append(ln)
        new_pages.append("\n".join(out).strip())

    return ("\n" + PAGE_BREAK + "\n").join(new_pages).strip()

def drop_footnotes_at_bottom(text: str) -> str:
    """Drop likely footnote blocks near the page bottom — numbered short lines in the last ~20 visible lines."""
    if PAGE_BREAK not in text:
        return text

    pages = [p.splitlines() for p in text.split(PAGE_BREAK)]
    cleaned = []
    for lines in pages:
        if not lines:
            cleaned.append("")
            continue
        idxs = [i for i, ln in enumerate(lines) if ln.strip()]
        if not idxs:
            cleaned.append("\n".join(lines))
            continue
        end = idxs[-1]
        start = max(0, end - 20)
        new_lines = lines[:]
        for i in range(start, end + 1):
            s = lines[i].strip()
            if not s:
                continue
            # Typical footnote starts; conservative length limits
            if re.match(r"^\d{1,3}[\.\)]\s+\S", s) and len(s) <= 200:
                new_lines[i] = ""
            elif re.match(r"^\d{1,3}\s+\S", s) and len(s) <= 160:
                new_lines[i] = ""
        cleaned.append("\n".join([x for x in new_lines if x is not None]))
    return ("\n" + PAGE_BREAK + "\n").join(cleaned).strip()

def strip_toc_lines(text: str) -> str:
    """Remove TOC lines with dot leaders ending in a page number."""
    return re.sub(r"(?m)^[^\n]*\.{3,}\s*\d{1,4}\s*$", "", text)

def strip_chapter_headings(text: str) -> str:
    """Remove common chapter/section heading patterns including numerals and short ALL‑CAPS lines."""
    text = re.sub(r"(?m)^\s*(?:Chapter|CHAPTER)\s+[IVXLCDM\d]+[.:]?(?:\s+.+)?\s*$", "", text)
    text = re.sub(r"(?m)^\s*(?:[IVXLCDM]+|\d{1,3})[.)]?\s+[A-Z][^\n]{0,80}\s*$", "", text)
    text = re.sub(r"(?m)^(?=.{3,80}$)(?:[A-Z][A-Z\s&,'\-]{3,})$", "", text)
    return text

# =========================
# TTS‑focused normalization
# =========================

def normalize_linebreak_hyphens(text: str) -> str:
    """
    TTS‑first hyphen/dash normalization:
    - Remove soft hyphen U+00AD and normalize Hangul Kiyeok U+1100 to hyphen.
    - If a hyphen/dash appears at EOL then newline, drop and join words.
    - If hyphen/dash is immediately followed by a space inside a word, drop both and fuse.
    """
    # Remove soft hyphen globally
    text = re.sub(r"\u00AD", "", text)
    # Normalize Kiyeok to hyphen first
    text = re.sub(r"\u1100", "-", text)

    # End-of-line hyphen/dash -> remove and join next line
    text = re.sub(r"([A-Za-z])[\-–—\u2212]\s*\n\s*(?=[a-z])", r"\1", text)

    # Hyphen/dash immediately followed by space inside a word -> fuse
    text = re.sub(r"(\b[A-Za-z]+)[\-–—\u2212]\s+([A-Za-z]+\b)", r"\1\2", text)

    # Double-dash variants inside words -> fuse
    text = re.sub(r"(\b[A-Za-z]+)--\s*([A-Za-z]+\b)", r"\1\2", text)

    return text

def strip_underscores_and_unreadables(text: str) -> str:
    """
    Replace underscores with space, remove control chars (except LF/CR/TAB),
    and strip dingbats/ornaments/emoji/box-drawing the TTS would mangle.
    """
    text = text.replace("_", " ")

    # Remove control characters except TAB/CR/LF
    text = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", text)

    # Normalize weird spaces to regular space
    text = re.sub(r"[^\S\r\n]", " ", text)

    # Dingbats/ornaments/emoji/box-drawing/geometric/misc symbols
    ranges = [
        (0x2000, 0x200B), (0x2028, 0x202F), (0x2050, 0x206F),
        (0x2190, 0x21FF), (0x2200, 0x22FF), (0x2300, 0x23FF),
        (0x2460, 0x24FF), (0x2500, 0x257F), (0x2580, 0x259F),
        (0x25A0, 0x25FF), (0x2600, 0x26FF), (0x2700, 0x27BF),
        (0x2B00, 0x2BFF),
        (0x1F300, 0x1F5FF), (0x1F600, 0x1F64F), (0x1F680, 0x1F6FF),
        (0x1F700, 0x1F77F), (0x1F780, 0x1F7FF), (0x1F800, 0x1F8FF),
        (0x1F900, 0x1F9FF), (0x1FA00, 0x1FAFF),
    ]
    for start, end in ranges:
        pattern = f"[\\U{start:08X}-\\U{end:08X}]"
        text = re.sub(pattern, "", text)

    # Remove common bullets/ornaments directly
    text = re.sub(r"[•·◦●◻■◆◇★☆►▶▸▪▫♦☞➤➔➜➣➧➩➲]", "", text)

    return text

def strip_all_quotes_keep_apostrophes(text: str) -> str:
    """Remove every kind of quotation mark; keep apostrophes (normalize to straight)."""
    quote_chars = ['"', '“', '”', '„', '‟', '«', '»', '‹', '›', '〝', '〞', '＂', '˝', 'ˮ', '״', '`', '´', 'ˈ', 'ˊ', 'ʹ', 'ʺ']
    for ch in quote_chars:
        text = text.replace(ch, "")
    # Normalize apostrophes and KEEP them
    return text.replace("’", "'").replace("‚", "'").replace("‛", "'")

def strip_figure_table_caption_lines(text: str) -> str:
    """
    Drop single-line captions that OCR sometimes injects for figures/tables/charts/graphs/images.
    Conservative: only removes short lines starting with these words plus number/colon.
    """
    pattern = r"(?m)^\s*(?:Figure|Fig\.|Table|Chart|Graph|Illustration|Image)\s*(?:\d+|[A-Z])?[:.\-]?\s.{0,120}$"
    return re.sub(pattern, "", text)

def remove_unwanted(text: str) -> str:
    """Strip non-TTS content typical of PDFs/academic text, plus footnote markers."""
    # Standalone page numbers and explicit "Page N"
    text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", text)
    text = re.sub(r"(?m)^\s*Page\s+\d+.*$", "", text)

    # TOC and headings
    text = strip_toc_lines(text)
    text = strip_chapter_headings(text)

    # URLs and emails
    text = re.sub(r"https?://[^\s]+", "", text)
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "", text)

    # Parenthetical citations and bracketed numeric refs
    text = re.sub(r"\([A-Z][a-z]+,?\s+\d{4}\)", "", text)    # (Smith, 2019)
    text = re.sub(r"\[[0-9,\s\-]+\]", "", text)              # [1,2,3] or [1-5]

    # Footnote markers attached to words (keep punctuation)
    text = re.sub(r"(?<=\w)\d+(?=\s|$|[,.!?])", "", text)

    # Footnote markers AFTER punctuation or closing quote: e.g., .'3  or ”12
    text = re.sub(r'([\.\,\!\?\:\;\'"\)\]])\s*(?:\d{1,3}|[\u00B9\u00B2\u00B3\u2070-\u2079]+)', r'\1', text)

    # Superscript digits right after a word: word¹²³ → word
    text = re.sub(r'(?<=\w)[\u00B9\u00B2\u00B3\u2070-\u2079]+', '', text)

    # Caption lines injected by OCR
    text = strip_figure_table_caption_lines(text)

    return text

def join_wrapped_lines(text: str) -> str:
    """Join wrapped lines after hyphen normalization."""
    text = re.sub(r"([a-z,;])\s*\n(?=[a-z])", r"\1 ", text)
    text = re.sub(r"(?m)^(\w+)\s*\n(?=\w)", r"\1 ", text)
    return text

def normalize_ellipses_to_period(text: str) -> str:
    """
    Convert any ellipsis variant to a single period:
    ..., . . ., ...., . . . . .  →  .
    Avoid touching decimals (3.14) by requiring 3+ dots/spaced dots.
    """
    text = re.sub(r"(?<!\d)\.{3,}(?!\d)", ".", text)     # 3+ consecutive dots
    text = re.sub(r"(?:\.\s*){3,}", ".", text)           # spaced ellipses
    return text

# ---------- Numbers & punctuation shaping ----------

_SMALL_NUMBER_WORDS = {
    0:"zero",1:"one",2:"two",3:"three",4:"four",5:"five",6:"six",7:"seven",8:"eight",9:"nine",
    10:"ten",11:"eleven",12:"twelve",13:"thirteen",14:"fourteen",15:"fifteen",
    16:"sixteen",17:"seventeen",18:"eighteen",19:"nineteen",
    20:"twenty",30:"thirty",40:"forty",50:"fifty",60:"sixty",70:"seventy",80:"eighty",90:"ninety"
}

def _number_to_words_upto_9999(n: int) -> str:
    """English words for 0..9999 (enough for range narration)."""
    if n < 0 or n > 9999: return str(n)
    if n in _SMALL_NUMBER_WORDS: return _SMALL_NUMBER_WORDS[n]
    if n < 100:
        tens, ones = divmod(n,10)
        return _SMALL_NUMBER_WORDS[tens*10] + (f"-{_SMALL_NUMBER_WORDS[ones]}" if ones else "")
    if n < 1000:
        h, r = divmod(n,100)
        return _SMALL_NUMBER_WORDS[h] + (" hundred" + (f" {_number_to_words_upto_9999(r)}" if r else "")) 
    # 1000..9999
    th, r = divmod(n,1000)
    return _SMALL_NUMBER_WORDS[th] + (" thousand" + (f" {_number_to_words_upto_9999(r)}" if r else ""))

def tts_number_ranges(text: str) -> str:
    """
    Ranges:
      - Small numbers (<=20, or exact tens <=90) -> words: 5–7 → 'five to seven'
      - Larger numbers -> numeric: 1930–1940 → '1930 to 1940'
    Handles hyphen/en/em dash separators, with/without spaces.
    """
    def repl(m):
        a, b = int(m.group(1)), int(m.group(2))
        small = lambda x: x <= 20 or (x % 10 == 0 and x <= 90)
        if small(a) and small(b):
            return f"{_number_to_words_upto_9999(a)} to {_number_to_words_upto_9999(b)}"
        return f"{a} to {b}"
    return re.sub(r"(?<=\b)(\d{1,4})\s*[—–-]\s*(\d{1,4})(?=\b)", repl, text)

def tts_punctuation_shaping(text: str) -> str:
    """
    Make punctuation friendlier for TTS:
    - (After ranges) dashes used as punctuation -> comma + space
    - Colons -> commas, but keep times like 12:30 and ratios like 3:16
    """
    # En/em dashes used as punctuation (spaced or unspaced) -> comma + space
    text = re.sub(r"\s*[—–]\s*", ", ", text)

    # Colons -> commas unless both sides are digits (times/ratios)
    text = re.sub(r"(?<!\d):(?!\d)", ",", text)

    return text

def clean_whitespace_and_punct(text: str) -> str:
    """Whitespace & punctuation normalization and collapse."""
    # Remove blank lines / collapse large gaps
    text = re.sub(r"(?:\r?\n){3,}", "\n\n", text)

    # No space before punctuation; ensure space after sentence end
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([.?!])([A-Z])", r"\1 \2", text)

    # Strip trailing spaces and collapse multispace
    text = re.sub(r"(?m)[ \t]+$", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Tidy repeated punctuation
    text = re.sub(r",{3,}", ",", text)
    text = re.sub(r";{3,}", ";", text)
    text = re.sub(r":{3,}", ":", text)

    return text

# ---------- OCR spelling & acronym fixes ----------

def ocr_spaced_letters(text: str) -> str:
    """Join common spaced-letter OCR patterns."""
    text = re.sub(r"\b([A-Za-z])\s([A-Za-z])\s([A-Za-z])\s([A-Za-z])\s([A-Za-z])\b", r"\1\2\3\4\5", text)
    text = re.sub(r"\b([A-Za-z])\s([A-Za-z])\s([A-Za-z])\s([A-Za-z])\b", r"\1\2\3\4", text)
    text = re.sub(r"\b([A-Za-z])\s([A-Za-z])\s([A-Za-z])\b", r"\1\2\3", text)
    return text

def ocr_digit_in_word_fixes(text: str) -> str:
    """
    Fix digits mis-OCR'd inside words ONLY when surrounded by letters:
      0->o, 1->l (ell), 5->s, 6/8->b (rare), 3->e (very conservative)
    """
    text = re.sub(r"(?i)(?<=([A-Za-z]))0(?=([A-Za-z]))", "o", text)
    text = re.sub(r"(?i)(?<=([A-Za-z]))1(?=([A-Za-z]))", "l", text)
    text = re.sub(r"(?i)(?<=([A-Za-z]))5(?=([A-Za-z]))", "s", text)
    text = re.sub(r"(?i)(?<=([A-Za-z]))[68](?=([A-Za-z]))", "b", text)
    # '3'->'e' can be risky; only apply in common endings like '3r'->'er' / '3d'->'ed'
    text = re.sub(r"(?i)3(?=r\b)", "e", text)
    text = re.sub(r"(?i)3(?=d\b)", "e", text)
    return text

def ocr_common_word_fixes(text: str) -> str:
    """
    Targeted, safe-ish word-level fixes:
      0f→of, 0n→on, l'→I' at sentence start, 'the' capitalization at sentence start.
    """
    text = re.sub(r"(?i)\b0f\b", "of", text)
    text = re.sub(r"(?i)\b0n\b", "on", text)
    # Capitalize 'the' at sentence start if OCR produced lowercase after a period
    text = re.sub(r"(?m)(?<=[\.\!\?]\s)(the)\b", lambda m: m.group(1).capitalize(), text)
    # "l'" at sentence start often meant "I'"
    text = re.sub(r"(?m)^(l')", "I'", text)
    return text

def collapse_dotted_acronyms(text: str) -> str:
    """
    Turn U.S.A. / U. S. A. / U.S. into USA so TTS doesn't pause.
    """
    # U. S. A. -> USA  (allow 2-6 letters)
    def repl(m):
        letters = re.findall(r"[A-Za-z]", m.group(0))
        return "".join(letters)
    text = re.sub(r"\b(?:[A-Za-z]\.\s*){2,6}[A-Za-z]?\.?", repl, text)
    return text
