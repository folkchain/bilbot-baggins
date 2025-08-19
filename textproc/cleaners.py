# -*- coding: utf-8 -*-
import re

def detect_jammed_text(text: str) -> bool:
    """Check if text lacks proper spacing."""
    sample = text[:500] if len(text) > 500 else text
    words = sample.split()
    # If average "word" is > 15 chars, text is jammed
    if not words:
        return True
    avg_word_len = sum(len(w) for w in words) / len(words)
    return avg_word_len > 15

def aggressive_space_fix(text: str) -> str:
    """
    Aggressively add spaces to jammed text.
    This is a nuclear option when PDF extraction fails.
    """
    # First, add spaces at obvious boundaries
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # camelCase
    text = re.sub(r'([a-z])(was|is|are|were|had|has|have|been|the|and|for|with|from|that|this|but|not|can|will|would|should|could)', r'\1 \2', text)
    text = re.sub(r'(was|is|are|were|had|has|have|been|the|and|for|with|from|that|this|but|not|can|will|would|should|could)([a-z])', r'\1 \2', text)
    text = re.sub(r'([.!?,;:])([A-Za-z])', r'\1 \2', text)  # After punctuation
    text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)  # Number to letter
    text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)  # Letter to number
    
    # Add spaces before common word patterns
    common_patterns = [
        'of', 'in', 'to', 'it', 'as', 'at', 'by', 'on', 'or', 'an',
        'be', 'he', 'me', 'we', 'so', 'no', 'up', 'my', 'do', 'if',
    ]
    for pattern in common_patterns:
        # Add space before the pattern if it's stuck to a lowercase letter
        text = re.sub(f'([a-z])({pattern})([^a-z])', r'\1 \2\3', text, flags=re.IGNORECASE)
    
    # Fix specific patterns from your example
    text = re.sub(r'([a-z])(American|English|French|Spanish|Chinese)', r'\1 \2', text)
    text = re.sub(r'(American|English|French|Spanish|Chinese)([a-z])', r'\1 \2', text)
    
    return text

def fix_line_break_hyphenation(text: str) -> str:
    """Fix hyphenated words at line breaks."""
    # Remove hyphens in obvious word breaks
    text = re.sub(r'([a-z])-\n([a-z])', r'\1\2', text)
    # Also fix hyphens without newlines in common cases
    text = re.sub(r'([a-z])-(ture|tion|ment|ness|ing|ed|er|est|ly|ity|ous|ive|ful|less|able|ible)(\s|$)', r'\1\2\3', text)
    return text

def remove_page_headers(text: str) -> str:
    """Remove page headers and numbers."""
    lines = text.split('\n')
    cleaned = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip pure numbers
        if re.match(r'^\d{1,4}$', stripped):
            continue
        
        # Skip headers with page numbers like "Twelve Years Later 119"
        if re.search(r'\b(Chapter|Section|Part|Page|Years)\b.*\d{1,4}$', stripped, re.IGNORECASE):
            continue
            
        # Skip roman numerals
        if re.match(r'^[ivxlcdm]+$', stripped, re.IGNORECASE):
            continue
            
        cleaned.append(line)
    
    return '\n'.join(cleaned)

def remove_all_quotes(text: str) -> str:
    """Remove ALL types of quotes completely."""
    # List of all quote characters to remove
    quotes = [
        '"', '"', '"',  # Double quotes
        '\'', ''', ''',  # Single quotes with escaped apostrophe
        '`', '´',  # Backticks and accents  
        '„', '‟', '‚',  # Bottom quotes
        '«', '»', '‹', '›',  # Guillemets
        '〝', '〞', '＂',  # CJK quotes
        '˝', 'ˮ', '״',  # Other quotes
    ]
    
    for quote in quotes:
        text = text.replace(quote, '')
    
    # Also remove escaped quotes
    text = text.replace('\\"', '')
    text = text.replace("\\'", '')
    
    return text

def clean_special_characters(text: str) -> str:
    """Clean special characters."""
    # Remove quotes first
    text = remove_all_quotes(text)
    
    # Fix dashes
    text = text.replace('—', ', ')
    text = text.replace('–', ', ')
    
    # Remove soft hyphens
    text = text.replace('\u00AD', '')
    
    # Remove other special chars
    text = text.replace('^', '')
    text = text.replace('~', '')
    text = text.replace('|', '')
    
    return text

def remove_footnote_markers(text: str) -> str:
    """Remove footnote markers."""
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\(\d+\)', '', text)
    text = re.sub(r'([.!?,;:])\d{1,3}', r'\1', text)
    return text

def remove_references(text: str) -> str:
    """Remove URLs, emails, citations."""
    text = re.sub(r'https?://[^\s]+', '', text)
    text = re.sub(r'www\.[^\s]+', '', text)
    text = re.sub(r'\S+@\S+\.\S+', '', text)
    text = re.sub(r'\([A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s+\d{4}\)', '', text)
    return text

def join_paragraphs_smart(text: str) -> str:
    """Join lines with proper spacing."""
    # Replace page breaks with spaces
    text = text.replace('\f', ' ')
    
    # Split on double newlines (paragraphs)
    paragraphs = text.split('\n\n')
    
    result = []
    for para in paragraphs:
        if not para.strip():
            continue
        
        # Join lines within paragraph WITH SPACES
        lines = para.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        
        if cleaned_lines:
            # Make sure we join with spaces!
            joined = ' '.join(cleaned_lines)
            result.append(joined)
    
    # Join all paragraphs with spaces
    return ' '.join(result)

def fix_punctuation_spacing(text: str) -> str:
    """Fix spacing around punctuation."""
    text = re.sub(r'\s+([,.!?;:])', r'\1', text)
    text = re.sub(r'([,.!?;:])([A-Za-z])', r'\1 \2', text)
    return text

def normalize_whitespace(text: str) -> str:
    """Clean up whitespace."""
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()
    return text

def validate_and_fix_spacing(text: str, original_len: int) -> str:
    """Final validation and emergency fixes."""
    # Check if text is jammed
    if detect_jammed_text(text):
        text = aggressive_space_fix(text)
    
    # Make sure we have spaces
    if ' ' not in text[:100] and len(text) > 100:
        # Nuclear option: add space every ~7 characters at word boundaries
        text = re.sub(r'([a-z]{5,7})([a-z])', r'\1 \2', text)
    
    return text

# Compatibility stubs
def remove_all_caps_lines(text: str) -> str:
    lines = text.splitlines()
    result = []
    for line in lines:
        letters = [c for c in line if c.isalpha()]
        if letters and all(c.isupper() for c in letters):
            continue
        result.append(line)
    return '\n'.join(result)

def remove_known_header_lines(text: str) -> str:
    text = re.sub(r'(?m)^.*Years.*\d{1,4}\s*$', '', text)
    return text

def final_flatten_to_single_paragraph(text: str) -> str:
    return text

# Compatibility mappings
strip_firstline_headers = remove_page_headers
drop_footnotes_at_bottom = remove_footnote_markers
normalize_linebreak_hyphens = fix_line_break_hyphenation
strip_underscores_and_unreadables = clean_special_characters
strip_all_quotes_keep_apostrophes = remove_all_quotes
remove_unwanted = remove_references
join_wrapped_lines = join_paragraphs_smart
normalize_ellipses_to_period = lambda x: x.replace('...', '.')
tts_punctuation_shaping = fix_punctuation_spacing
clean_whitespace_and_punct = normalize_whitespace
ensure_punctuation_spacing = fix_punctuation_spacing