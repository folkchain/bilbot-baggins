import streamlit as st
import io
import os
import re
import tempfile
import asyncio
from typing import List

import edge_tts
import pdfplumber
from pypdf import PdfReader

def read_text_file(file_bytes):
    """Read text from uploaded file"""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1", errors="ignore")

def read_pdf_file(file_bytes):
    """Extract text from PDF file"""
    text_parts = []
    
    # Try pdfplumber first
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

def clean_text(text):
    """Comprehensive text cleanup for better TTS output"""
    
    # 1) NORMALIZE LINE ENDINGS
    text = text.replace("\r", "\n")
    
    # 2) HYPHEN/DASH CLEANUP (all types with spaces)
    # Remove soft hyphens with any amount of space
    text = re.sub(r"\u00AD\s*", "", text)
    text = re.sub(r"\u00AD", "", text)
    
    # Remove regular hyphens with spaces WITHIN words
    text = re.sub(r"(\b[A-Za-z]+)-\s+([A-Za-z]+\b)", r"\1\2", text)
    
    # Remove en-dash with spaces within words
    text = re.sub(r"(\b[A-Za-z]+)–\s*([A-Za-z]+\b)", r"\1\2", text)
    
    # Remove em-dash with spaces within words  
    text = re.sub(r"(\b[A-Za-z]+)—\s*([A-Za-z]+\b)", r"\1\2", text)
    
    # Remove minus sign with spaces within words
    text = re.sub(r"(\b[A-Za-z]+)\u2212\s*([A-Za-z]+\b)", r"\1\2", text)
    
    # Handle double hyphens with spaces (like intel-- lectual)
    text = re.sub(r"(\b[A-Za-z]+)--\s*([A-Za-z]+\b)", r"\1\2", text)
    
    # Remove any dash at end of line if next line starts with lowercase
    text = re.sub(r"([A-Za-z])[\-–—\u2212]\s*\n\s*(?=[a-z])", r"\1", text)
    
    # Specific pattern: word+hyphen+space+word should join
    text = re.sub(r"\b([A-Za-z]+)[\-–—\u2212]\s+([A-Za-z]+)\b", r"\1\2", text)
    
    # 3) JOIN WRAPPED LINES (conservative)
    # Only join if line doesn't end with sentence punctuation
    text = re.sub(r"([a-z,;])\s*\n(?=[a-z])", r"\1 ", text)
    
    # 4) WHITESPACE CLEANUP (safe)
    # Trim trailing whitespace
    text = re.sub(r"(?m)[ \t]+$", "", text)
    # Collapse 3+ spaces to 1
    text = re.sub(r"[ \t]{3,}", " ", text)
    # Collapse 4+ blank lines to 2
    text = re.sub(r"(?:\n){4,}", "\n\n", text)
    
    # Basic punctuation spacing
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([.?!])([A-Z])", r"\1 \2", text)
    
    # 5) MINIMAL CLEANUP (very conservative)
    # Only collapse really excessive punctuation
    text = re.sub(r"\.{4,}", "...", text)
    text = re.sub(r",{3,}", ",", text)
    text = re.sub(r";{3,}", ";", text)
    text = re.sub(r":{3,}", ":", text)
    
    # Join single spaced letters (clear OCR error)
    text = re.sub(r"\b([A-Za-z])\s([A-Za-z])\s([A-Za-z])\s([A-Za-z])\s([A-Za-z])\b", r"\1\2\3\4\5", text)
    text = re.sub(r"\b([A-Za-z])\s([A-Za-z])\s([A-Za-z])\s([A-Za-z])\b", r"\1\2\3\4", text)
    text = re.sub(r"\b([A-Za-z])\s([A-Za-z])\s([A-Za-z])\b", r"\1\2\3", text)
    
    # 6) REMOVE PROBLEMATIC CHARACTERS
    # Remove characters that cause TTS issues or are formatting artifacts
    text = re.sub(r"[~*{}<>^\[\]@•=_/\\|£]", "", text)
    text = re.sub(r"!", "", text)  # Remove exclamation marks if they're causing issues
    text = re.sub(r"- -", "-", text)
    
    # Final space cleanup
    text = re.sub(r"  +", " ", text)
    
    return text.strip()

def split_into_chunks(text, max_length=2000):
    """Split text into chunks suitable for TTS"""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 2 <= max_length:
            current_chunk = (current_chunk + "\n\n" + paragraph).strip() if current_chunk else paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = paragraph
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

