# -*- coding: utf-8 -*-
import os
import asyncio
import tempfile
from pathlib import Path

import streamlit as st
from PIL import Image
import base64

import edge_tts
from edge_tts import VoicesManager

from text_processor import TextProcessor
from textproc.chunking import split_into_sentences
from textproc import cleaners as C

# --- App identity & theme -----------------------------------------------------
APP_NAME = "BilBot Baggins"
LOGO_PATH = Path("assets/bilbot-baggins-logo.png")

_logo_img = Image.open(LOGO_PATH)
st.set_page_config(
    page_title=f"{APP_NAME} - Audiobook",
    page_icon=_logo_img,
    layout="centered",
)

def _inject_css():
    with open(LOGO_PATH, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    css = f"""
    <style>
      .stApp {{
        background: linear-gradient(180deg, #F4EEDA 0%, #EFE7CC 100%);
        color: #2E2A22;
      }}
      .bilbot-hero {{
        display:flex; align-items:center; gap:16px; margin: 4px 0 12px 0;
        padding: 12px 16px; border-radius: 16px;
        background: #EFE7CC; border: 2px solid #D7CCAA;
        box-shadow: 0 4px 14px rgba(60, 55, 45, 0.08);
      }}
      .bilbot-hero img {{
        width: 72px; height: 72px; border-radius: 16px; border: 2px solid #3A2F21;
      }}
      .bilbot-title {{
        font-family: Georgia, 'Times New Roman', serif;
        font-weight: 700; font-size: 28px; line-height: 1.1; margin: 0;
        color: #2E2A22;
      }}
      .bilbot-sub {{
        margin: 2px 0 0 0; color: #4A7C59; font-size: 14px;
      }}
      section[data-testid="stSidebar"] > div {{ background: #EFE7CC; }}
      .stButton>button, .stDownloadButton>button {{
        border-radius: 12px; padding: 10px 16px; border: 2px solid #3A2F21;
        background:#4A7C59; color:#F4EEDA; font-weight:600;
      }}
      .stButton>button:hover, .stDownloadButton>button:hover {{ filter: brightness(1.05); }}
      .stSelectbox div[data-baseweb="select"] > div {{
        border-radius: 12px; border: 2px solid #3A2F21;
      }}
      pre, code, .stText {{ color: #2E2A22; }}
    </style>
    <div class="bilbot-hero">
      <img src="data:image/png;base64,{b64}" alt="BilBot Baggins logo"/>
      <div>
        <h1 class="bilbot-title">BilBot Baggins</h1>
        <div class="bilbot-sub">Convert TXT and PDF into MP3 audiobooks with AI voices.</div>
      </div>
    </div>
    """
    st.markdown(css, unsafe_allow_html=True)

_inject_css()

# --- Voices: English Neural only ---------------------------------------------
DEFAULT_VOICE = "en-US-AndrewNeural"
VOICES_FALLBACK = [
    DEFAULT_VOICE,
    "en-US-JennyNeural",
    "en-US-GuyNeural",
    "en-US-AriaNeural",
    "en-GB-LibbyNeural",
    "en-GB-RyanNeural",
]

@st.cache_resource(show_spinner=False)
def load_english_neural_voices():
    try:
        voices_mgr = asyncio.run(VoicesManager.create())
        en_voices = voices_mgr.find(Language="en")
        names = sorted({v["ShortName"] for v in en_voices if "Neural" in v["ShortName"]})
        if DEFAULT_VOICE in names:
            names.remove(DEFAULT_VOICE)
            names.insert(0, DEFAULT_VOICE)
        return names or VOICES_FALLBACK
    except Exception:
        return VOICES_FALLBACK

VOICES = load_english_neural_voices()

# --- Helpers -----------------------------------------------------------------
def signed(val: int) -> str:
    return f"+{val}" if val >= 0 else str(val)

def pick_chunk_size(text: str) -> int:
    """
    Auto-tune chunk length for smoother TTS. Returns value in [1500, 2800].
    """
    try:
        sents = split_into_sentences(text)
        if not sents:
            return 2200
        avg = sum(len(s) for s in sents) / max(1, len(sents))
        longest = max(len(s) for s in sents)
        size = 2200
        if longest > 2400:
            size = 1800
        elif avg > 300:
            size = 2000
        elif avg < 120:
            size = 2600
        return max(1500, min(size, 2800))
    except Exception:
        return 2200

async def synthesize_best_quality_mp3_async(text: str, voice: str, out_path: str, rate_pct: int, pitch_hz: int, volume_pct: int):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=f"{signed(rate_pct)}%",
        pitch=f"{signed(pitch_hz)}Hz",
        volume=f"{signed(volume_pct)}%",
    )
    await communicate.save(out_path)

def synthesize_best_quality_mp3(text: str, voice: str, out_path: str, rate_pct: int, pitch_hz: int, volume_pct: int):
    asyncio.run(synthesize_best_quality_mp3_async(text, voice, out_path, rate_pct, pitch_hz, volume_pct))

def check_text_quality(text: str) -> dict:
    """Check if text has spacing issues."""
    sample = text[:1000] if len(text) > 1000 else text
    words = sample.split()
    avg_word_len = len(sample.replace(" ", "")) / max(1, len(words))
    
    return {
        "words_in_sample": len(words),
        "avg_word_length": avg_word_len,
        "has_spacing_issues": avg_word_len > 15,
        "sample": sample[:200]
    }

# --- UI ----------------------------------------------------------------------
uploaded = st.file_uploader("Upload a PDF or TXT", type=["pdf", "txt"], key="upload")

default_idx = VOICES.index(DEFAULT_VOICE) if DEFAULT_VOICE in VOICES else 0
voice = st.selectbox("Voice", VOICES, index=default_idx, key="voice")

