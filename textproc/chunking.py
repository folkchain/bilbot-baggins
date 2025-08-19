# -*- coding: utf-8 -*-
import re
from typing import List

# Placeholder used to protect periods inside abbreviations during splitting
_ABBR_DOT = "§DOT§"

# Common English abbreviations that shouldn’t trigger sentence splits
_ABBR_LIST = [
    # honorifics / titles
    "Mr", "Mrs", "Ms", "Dr", "Prof", "Sr", "Jr", "St",
    # common short forms
    "vs", "etc", "Fig", "No", "Vol", "pp", "p", "Ch", "Mt",
    # months
    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    # degrees & acronyms that often appear with dots
    "B", "M", "Ph", "Ed",  # so "Ph.D." becomes protected per pattern below
]

# Build regexes to protect & restore periods in abbreviations
# 1) Simple tokens like "Dr."  -> replace the dot
_ABBR_SIMPLE_RE = re.compile(r"\b(" + "|".join(map(re.escape, _ABBR_LIST)) + r")\.", flags=re.IGNORECASE)

# 2) Dotted degree patterns like "Ph. D." / "B. A." / "M. A." / "Ed. D."
#    We replace their dots so splitting won't happen in the middle.
_DEGREE_DOTTED_RE = re.compile(
    r"\b([B|M|Ph|Ed])\.\s*([A|D])\.",  # captures "Ph. D.", "B. A.", etc.
    flags=re.IGNORECASE
)

# Splitting rule: after a sentence ender and before a likely sentence start
_SENT_SPLIT_RE = re.compile(
    r"(?<=[.?!])\s+(?=[A-Z\"'(\[])"
)

def _protect_abbreviations(text: str) -> str:
    # Protect simple "Abbr." -> "Abbr§DOT§"
    text = _ABBR_SIMPLE_RE.sub(lambda m: f"{m.group(1)}{_ABBR_DOT}", text)
    # Protect dotted degree patterns "Ph. D." -> "Ph§DOT§ D§DOT§"
    text = _DEGREE_DOTTED_RE.sub(lambda m: f"{m.group(1)}{_ABBR_DOT} {m.group(2)}{_ABBR_DOT}", text)
    # Protect sequences like "U. S. A." generically -> "U§DOT§ S§DOT§ A§DOT§"
    text = re.sub(r"\b([A-Za-z])\.\s+(?=[A-Za-z]\.)", r"\1" + _ABBR_DOT + " ", text)
    text = re.sub(r"\b([A-Za-z])\.(?=\s*[A-Za-z]\b)", r"\1" + _ABBR_DOT, text)
    return text

def _restore_abbreviations(text: str) -> str:
    return text.replace(_ABBR_DOT, ".")

def split_into_sentences(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []

    # Protect abbreviations so sentence split doesn’t fire inside them
    protected = _protect_abbreviations(text)

    # Split on sentence boundaries
    parts = _SENT_SPLIT_RE.split(protected)

    # Restore abbreviations
    sentences = [_restore_abbreviations(p).strip() for p in parts if p and p.strip()]
    return sentences

def smart_split_into_chunks(text: str, max_length: int = 2200) -> List[str]:
    """
    Build chunks from full sentences only (no mid-sentence splits).
    max_length is character-based for Edge TTS comfort.
    """
    sents = split_into_sentences(text)
    chunks: List[str] = []
    cur = ""
    for s in sents:
        if not s:
            continue
        if len(cur) + len(s) + (1 if cur else 0) <= max_length:
            cur = (cur + " " + s) if cur else s
        else:
            if cur:
                chunks.append(cur)
            if len(s) > max_length:
                # Very long sentence; soft-wrap on spaces
                words = s.split()
                cur2 = ""
                for w in words:
                    if len(cur2) + len(w) + (1 if cur2 else 0) <= max_length:
                        cur2 = (cur2 + " " + w) if cur2 else w
                    else:
                        chunks.append(cur2)
                        cur2 = w
                cur = cur2
            else:
                cur = s
    if cur:
        chunks.append(cur)
    return chunks

def get_text_stats(text: str) -> dict:
    words = len(text.split())
    characters = len(text)
    paragraphs = 1  # flattened
    reading_time_minutes = words / 200.0
    audio_time_minutes = words / 150.0
    return {
        "characters": characters,
        "words": words,
        "paragraphs": paragraphs,
        "reading_time_minutes": reading_time_minutes,
        "estimated_audio_minutes": audio_time_minutes,
    }