@st.cache_data
def get_available_voices():
    """Get list of US English Male Neural voices only"""
    try:
        voices = asyncio.run(edge_tts.list_voices())
        # Filter for US English Male Neural voices only
        us_male_voices = [
            v for v in voices 
            if (v.get("Locale", "").startswith("en-US") and 
                "Neural" in v.get("ShortName", "") and
                v.get("Gender", "").lower() == "male")
        ]
        return sorted(us_male_voices, key=lambda x: x.get("ShortName", ""))
    except Exception as e:
        st.error(f"Error getting voices: {e}")
        return []

async def generate_speech(text, voice, rate, pitch, output_file):
    """Generate speech from text"""
    communicate = edge_tts.Communicate(
        text=text, 
        voice=voice, 
        rate=f"{rate:+d}%", 
        pitch=f"{pitch:+d}Hz"
    )
    await communicate.save(output_file)

def combine_audio_files(file_list):
    """Combine multiple MP3 files into one using simple concatenation"""
    combined_data = b""
    
    for file_path in file_list:
        with open(file_path, 'rb') as f:
            mp3_data = f.read()
            combined_data += mp3_data
    
    return combined_data

# Streamlit UI
st.set_page_config(
    page_title="Text to Audiobook Converter", 
    page_icon="🎧", 
    layout="centered"
)

st.title("🎧 Text to Audiobook Converter")
st.write("Convert your text files or PDFs into MP3 audiobooks using US English male AI voices!")

# File upload
uploaded_file = st.file_uploader(
    "Upload a text file or PDF", 
    type=["txt", "pdf"],
    help="Choose a .txt file or searchable PDF to convert to audio"
)

# Voice selection
voices = get_available_voices()
if not voices:
    st.error("Could not load voice list. Please refresh the page.")
    st.stop()

voice_options = [v.get("ShortName") for v in voices]

# Show some info about available voices
st.write(f"**Available voices:** {len(voice_options)} US English Male Neural voices")

selected_voice = st.selectbox(
    "Choose a male voice", 
    voice_options,
    index=0 if not voice_options else (
        voice_options.index("en-US-AndrewNeural") if "en-US-AndrewNeural" in voice_options else 0
    )
)

# Voice settings
col1, col2 = st.columns(2)
with col1:
    speech_rate = st.slider("Speech Rate", -50, 50, 0, help="Negative = slower, Positive = faster")
with col2:
    speech_pitch = st.slider("Pitch", -20, 20, 0, help="Negative = lower, Positive = higher")

# Text cleaning option
clean_whitespace = st.checkbox("Clean up text formatting", value=True)

# Generate button
if st.button("🎵 Generate Audiobook", type="primary"):
    if not uploaded_file:
        st.error("Please upload a file first!")
        st.stop()
    
    # Read file content
    with st.spinner("Reading file..."):
        file_content = uploaded_file.read()
        filename = uploaded_file.name
        
        if filename.lower().endswith(".txt"):
            text_content = read_text_file(file_content)
        else:
            text_content = read_pdf_file(file_content)
    
    if not text_content.strip():
        st.error("No text found in the file. For PDFs, make sure it contains selectable text, not just images.")
        st.stop()
    
    # Clean text if requested
    if clean_whitespace:
        text_content = clean_text(text_content)
    
    # Split into chunks
    text_chunks = split_into_chunks(text_content)
    
    st.success(f"Found {len(text_content):,} characters in {len(text_chunks)} chunks")
    
    # Generate audio for each chunk
    temp_files = []
    temp_dir = tempfile.mkdtemp()
    
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, chunk in enumerate(text_chunks):
            status_text.text(f"Generating audio for chunk {i+1} of {len(text_chunks)}...")
            
            temp_file = os.path.join(temp_dir, f"chunk_{i:03d}.mp3")
            asyncio.run(generate_speech(chunk, selected_voice, speech_rate, speech_pitch, temp_file))
            temp_files.append(temp_file)
            
            progress_bar.progress((i + 1) / len(text_chunks))
        
        # Combine all audio files
        status_text.text("Combining audio files...")
        final_audio = combine_audio_files(temp_files)
        
        # Prepare download
        base_filename = os.path.splitext(filename)[0]
        download_filename = f"{base_filename}_audiobook_{selected_voice}.mp3"
        
        st.success("✅ Audiobook generated successfully!")
        st.download_button(
            label="📥 Download MP3 Audiobook",
            data=final_audio,
            file_name=download_filename,
            mime="audio/mpeg"
        )
        
    except Exception as e:
        st.error(f"Error generating audiobook: {e}")
    
    finally:
        # Clean up temp files
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass
        try:
            os.rmdir(temp_dir)
        except:
            pass

st.markdown("---")
st.markdown("**Tips:**")
st.markdown("• For best results, use clean, well-formatted text")
st.markdown("• Large files may take several minutes to process")
st.markdown("• The app will automatically split long texts into manageable chunks")
st.markdown("• Only US English male voices are available")
