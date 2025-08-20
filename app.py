# -*- coding: utf-8 -*-
import os
import asyncio
import tempfile
from pathlib import Path

import streamlit as st
from PIL import Image
import base64
import time

import edge_tts
from edge_tts import VoicesManager

from text_processor import TextProcessor
from textproc.chunking import split_into_sentences

# --- App identity & theme -----------------------------------------------------
APP_NAME = "BilBot Baggins"
LOGO_PATH = Path("assets/bilbot-baggins-logo.png")

_logo_img = Image.open(LOGO_PATH)
st.set_page_config(
    page_title=f"{APP_NAME} - Audiobook",
    page_icon=_logo_img,
    layout="centered",
    initial_sidebar_state="auto"
)

def _inject_css():
    with open(LOGO_PATH, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    css = f"""
    <style>
      /* Force light palette everywhere */
      html, body, .stApp, [data-testid="stAppViewContainer"] {{
        background: #F4EEDA !important;
        color: #2E2A22 !important;
      }}

      /* Sidebar */
      section[data-testid="stSidebar"] > div {{
        background: #EFE7CC !important;
        color: #2E2A22 !important;
      }}

      /* Buttons */
      .stButton>button, .stDownloadButton>button {{
        border-radius: 12px; padding: 10px 16px; border: 2px solid #3A2F21;
        background:#4A7C59 !important; color:#F4EEDA !important; font-weight:600;
      }}
      .stButton>button:hover, .stDownloadButton>button:hover {{
        filter: brightness(1.05);
      }}

      /* Selectboxes and inputs */
      .stSelectbox div[data-baseweb="select"] > div,
      .stTextInput input, .stTextArea textarea {{
        background: #F4EEDA !important;
        color: #2E2A22 !important;
        border: 2px solid #3A2F21 !important;
      }}

      /* Code blocks and markdown text */
      pre, code, .stText, .stMarkdown, .stCaption, .stAlert {{
        color: #2E2A22 !important;
      }}

      /* Hero block */
      .bilbot-hero {{
        display:flex; align-items:center; gap:16px; margin: 4px 0 12px 0;
        padding: 12px 16px; border-radius: 16px;
        background: #EFE7CC !important; border: 2px solid #D7CCAA !important;
        box-shadow: 0 4px 14px rgba(60, 55, 45, 0.08);
      }}
      .bilbot-hero img {{
        width: 72px; height: 72px; border-radius: 16px; border: 2px solid #3A2F21;
      }}
      .bilbot-title {{
        font-family: Georgia, 'Times New Roman', serif;
        font-weight: 700; font-size: 28px; line-height: 1.1; margin: 0;
        color: #2E2A22 !important;
      }}
      .bilbot-sub {{
        margin: 2px 0 0 0; color: #4A7C59 !important; font-size: 14px;
      }}
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

# --- Voices --------------------------------------------------------------------
DEFAULT_VOICE = "en-US-AndrewNeural"

@st.cache_resource(show_spinner="Loading voices...")
def load_english_neural_voices():
    try:
        voices_mgr = asyncio.run(VoicesManager.create())
        en_voices = voices_mgr.find(Language="en")
        names = sorted({v["ShortName"] for v in en_voices if "Neural" in v["ShortName"]})
        if DEFAULT_VOICE in names:
            names.remove(DEFAULT_VOICE)
            names.insert(0, DEFAULT_VOICE)
        return names
    except Exception:
        return [DEFAULT_VOICE, "en-US-JennyNeural", "en-US-GuyNeural"]

VOICES = load_english_neural_voices()

# --- Helper Functions --------------------------------------------------------
def signed(val: int) -> str:
    return f"+{val}" if val >= 0 else str(val)

def pick_chunk_size(text: str) -> int:
    try:
        sents = split_into_sentences(text)
        if not sents: return 2200
        avg = sum(len(s) for s in sents) / max(1, len(sents))
        size = 2200
        if max(len(s) for s in sents) > 2400: size = 1800
        elif avg > 300: size = 2000
        elif avg < 120: size = 2600
        return max(1500, min(size, 2800))
    except Exception:
        return 2200

def sanitize_for_tts(text: str) -> str:
    return text.replace('&', ' and ').replace('<', '').replace('>', '')

async def synthesize_mp3_async(text: str, voice: str, out_path: str, rate_pct: int, pitch_hz: int, volume_pct: int):
    communicate = edge_tts.Communicate(
        text=text, voice=voice, rate=f"{signed(rate_pct)}%",
        pitch=f"{signed(pitch_hz)}Hz", volume=f"{signed(volume_pct)}%"
    )
    await communicate.save(out_path)

# --- UI & State Initialization ------------------------------------------------
st.session_state.setdefault('last_file_identifier', None)
st.session_state.setdefault('last_options', None)
st.session_state.setdefault('chunks', [])
st.session_state.setdefault('cleaned_text', "")
st.session_state.setdefault('mp3_bytes', None)
st.session_state.setdefault('mp3_filename', "")
st.session_state.setdefault('txt_filename', "")

# --- Main App Logic -----------------------------------------------------------
uploaded = st.file_uploader("Upload a PDF or TXT", type=["pdf", "txt"], key="upload")

if not uploaded:
    st.session_state.clear()

default_idx = VOICES.index(DEFAULT_VOICE) if DEFAULT_VOICE in VOICES else 0
voice = st.selectbox("Voice", VOICES, index=default_idx, key="voice")
rate_pct = st.slider("Rate (% change)", -50, 50, 0, 5, key="rate")
pitch_hz = st.slider("Pitch (Hz change)", -300, 300, 0, 10, key="pitch")
volume_pct = 0

st.write("---")
st.markdown("##### Text Cleaning Options")
remove_headers = st.checkbox("Remove running headers/page numbers", value=True, key="rm_hdr")
remove_footnotes = st.checkbox("Remove footnote markers", value=True, key="rm_foot")
st.write("---")

current_options = (remove_headers, remove_footnotes)
if uploaded:
    file_identifier = (uploaded.name, uploaded.size)
    if file_identifier != st.session_state.get('last_file_identifier') or current_options != st.session_state.get('last_options'):
        st.session_state.last_file_identifier = file_identifier
        st.session_state.last_options = current_options
        st.session_state.mp3_bytes = None

        with st.spinner("Analyzing and cleaning text..."):
            data = uploaded.read()
            ext = Path(uploaded.name).suffix.lower()
            raw_text = TextProcessor.read_pdf_file(data) if ext == ".pdf" else TextProcessor.read_text_file(data)
            
            if "ERROR:" in raw_text:
                st.error(raw_text)
                st.session_state.chunks = []
                st.session_state.cleaned_text = ""
            else:
                st.session_state.cleaned_text = TextProcessor.clean_text(
                    raw_text,
                    remove_running_headers=remove_headers,
                    remove_bottom_footnotes=remove_footnotes,
                )
                max_chars = pick_chunk_size(st.session_state.cleaned_text)
                st.session_state.chunks = TextProcessor.smart_split_into_chunks(
                    st.session_state.cleaned_text, max_length=max_chars
                )
                st.success(f"Text processed into {len(st.session_state.chunks)} chunks. Ready to generate.")

if st.button("🎧 Generate Audio", key="generate", disabled=not st.session_state.get('chunks')):
    with st.spinner("Generating audio..."):
        chunks = st.session_state.chunks
        try:
            with tempfile.TemporaryDirectory() as td:
                part_paths = []
                for i, ch in enumerate(chunks, 1):
                    if not ch.strip(): continue
                    part_path = os.path.join(td, f"part_{i:03d}.mp3")
                    safe_chunk = sanitize_for_tts(ch)
                    asyncio.run(synthesize_mp3_async(
                        safe_chunk, voice, part_path,
                        rate_pct, pitch_hz, volume_pct
                    ))
                    part_paths.append(part_path)
                final_bytes = b"".join(open(p, "rb").read() for p in part_paths)
                
                st.session_state.mp3_bytes = final_bytes
                out_base = Path(uploaded.name).stem
                st.session_state.mp3_filename = f"{out_base}.mp3"
                st.session_state.txt_filename = f"{out_base}.clean.txt"
        
        except Exception as e:
            st.error(f"Error on chunk {i}: {e}")
            st.text_area("Problematic Text", ch, height=200)
            st.session_state.mp3_bytes = None

if st.session_state.get('mp3_bytes'):
    st.success("✅ Your audiobook is ready!")
    c1, c2 = st.columns(2)
    c1.download_button( "⬇️ Download MP3", data=st.session_state.mp3_bytes, file_name=st.session_state.mp3_filename, mime="audio/mpeg")
    c2.download_button("⬇️ Download Cleaned Text", data=st.session_state.cleaned_text.encode("utf-8"), file_name=st.session_state.txt_filename, mime="text/plain")
    
    if st.button("🔄 Reset and Start Over"):
        st.session_state.clear()
        st.rerun()