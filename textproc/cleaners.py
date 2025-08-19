# -*- coding: utf-8 -*-
import re

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
    """Fixes hyphenated words at line breaks."""
    text = re.sub(r'([a-z])-\n([a-z])', r'\1\2', text)
    text = re.sub(r'([a-z])-(ture|tion|ment|ness|ing|ed|er|est|ly|ity|ous|ive|ful|less|able|ible)(\s|$)', r'\1\2\3', text)
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
    """Removes all types of quote characters."""
    # This extensive list covers various Unicode quotes
    quotes_regex = r'["\'`´„‟‚«»‹›〝〞＂˝ˮ״]'
    return re.sub(quotes_regex, '', text)

def clean_special_characters(text: str) -> str:
    """Normalizes dashes and removes a few other special characters."""
    text = re.sub(r'[—–]', ', ', text)  # Em and En dashes to comma
    text = text.replace('\u00AD', '')      # Soft hyphen
    return re.sub(r'[~|^]', '', text)

def fix_punctuation_spacing(text: str) -> str:
    """Ensures correct spacing around punctuation."""
    text = re.sub(r'\s+([,.!?;:])', r'\1', text)
    text = re.sub(r'([,.!?;:])(?=[a-zA-Z0-9])', r'\1 ', text)
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