# -*- coding: utf-8 -*-
import re
from typing import List

def smart_split_into_chunks(text: str, max_length: int = 2000) -> List[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks: List[str] = []
    cur = ""
    for sent in sentences:
        if len(cur) + len(sent) + 1 <= max_length:
            cur = (cur + " " + sent).strip() if cur else sent
        else:
            if cur:
                chunks.append(cur)
            if len(sent) > max_length:
                chunks.extend(_split_long_sentence(sent, max_length)[:-1])
                cur = _split_long_sentence(sent, max_length)[-1]
            else:
                cur = sent
    if cur:
        chunks.append(cur)
    return [c for c in chunks if c.strip()]

def _split_long_sentence(sentence: str, max_length: int) -> List[str]:
    words = sentence.split()
    chunks: List[str] = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_length:
            cur = (cur + " " + w).strip() if cur else w
        else:
            if cur:
                chunks.append(cur)
            cur = w
    if cur:
        chunks.append(cur)
    return chunks

def get_text_stats(text: str) -> dict:
    words = len(text.split())
    characters = len(text)
    paragraphs = len([p for p in text.split("\n\n") if p.strip()])
    reading_time_minutes = words / 200.0
    audio_time_minutes = words / 150.0
    return {
        "characters": characters,
        "words": words,
        "paragraphs": paragraphs,
        "reading_time_minutes": reading_time_minutes,
        "estimated_audio_minutes": audio_time_minutes,
    }
