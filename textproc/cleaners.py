# -*- coding: utf-8 -*-
import re
from .extractors import PAGE_BREAK

# ---------- Page-aware helpers ----------

def _norm_line(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())

def _is_page_num_token(s: str) -> bool:
    s = s.strip()
    return bool(re.fullmatch(r"[ivxlcdm]+|[0-9]{1,4}", s, flags=re.IGNORECASE))

def _looks_like_header(s: str) -> bool:
    """Heuristic for chapter/book headers (no terminal punctuation; mostly letters; not too long)."""
    s2 = s.strip()
    if not s2:
        return False
    if re.search(r"[.!?]$", s2):
        return False
    if len(s2) > 120 or len(s2) < 3:
        return False
    letters = sum(ch.isalpha() for ch in s2)
    return letters >= max(8, int(len(s2) * 0.45))

def remove_all_caps_lines(text: str) -> str:
    """
    Delete lines that are entirely capitalized (ignoring digits/spaces/punct),
    used only where we call it (not page-position constrained).
    """
    lines = text.splitlines()
    kept = []
    for ln in lines:
        letters = re.findall(r"[A-Za-z]", ln)
        if letters and all(ch.isupper() for ch in letters):
            continue
        kept.append(ln)
    return "\n".join(kept)

def remove_known_header_lines(text: str) -> str:
    """Remove OCR header variants like 'The Southern Writer 6' (when used)."""
    return re.sub(r"(?im)^\s*the\s+southern\s+writer\s+\d+\s*$", "", text)

# ---------- New: FIRST-LINE-ONLY running header removal ----------

def strip_firstline_headers(text: str) -> str:
    """
    Remove ONLY the first non-blank line of each page IFF it looks like a header:
      - a page number token, OR
      - all-caps line, OR
      - header-like by heuristic above, OR
      - known series like 'The Southern Writer N'
    Bottom-of-page content is NOT touched here.
    """
    if PAGE_BREAK not in text:
        # Single page: only remove if it's the very first non-empty line
        lines = text.splitlines()
        # find first non-empty index
        idx = next((i for i, ln in enumerate(lines) if ln.strip()), None)
        if idx is None:
            return text
        cand = lines[idx]
        letters = re.findall(r"[A-Za-z]", cand)
        is_all_caps = bool(letters) and all(ch.isupper() for ch in letters)
        if (
            _is_page_num_token(cand)
            or is_all_caps
            or _looks_like_header(cand)
            or re.fullmatch(r"(?i)\s*the\s+southern\s+writer\s+\d+\s*", cand or "")
        ):
            lines[idx] = ""
        return "\n".join(l for l in lines if l is not None)

    pages = text.split(PAGE_BREAK)
    new_pages = []
    for p in pages:
        lines = p.splitlines()
        # find first non-empty
        idx = next((i for i, ln in enumerate(lines) if ln.strip()), None)
        if idx is not None:
            cand = lines[idx]
            letters = re.findall(r"[A-Za-z]", cand)
            is_all_caps = bool(letters) and all(ch.isupper() for ch in letters)
            if (
                _is_page_num_token(cand)
                or is_all_caps
                or _looks_like_header(cand)
                or re.fullmatch(r"(?i)\s*the\s+southern\s+writer\s+\d+\s*", cand or "")
            ):
                lines[idx] = ""
        new_pages.append("\n".join(lines))
    return ("\n" + PAGE_BREAK + "\n").join(new_pages)

# ---------- Optional bottom-footnote block removal (guarded by UI) ----------

def drop_footnotes_at_bottom(text: str) -> str:
    """Drop likely footnote blocks near the page bottom — numbered short lines in the last ~20 visible lines."""
    if PAGE_BREAK not in text:
        # fall back: try last ~20 non-empty lines of whole doc (conservative)
        lines = text.splitlines()
        idxs = [i for i, ln in enumerate(lines) if ln.strip()]
        if not idxs:
            return text
        end = idxs[-1]
        start = max(0, end - 20)
        new_lines = lines[:]
        for i in range(start, end + 1):
            s = lines[i].strip()
            if re.match(r"^\d{1,3}[\.\)]\s+\S", s) and len(s) <= 200:
                new_lines[i] = ""
            elif re.match(r"^\d{1,3}\s+\S", s) and len(s) <= 160:
                new_lines[i] = ""
        return "\n".join(new_lines)

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
            if re.match(r"^\d{1,3}[\.\)]\s+\S", s) and len(s) <= 200:
                new_lines[i] = ""
            elif re.match(r"^\d{1,3}\s+\S", s) and len(s) <= 160:
                new_lines[i] = ""
        cleaned.append("\n".join(new_lines))
    return ("\n" + PAGE_BREAK + "\n").join(cleaned)

# ---------- TTS‑focused normalization (same as previous, trimmed for brevity) ----------