# Keep user controls for Rate and Pitch
rate_pct = st.slider("Rate (% change)", min_value=-50, max_value=50, value=0, step=5, key="rate")
pitch_hz = st.slider("Pitch (Hz change)", min_value=-300, max_value=300, value=0, step=10, key="pitch")
volume_pct = 0  # fixed for now

# Cleanup options
with st.expander("⚙️ Text Cleaning Options"):
    remove_headers = st.checkbox("Remove running headers/page numbers", value=True, key="rm_hdr")
    remove_footnotes = st.checkbox("Remove footnote markers", value=True, key="rm_foot")
    debug_mode = st.checkbox("🔍 Show debug info", value=False, key="debug")

if uploaded:
    data = uploaded.read()
    ext = Path(uploaded.name).suffix.lower()

    with st.spinner("Extracting text..."):
        if ext == ".pdf":
            raw_text = TextProcessor.read_pdf_file(data)
        else:
            raw_text = TextProcessor.read_text_file(data)

    # Show extraction quality
    if debug_mode:
        st.info(f"📄 Extracted {len(raw_text):,} characters from {uploaded.name}")
        with st.expander("View raw extracted text (first 1000 chars)"):
            st.text(raw_text[:1000])

    with st.spinner("Cleaning text for TTS..."):
        t = TextProcessor.clean_text(
            raw_text,
            remove_running_headers=remove_headers,
            remove_bottom_footnotes=remove_footnotes,
        )

    # Check text quality
    quality = check_text_quality(t)
    
    if quality["has_spacing_issues"]:
        st.warning("⚠️ Text may have spacing issues detected!")
        if debug_mode:
            st.write(f"- Words in sample: {quality['words_in_sample']}")
            st.write(f"- Avg word length: {quality['avg_word_length']:.1f} chars")
            st.text("Sample of cleaned text:")
            st.code(quality['sample'])
        
        # Offer to fix
        if st.button("🔧 Apply automatic spacing fix"):
            import re
            # Emergency fixes
            t = re.sub(r"([a-z])([A-Z])", r"\1 \2", t)
            t = re.sub(r"([.!?,;:])([A-Za-z])", r"\1 \2", t)
            t = re.sub(r"(\d)([A-Za-z])", r"\1 \2", t)
            st.success("Applied spacing fixes!")
            quality = check_text_quality(t)
    
    # Debug view
    if debug_mode:
        col1, col2 = st.columns(2)
        with col1:
            st.text_area("Original (first 500)", raw_text[:500], height=200, key="orig")
        with col2:
            st.text_area("Cleaned (first 500)", t[:500], height=200, key="clean")

    with st.spinner("Chunking on full sentences..."):
        max_chars = pick_chunk_size(t)
        chunks = TextProcessor.smart_split_into_chunks(t, max_length=max_chars)
        st.caption(f"Voice: {voice} · Chunk size: {max_chars} · Chunks: {len(chunks)}")

    # Preview button
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("🔊 Preview (30 sec)", key="preview"):
            preview_text = chunks[0][:400] if chunks else t[:400]
            with st.spinner("Generating preview..."):
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    synthesize_best_quality_mp3(
                        preview_text, voice, tmp.name, 
                        rate_pct, pitch_hz, volume_pct
                    )
                    st.audio(tmp.name, format="audio/mp3")
                    st.caption("Preview - first 30 seconds")

import time

if st.button("🎧 Generate Audio", key="generate"):
    started = time.monotonic()
    total = len(chunks)

    prog = st.progress(0, text="Starting… 0%")
    with st.status("Preparing to generate audio…", expanded=True) as st_status:
        try:
            st_status.write(f"📚 Chunks ready: {total} · Voice: {voice} · Rate: {rate_pct}% · Pitch: {pitch_hz}Hz")

            with tempfile.TemporaryDirectory() as td:
                part_paths = []

                for i, ch in enumerate(chunks, 1):
                    st_status.write(f"🔊 Generating chunk {i}/{total} ({len(ch):,} chars)")
                    part_path = os.path.join(td, f"part_{i:03d}.mp3")

                    synthesize_best_quality_mp3(
                        ch, voice, part_path,
                        rate_pct=rate_pct, pitch_hz=pitch_hz, volume_pct=volume_pct
                    )
                    part_paths.append(part_path)

                    frac = i / total
                    prog.progress(frac, text=f"Generating… {int(frac * 100)}%")

                st_status.write("📎 Merging audio parts…")
                final_bytes = b"".join(open(p, "rb").read() for p in part_paths)

            elapsed = time.monotonic() - started
            st_status.update(label=f"✅ Done in {elapsed:.1f}s", state="complete")

            # filenames
            out_base = Path(uploaded.name).stem
            mp3_name = f"{out_base}.mp3"
            clean_name = f"{out_base}.clean.txt"

            # downloads
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "⬇️ Download MP3",
                    data=final_bytes,
                    file_name=mp3_name,
                    mime="audio/mpeg",
                )
            with c2:
                st.download_button(
                    "⬇️ Download Cleaned Text",
                    data=t.encode("utf-8"),
                    file_name=clean_name,
                    mime="text/plain",
                )

            st.success(f"Generated {total} chunks in {elapsed:.1f}s")
            st.caption(f"Voice: {voice} · Rate: {rate_pct}% · Pitch: {pitch_hz}Hz · Chunk size: {max_chars}")

        except Exception as e:
            st_status.update(label="❌ Failed", state="error")
            st.error(f"Error during generation: {e}")

    # Stats
    stats = TextProcessor.get_text_stats(t)
    st.write(
        f"**Words:** {stats['words']:,} · **Characters:** {stats['characters']:,} · "
        f"**Estimated audio:** {stats['estimated_audio_minutes']:.1f} min"
    )