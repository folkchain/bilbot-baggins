import re
import io
import pdfplumber
from pypdf import PdfReader
from typing import List


class TextProcessor:
    """Handles all text extraction, cleaning, and chunking operations"""
    
    @staticmethod
    def read_text_file(file_bytes: bytes) -> str:
        """Read text from uploaded file"""
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="ignore")

    @staticmethod
    def read_pdf_file(file_bytes: bytes) -> str:
        """Extract text from PDF file using multiple methods"""
        text_parts = []
        
        # Try pdfplumber first (better for complex layouts)
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    text_parts.append(text)
            result = "\n".join(text_parts).strip()
            if result:
                return result
        except Exception:
            pass
        
        # Fallback to pypdf
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                text = page.extract_text() or ""
                text_parts.append(text)
            return "\n".join(text_parts).strip()
        except Exception:
            return ""

    @staticmethod
    def clean_text(text: str) -> str:
        """Comprehensive text cleanup for better TTS output"""
        
        # 1) NORMALIZE LINE ENDINGS
        text = text.replace("\r", "\n")
        
        # 2) LIGATURE FIXES
        ligature_map = {
            "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"
        }
        for ligature, replacement in ligature_map.items():
            text = text.replace(ligature, replacement)
        
        # 3) QUOTE & APOSTROPHE NORMALIZATION
        quote_map = {
            """: '"', """: '"', "'": "'", "'": "'"
        }
        for curly, straight in quote_map.items():
            text = text.replace(curly, straight)
        
        # 4) REMOVE UNWANTED CONTENT
        # Remove standalone page numbers (1-4 digits only)
        text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", text)
        
        # Remove common header/footer patterns
        text = re.sub(r"(?m)^(Chapter|CHAPTER)\s+\d+.*$", "", text)
        text = re.sub(r"(?m)^\s*Page\s+\d+.*$", "", text)
        
        # Remove URLs and emails
        text = re.sub(r"https?://[^\s]+", "", text)
        text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "", text)
        
        # Remove TOC lines with dots and page numbers
        text = re.sub(r"(?m)^.*\.{3,}.*\d+\s*$", "", text)
        
        # Remove parenthetical citations
        text = re.sub(r"\([A-Z][a-z]+,?\s+\d{4}\)", "", text)  # (Smith, 2019)
        text = re.sub(r"\[[0-9,\s-]+\]", "", text)  # [1,2,3] or [1-5]
        
        # Remove footnote markers (be conservative)
        text = re.sub(r"(?<=\w)\d+(?=\s|$|[,.!?])", "", text)
        
        # 5) HYPHEN/DASH CLEANUP
        text = TextProcessor._clean_hyphens_and_dashes(text)
        
        # 6) JOIN WRAPPED LINES (conservative)
        text = re.sub(r"([a-z,;])\s*\n(?=[a-z])", r"\1 ", text)
        text = re.sub(r"(?m)^(\w+)\s*\n(?=\w)", r"\1 ", text)
        
        # 7) WHITESPACE CLEANUP
        text = TextProcessor._clean_whitespace(text)
        
        # 8) QUOTE SPACING FIXES
        text = TextProcessor._fix_quote_spacing(text)
        
        # 9) PUNCTUATION CLEANUP
        text = re.sub(r",{3,}", ",", text)
        text = re.sub(r";{3,}", ";", text)
        text = re.sub(r":{3,}", ":", text)
        text = re.sub(r"\.{4,}", "...", text)
        
        # 10) OCR ERROR FIXES
        text = TextProcessor._fix_ocr_errors(text)
        
        # 11) REMOVE PROBLEMATIC CHARACTERS
        text = re.sub(r"[~*{}<>^\[\]@•=_/\\|£]", "", text)
        text = re.sub(r"- -", "-", text)
        
        # Final cleanup
        text = re.sub(r"  +", " ", text)
        
        return text.strip()

    @staticmethod
    def _clean_hyphens_and_dashes(text: str) -> str:
        """Clean up various hyphen and dash issues"""
        # Remove soft hyphens
        text = re.sub(r"\u00AD\s*", "", text)
        
        # Convert Hangul Choseong Kiyeok to regular hyphen
        text = re.sub(r"\u1100", "-", text)
        
        # Remove hyphens with spaces within words
        text = re.sub(r"(\b[A-Za-z]+)-\s+([A-Za-z]+\b)", r"\1\2", text)
        text = re.sub(r"(\b[A-Za-z]+)\u1100\s+([A-Za-z]+\b)", r"\1\2", text)
        text = re.sub(r"(\b[A-Za-z]+)–\s*([A-Za-z]+\b)", r"\1\2", text)
        text = re.sub(r"(\b[A-Za-z]+)—\s*([A-Za-z]+\b)", r"\1\2", text)
        text = re.sub(r"(\b[A-Za-z]+)\u2212\s*([A-Za-z]+\b)", r"\1\2", text)
        text = re.sub(r"(\b[A-Za-z]+)--\s*([A-Za-z]+\b)", r"\1\2", text)
        
        # Remove dash at end of line if next line starts with lowercase
        text = re.sub(r"([A-Za-z])[\-–—\u2212\u1100]\s*\n\s*(?=[a-z])", r"\1", text)
        
        return text

    @staticmethod
    def _clean_whitespace(text: str) -> str:
        """Clean up whitespace issues"""
        # Trim trailing whitespace
        text = re.sub(r"(?m)[ \t]+$", "", text)
        
        # Collapse multiple spaces
        text = re.sub(r"[ \t]{3,}", " ", text)
        
        # Collapse multiple blank lines
        text = re.sub(r"(?:\r?\n){4,}", "\n\n", text)
        
        # Remove space before punctuation
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        
        # Add space after sentence punctuation before capital letters
        text = re.sub(r"([.?!])([A-Z])", r"\1 \2", text)
        
        return text

    @staticmethod
    def _fix_quote_spacing(text: str) -> str:
        """Fix spacing around quotes"""
        # Fix escaped quotes with spaces
        text = re.sub(r'\\\s*"\s*([^"]*?)\s*"\s*', r' "\1" ', text)
        
        # Normalize spacing around quotes
        text = re.sub(r"\s+([\"'])([^\"']*?)([\"'])\s+", r' \1\2\3 ', text)
        text = re.sub(r"([\"'])\s+([^\s])", r"\1\2", text)
        text = re.sub(r"([^\s])\s+([\"'])", r"\1\2", text)
        
        return text

    @staticmethod
    def _fix_ocr_errors(text: str) -> str:
        """Fix common OCR errors like spaced letters"""
        # Join single spaced letters (clear OCR error)
        text = re.sub(r"\b([A-Za-z])\s([A-Za-z])\s([A-Za-z])\s([A-Za-z])\s([A-Za-z])\b", r"\1\2\3\4\5", text)
        text = re.sub(r"\b([A-Za-z])\s([A-Za-z])\s([A-Za-z])\s([A-Za-z])\b", r"\1\2\3\4", text)
        text = re.sub(r"\b([A-Za-z])\s([A-Za-z])\s([A-Za-z])\b", r"\1\2\3", text)
        
        return text

    @staticmethod
    def smart_split_into_chunks(text: str, max_length: int = 2000) -> List[str]:
        """Split text at sentence boundaries when possible"""
        # Split into sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk = (current_chunk + " " + sentence).strip() if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If single sentence is too long, split it by words
                if len(sentence) > max_length:
                    word_chunks = TextProcessor._split_long_sentence(sentence, max_length)
                    chunks.extend(word_chunks[:-1])
                    current_chunk = word_chunks[-1] if word_chunks else ""
                else:
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return [chunk for chunk in chunks if chunk.strip()]

    @staticmethod
    def _split_long_sentence(sentence: str, max_length: int) -> List[str]:
        """Split a long sentence into chunks by words"""
        words = sentence.split()
        chunks = []
        current_chunk = ""
        
        for word in words:
            if len(current_chunk) + len(word) + 1 <= max_length:
                current_chunk = (current_chunk + " " + word).strip() if current_chunk else word
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = word
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    @staticmethod
    def get_text_stats(text: str) -> dict:
        """Get statistics about the text"""
        words = len(text.split())
        characters = len(text)
        paragraphs = len([p for p in text.split('\n\n') if p.strip()])
        
        # Estimate reading time (average 200 words per minute)
        reading_time_minutes = words / 200
        
        # Estimate audio length (average 150 words per minute for TTS)
        audio_time_minutes = words / 150
        
        return {
            'characters': characters,
            'words': words,
            'paragraphs': paragraphs,
            'reading_time_minutes': reading_time_minutes,
            'estimated_audio_minutes': audio_time_minutes
        }