# ---------- Hyphenation & newline handling ----------
def normalize_linebreak_hyphens(text: str) -> str:
    # Remove soft hyphen and the Kiyeok OCR artifact
    text = text.replace("\u00AD", "")   # soft hyphen
    text = text.replace("\u1100", "-")  # Kiyeok → hyphen for consistency

    # End-of-line hyphenation: neu-\ntrality → neutrality  (only real hyphen)
    text = re.sub(r"([A-Za-z])-\s*\n\s*([a-z])", r"\1\2", text)

    # Leave dashes that are punctuation (– —) for later steps
    return text

def strip_underscores_and_unreadables(text: str) -> str:
    text = text.replace("_", " ")
    text = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", text)
    text = re.sub(r"[^\S\r\n]", " ", text)
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
        text = re.sub(f"[\\U{start:08X}-\\U{end:08X}]", "", text)
    text = re.sub(r"[•·◦●◻■◆◇★☆►▶▸▪▫♦☞➤➔➜➣➧➩➲*]", "", text)
    return text

def strip_all_quotes_keep_apostrophes(text: str) -> str:
    for ch in ['"', '“', '”', '„', '‟', '«', '»', '‹', '›', '〝', '〞', '＂', '˝', 'ˮ', '״', '`', '´', 'ˈ', 'ˊ', 'ʹ', 'ʺ']:
        text = text.replace(ch, "")
    return text.replace("’", "'").replace("‚", "'").replace("‛", "'")

def strip_figure_table_caption_lines(text: str) -> str:
    pattern = r"(?m)^\s*(?:Figure|Fig\.|Table|Chart|Graph|Illustration|Image)\s*(?:\d+|[A-Z])?[:.\-]?\s.{0,120}$"
    return re.sub(pattern, "", text)

def remove_unwanted(text: str) -> str:
    # NOTE: page-number removal here is **disabled**; we do it only via first-line header logic.
    # URLs / emails
    text = re.sub(r"https?://[^\s]+", "", text)
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "", text)
    # Parenthetical citations and [num] refs
    text = re.sub(r"\([A-Z][a-z]+,?\s+\d{4}\)", "", text)
    text = re.sub(r"\[[0-9,\s\-]+\]", "", text)
    # Footnote markers attached or after punctuation + superscripts (ALWAYS remove superscripts/endnote markers)
    text = re.sub(r"(?<=\w)\d+(?=\s|$|[,.!?])", "", text)
    text = re.sub(r'([\.\,\!\?\:\;\'"\)\]])\s*(?:\d{1,3}|[\u00B9\u00B2\u00B3\u2070-\u2079]+)', r'\1', text)
    text = re.sub(r'(?<=\w)[\u00B9\u00B2\u00B3\u2070-\u2079]+', '', text)
    # OCR caption lines
    text = strip_figure_table_caption_lines(text)
    return text

def join_wrapped_lines(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)   # normalize big gaps temporarily
    text = re.sub(r"(?<=\w)\n(?=\w)", " ", text)      # word\nword -> space
    text = re.sub(r"(?<=[,;:])\n(?=\w)", " ", text)   # comma/colon newline word -> space
    return text

def normalize_ellipses_to_period(text: str) -> str:
    text = text.replace("…", "...")
    text = re.sub(r"(?<!\d)\.{3,}(?!\d)", ".", text)
    text = re.sub(r"(?:\.\s*){3,}", ".", text)
    return text

# ---------- Numbers & punctuation shaping ----------

_SMALL_NUMBER_WORDS = {
    0:"zero",1:"one",2:"two",3:"three",4:"four",5:"five",6:"six",7:"seven",8:"eight",9:"nine",
    10:"ten",11:"eleven",12:"twelve",13:"thirteen",14:"fourteen",15:"fifteen",
    16:"sixteen",17:"seventeen",18:"eighteen",19:"nineteen",
    20:"twenty",30:"thirty",40:"forty",50:"fifty",60:"sixty",70:"seventy",80:"eighty",90:"ninety"
}

def _number_to_words_upto_9999(n: int) -> str:
    if n < 0 or n > 9999: return str(n)
    if n in _SMALL_NUMBER_WORDS: return _SMALL_NUMBER_WORDS[n]
    if n < 100:
        t,o = divmod(n,10)
        return _SMALL_NUMBER_WORDS[t*10] + (f"-{_SMALL_NUMBER_WORDS[o]}" if o else "")
    if n < 1000:
        h,r = divmod(n,100)
        return _SMALL_NUMBER_WORDS[h] + (" hundred" + (f" {_number_to_words_upto_9999(r)}" if r else "")) 
    th,r = divmod(n,1000)
    return _SMALL_NUMBER_WORDS[th] + (" thousand" + (f" {_number_to_words_upto_9999(r)}" if r else ""))

