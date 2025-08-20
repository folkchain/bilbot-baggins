# -*- coding: utf-8 -*-
import re
# Normalize/handle these as hyphen-like
_HYPHEN_CLASS = r"[-\u00AD\u2010-\u2015\u2212\u2043\u058A\u05BE\u1400\u1806\u2E3A\u2E3B\uFE63\uFF0D\u30A0\u1100]"


def strip_firstline_headers(text: str) -> str:
    """
    A safer header removal function that ONLY removes the first non-blank line
    of each page if it looks like a header (e.g., page number, short title).
    This prevents accidental deletion of body text.
    """
    PAGE_BREAK = "\f"
    pages = text.split(PAGE_BREAK) if PAGE_BREAK in text else [text]

    cleaned_pages = []
    for page in pages:
        lines = page.strip().split('\n')
        if not lines:
            continue

        first_line_index = next((i for i, line in enumerate(lines) if line.strip()), -1)
        
        if first_line_index != -1:
            first_line = lines[first_line_index].strip()
            
            # Heuristics to identify a header:
            is_page_number = re.fullmatch(r'[\divxlcdm]+', first_line, re.IGNORECASE)
            is_known_header = re.search(r'\b(Chapter|Page|Years)\b', first_line, re.IGNORECASE) and re.search(r'\d', first_line)
            is_short_and_no_punct = len(first_line.split()) < 10 and not re.search(r'[.!?]$', first_line)

            if is_page_number or is_known_header or is_short_and_no_punct:
                lines.pop(first_line_index)
        
        cleaned_pages.append('\n'.join(lines))

    return PAGE_BREAK.join(cleaned_pages)

def fix_line_break_hyphenation(text: str) -> str:
    """
    1) Join words split by a hyphen-like char at line break: 'rea-\nding' -> 'reading'
    2) Join tokens split like 'kin- folk' -> 'kinfolk'
    3) Keep your suffix glue behavior (ture/tion/etc.)
    """
    # 1) across line breaks
    text = re.sub(fr"([A-Za-z]){_HYPHEN_CLASS}\n([A-Za-z])", r"\1\2", text)

    # 2) hyphen-like + space in the middle of a line -> join to a single word
    text = re.sub(fr"(\b\w+){_HYPHEN_CLASS}\s+(\w+\b)", r"\1\2", text)

    # 3) your original suffix glue idea (expanded to any hyphen-like)
    text = re.sub(fr"([a-z]){_HYPHEN_CLASS}(ture|tion|ment|ness|ing|ed|er|est|ly|ity|ous|ive|ful|less|able|ible)(\s|$)", r"\1\2\3", text, flags=re.IGNORECASE)

    return text

def join_paragraphs_smart(text: str) -> str:
    """Joins lines into paragraphs with proper spacing, handling page breaks."""
    text = text.replace('\f', '\n\n') # Treat page breaks as paragraph breaks
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    cleaned_paragraphs = [' '.join(line.strip() for line in p.split('\n')) for p in paragraphs]
    return '\n\n'.join(cleaned_paragraphs) # Re-join with double newlines for now

def final_flatten(text: str) -> str:
    """Flattens the entire text into a single, space-separated paragraph."""
    return re.sub(r'\s+', ' ', text).strip()

def remove_footnote_markers(text: str) -> str:
    """Removes footnote markers like [1] or (2)."""
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\(\d+\)', '', text)
    text = re.sub(r'([.!?,;:])\d{1,3}', r'\1', text)
    return text

def remove_references(text: str) -> str:
    """Removes URLs, emails, and common citation formats."""
    text = re.sub(r'https?://[^\s]+', '', text)
    text = re.sub(r'www\.[^\s]+', '', text)
    text = re.sub(r'\S+@\S+\.\S+', '', text)
    text = re.sub(r'\([A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s+\d{4}\)', '', text)
    return text

def remove_all_quotes(text: str) -> str:
    """
    Remove all quote/prime-like characters (straight + curly + assorted Unicode).
    """
    quotes_regex = (
        r"["
        r"\"'"                # straight double/single
        r"\u2018\u2019"       # ‘ ’
        r"\u201A\u201B"       # ‚ ‛
        r"\u201C\u201D"       # “ ”
        r"\u201E\u201F"       # „ ‟
        r"\u00AB\u00BB"       # « »
        r"\u2039\u203A"       # ‹ ›
        r"\u301D\u301E"       # 〝 〞
        r"\uFF02"             # ＂
        r"\u02DD"             # ˝
        r"\u2032\u2035"       # ′ ‵ (primes sometimes used as quotes)
        r"\u00B4\u02B9"       # ´ ʹ
        r"\u05F4"             # ״
        r"`´"                 # backtick + acute
        r"]"
    )
    return re.sub(quotes_regex, "", text)

def clean_special_characters(text: str) -> str:
    """
    Normalize symbols without ever introducing commas, and remove noisy marks.
    - Do NOT add commas for dashes.
    - Normalize all hyphen-like to '-' for predictability.
    - Remove '+', '*', ellipsis, and runs of '.'.
    - Enforce: normal hyphenated words become spaced words ('self-hosted' -> 'self hosted').
    - Re-join 'word- word' to 'wordword' as a safety net.
    """
    # Normalize a wide set of hyphen-like characters to a simple hyphen
    text = re.sub(_HYPHEN_CLASS, "-", text)

    # Remove explicit soft hyphen just in case
    text = text.replace("\u00AD", "")

    # Remove plus and asterisk
    text = re.sub(r"[+*]+", "", text)

    # Remove ellipsis and runs of dots
    text = text.replace("…", "")
    text = re.sub(r"\.{2,}", "", text)

    # Safety: join 'word- space word' -> 'wordword' (if anything remained)
    text = re.sub(r"(\b\w+)-\s+(\w+\b)", r"\1\2", text)

    # Normal hyphenated words become spaced words: 'self-hosted' -> 'self hosted'
    text = re.sub(r"(?<=\w)-(?=\w)", " ", text)

    # Remove a few other specials (kept from your original)
    text = re.sub(r"[~|^]", "", text)

    return text

def fix_punctuation_spacing(text: str) -> str:
    """
    Fix spaces around punctuation and collapse adjacent punctuation sequences.
    """
    # Trim spaces before punctuation
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)

    # Ensure 1 space after punctuation when followed by an alnum
    text = re.sub(r"([,.!?;:])([A-Za-z0-9])", r"\1 \2", text)

    # Collapse sequences of mixed/repeated punctuation to the first one
    text = re.sub(r"([,.!?;:])[,.!?;:]+", r"\1", text)

    return text

def normalize_whitespace(text: str) -> str:
    """Cleans up and normalizes all whitespace."""
    return re.sub(r'\s+', ' ', text).strip()

def validate_and_fix_spacing(text: str) -> str:
    """Final validation for 'jammed' text and applies an aggressive fix if needed."""
    sample = text[:500]
    words = sample.split()
    if not words: return text
    
    avg_word_len = sum(len(w) for w in words) / len(words)
    if avg_word_len > 15:
        # Aggressively add spaces at obvious boundaries
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = re.sub(r'([.!?,;:])([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
    return text