def tts_number_ranges(text: str) -> str:
    def repl(m):
        a, b = int(m.group(1)), int(m.group(2))
        small = lambda x: x <= 20 or (x % 10 == 0 and x <= 90)
        if small(a) and small(b):
            return f"{_number_to_words_upto_9999(a)} to {_number_to_words_upto_9999(b)}"
        return f"{a} to {b}"
    return re.sub(r"(?<=\b)(\d{1,4})\s*[—–-]\s*(\d{1,4})(?=\b)", repl, text)

def tts_punctuation_shaping(text: str) -> str:
    # Em dash → comma+space, regardless of surrounding spaces
    text = re.sub(r"\s*—\s*", ", ", text)
    # Keep times/ratios; otherwise colon → comma
    text = re.sub(r"(?<!\d):(?!\d)", ",", text)
    return text

# Hyphen & dash removal between words (after number ranges & dash shaping)
def dehyphenate_word_compounds(text: str) -> str:
    # Replace hyphen, non-breaking hyphen, figure/en dash between letters with a single space
    # U+2010 hyphen, U+2011 non-breaking hyphen, U+2012 figure dash, U+2013 en dash
    text = re.sub(
        r"(?i)\b([A-Za-z]+)\s*[-\u2010\u2011\u2012\u2013]\s*([A-Za-z]+)\b",
        r"\1 \2",
        text,
    )
    return text

def smooth_article_commas(text: str) -> str:
    return re.sub(r"\b(?:the|a|an|of|in|to)\s*,\s+", lambda m: m.group(0).replace(",", ""), text, flags=re.IGNORECASE)

# ---------- OCR spelling & acronym fixes ----------

def ocr_spaced_letters(text: str) -> str:
    text = re.sub(r"\b([A-Za-z])\s([A-Za-z])\s([A-Za-z])\s([A-Za-z])\s([A-Za-z])\b", r"\1\2\3\4\5", text)
    text = re.sub(r"\b([A-Za-z])\s([A-Za-z])\s([A-Za-z])\s([A-Za-z])\b", r"\1\2\3\4", text)
    text = re.sub(r"\b([A-Za-z])\s([A-Za-z])\s([A-Za-z])\b", r"\1\2\3", text)
    return text

def ocr_digit_in_word_fixes(text: str) -> str:
    text = re.sub(r"(?i)(?<=([A-Za-z]))0(?=([A-Za-z]))", "o", text)
    text = re.sub(r"(?i)(?<=([A-Za-z]))1(?=([A-Za-z]))", "l", text)
    text = re.sub(r"(?i)(?<=([A-Za-z]))5(?=([A-Za-z]))", "s", text)
    text = re.sub(r"(?i)(?<=([A-Za-z]))[68](?=([A-Za-z]))", "b", text)
    text = re.sub(r"(?i)3(?=r\b)", "e", text)
    text = re.sub(r"(?i)3(?=d\b)", "e", text)
    return text

def ocr_common_word_fixes(text: str) -> str:
    text = re.sub(r"(?i)\b0f\b", "of", text)
    text = re.sub(r"(?i)\b0n\b", "on", text)
    text = re.sub(r"(?m)(?<=[\.\!\?]\s)(the)\b", lambda m: m.group(1).capitalize(), text)
    text = re.sub(r"(?m)^(l')", "I'", text)
    # Acronyms/dotted
    def acr_repl(m):
        letters = re.findall(r"[A-Za-z]", m.group(0))
        return "".join(letters)
    text = re.sub(r"\b(?:[A-Za-z]\.\s*){2,6}[A-Za-z]?\.?", acr_repl, text)
    text = re.sub(r"(?i)\bPh\.\s*D\.'s\b", "PhDs", text)
    text = re.sub(r"(?i)\bPh\.\s*D\.\b", "PhD", text)
    return text

# ---------- Whitespace & final flatten ----------

def clean_whitespace_and_punct(text: str) -> str:
    text = re.sub(r"(?:\r?\n){3,}", "\n\n", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([.?!])([A-Z])", r"\1 \2", text)
    text = re.sub(r"(?m)[ \t]+$", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r",{3,}", ",", text)
    text = re.sub(r";{3,}", ";", text)
    text = re.sub(r":{3,}", ":", text)
    return text

def ensure_punctuation_spacing(text: str) -> str:
    text = re.sub(r"([,;:])(?=\S)", r"\1 ", text)
    text = re.sub(r"([.?!])(?=\S)", r"\1 ", text)
    # Separate jammed digit/letter boundaries
    text = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", text)
    text = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", text)
    # Collapse doubles
    text = re.sub(r" {2,}", " ", text)
    return text

def final_flatten_to_single_paragraph(text: str) -> str:
    text = text.replace("\r", "\n").replace(PAGE_BREAK, " ")
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()
