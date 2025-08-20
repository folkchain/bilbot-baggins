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
      /* Announce light; pin theme tokens used by Streamlit components */
      :root,
      :root [data-theme="light"],
      :root [data-theme="dark"] {{
        color-scheme: light;
        --text-color: #2E2A22 !important;
        --background-color: #F4EEDA !important;
        --secondary-background-color: #EFE7CC !important;
        --primary-color: #4A7C59 !important;
      }}

      /* App container: set the base text color and make ALL descendants inherit it */
      .stApp,
      [data-testid="stAppViewContainer"] {{
        background: #F4EEDA !important;
        color: #2E2A22 !important;
      }}
      .stApp *, [data-testid="stAppViewContainer"] * {{
        color: inherit !important;
      }}

      /* Sidebar surface + inherit text */
      section[data-testid="stSidebar"] > div {{
        background: #EFE7CC !important;
        color: #2E2A22 !important;
      }}
      section[data-testid="stSidebar"] * {{ color: inherit !important; }}

      /* Markdown/Text containers (common white-text culprits in prod) */
      [data-testid="stMarkdownContainer"], .stMarkdown, .stText, .stCaption, .stAlert {{
        color: #2E2A22 !important;
      }}
      [data-testid="stMarkdownContainer"] * {{ color: inherit !important; }}

      /* Inputs / selects (BaseWeb) */
      .stSelectbox div[data-baseweb="select"] > div,
      .stTextInput input, .stTextArea textarea {{
        background: #F4EEDA !important;
        color: #2E2A22 !important;
        border: 2px solid #3A2F21 !important;
      }}
      .stSelectbox [data-baseweb="select"] * {{ color: #2E2A22 !important; }}
      .stSelectbox [data-baseweb="select"] svg {{ fill: #2E2A22 !important; }}

      /* Buttons: keep your brand foreground on the button itself */
      .stButton>button, .stDownloadButton>button {{
        border-radius: 12px; padding: 10px 16px; border: 2px solid #3A2F21;
        background:#4A7C59 !important; color:#F4EEDA !important; font-weight:600;
      }}

      /* Code blocks */
      pre, code {{ color: #2E2A22 !important; }}

      /* Your hero (unchanged visually; just add !important so it wins) */
      .bilbot-hero {{
        display:flex; align-items:center; gap:16px; margin: 4px 0 12px 0;
        padding: 12px 16px; border-radius: 16px;
        background: #EFE7CC !important; border: 2px solid #D7CCAA !important;
        box-shadow: 0 4px 14px rgba(60, 55, 45, 0.08);
      }}
      .bilbot-hero img {{
        width: 120px; height: auto; border-radius: 16px; border: 2px solid #3A2F21;
      }}
      .bilbot-title {{
        font-family: Georgia, 'Times New Roman', serif;
        font-weight: 700; font-size: 28px; line-height: 1.1; margin: 0;
        color: #2E2A22 !important;
      }}
      .bilbot-sub {{
        margin: 2px 0 0 0; color: #4A7C59 !important; font-size: 14px;
      }}

      /* Hard overrides for prod utilities that set white text */
      .text-white, [class*="text-white"] {{ color: #2E2A22 !important; }}
      
      /* === Streamlit file uploader: keep brown text on parchment === */
      label[data-testid="stWidgetLabel"] {{ color: #2E2A22 !important; }}

      section[data-testid="stFileUploaderDropzone"] {{
        background: #EFE7CC !important;
        color: #2E2A22 !important;
        border: 2px dashed #3A2F21 !important;
      }}
      section[data-testid="stFileUploaderDropzone"] * {{
        color: inherit !important;
        fill: currentColor !important; /* the cloud icon */
      }}

      /* The “Drag and drop…” helper text */
      [data-testid="stFileUploaderDropzoneInstructions"] {{
        color: #2E2A22 !important;
      }}
      [data-testid="stFileUploaderDropzoneInstructions"] * {{
        color: inherit !important;
      }}

      /* The “Browse files” button that lives with the dropzone */
      [data-testid="stFileUploader"] button,
      section[data-testid="stFileUploaderDropzone"] + button {{
        background: #4A7C59 !important;
        color: #F4EEDA !important;
        border: 2px solid #3A2F21 !important;
      }}

      /* === Disabled secondary button (Generate Audio before a file is uploaded) === */
      button[disabled][data-testid="stBaseButton-secondary"] {{
        background: #C9D7C9 !important; /* muted moss for disabled state */
        color: #2E2A22 !important;
        border: 2px solid #3A2F21 !important;
        opacity: 1 !important; /* avoid gray overlay that can flip text color */
      }}
      button[disabled][data-testid="stBaseButton-secondary"] * {{
        color: inherit !important;
      }}

      /* Enabled secondary buttons (e.g., "Generate Audio") */
      button[data-testid="stBaseButton-secondary"]:not([disabled]) {{
        background: #4A7C59 !important;   /* moss green */
        color: #F4EEDA !important;        /* parchment text */
        border: 2px solid #3A2F21 !important;
        font-weight: 600;
      }}
      button[data-testid="stBaseButton-secondary"]:not([disabled]) * {{
        color: inherit !important;
      }}

      /* Optional: keep hover consistent */
      button[data-testid="stBaseButton-secondary"]:not([disabled]):hover {{
        filter: brightness(1.05);
      }}

      /* Disabled secondary button state (before a file is uploaded) */
      button[disabled][data-testid="stBaseButton-secondary"] {{
        background: #C9D7C9 !important;   /* muted moss */
        color: #2E2A22 !important;
        border: 2px solid #3A2F21 !important;
        opacity: 1 !important;            /* avoid dim overlay */
      }}
      button[disabled][data-testid="stBaseButton-secondary"] * {{
        color: inherit !important;
      }}

      /* Keep secondary buttons consistent in general */
      button[data-testid="stBaseButton-secondary"]:not([disabled]) {{
        background: #4A7C59 !important;
        color: #F4EEDA !important;
        border: 2px solid #3A2F21 !important;
      }}
      /* === Status box (st.status) === */
      [data-testid="stStatus"] {{
        background: #EFE7CC !important;            /* lighter parchment */
        color: #2E2A22 !important;                 /* warm brown text */
        border: 2px solid #3A2F21 !important;
        border-radius: 12px !important;
      }}
      [data-testid="stStatus"] * {{
        color: inherit !important;
      }}

      /* === Progress bar (st.progress) === */
      [data-testid="stProgressBar"] > div {{
        background: #D7CCAA !important;            /* track color */
      }}
      [data-testid="stProgressBar"] div[role="progressbar"] {{
        background: #4A7C59 !important;            /* fill color (moss green) */
      }}
      /* Progress label text (e.g., "Generating… 42%") */
      [data-testid="stProgressBar"] [data-testid="stProgressBarLabel"] {{
        color: #2E2A22 !important;
      }}
      /* === Make horizontal rules (st.write("---") / st.divider()) visible in prod === */
      [data-testid="stMarkdownContainer"] hr,
      hr,
      [role="separator"] {{
        border: 0 !important;
        border-top: 2px solid #3A2F21 !important;  /* warm brown line */
        height: 0 !important;
        opacity: 1 !important;
        margin: 16px 0 !important;
      }}

      div[data-baseweb="slider"]:has([aria-label="Pitch (Hz change)"]) > div > div {{ background-color: #D7CCAA !important; }}
      div[data-baseweb="slider"]:has([aria-label="Pitch (Hz change)"]) > div > div > div {{ background-color: #4A7C59 !important; }}
      div[data-baseweb="slider"]:has([aria-label="Pitch (Hz change)"]) [role="slider"] {{ background-color: #4A7C59 !important; border: 1px solid #fff !important; box-shadow: 0 0 0 4px rgba(74,124,89,.18) !important; }}
      div[data-baseweb="slider"]:has([aria-label="Pitch (Hz change)"]) [data-testid="stSliderThumbValue"] {{ background: #4A7C59 !important; color: #fff !important; }}
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

async def synthesize_mp3_async(text: str, voice: str, out_path: str, rate_pct: int, pitch_hz: int):
    communicate = edge_tts.Communicate(
      text=text,
      voice=voice,
      rate=f"{signed(rate_pct)}%",
      pitch=f"{signed(pitch_hz)}Hz"
    )
    try:
        await communicate.save(out_path, output_format="audio-24khz-96kbitrate-mono-mp3")
    except TypeError:  # some older builds may not accept output_format here
        await communicate.save(out_path)  # fall back to library default


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

st.markdown("""
---
### **Important Notes**

- **Audio quality depends on your source file** - Clear text files produce better results than scanned/image-based PDFs.
- **OCR is complex** - Advanced text extraction and cleaning is applied, but some documents may still have errors.
- **Work in progress** - Regular improvements are made to text processing and cleaning algorithms.
- **For Better Results** - 1. Save a copy of your PDF. 2. Prepare the copy by deleting all blank pages, title page, copyright page, table of contents, index, & endnotes. 3. Crop the PDF to remove page headers and footers. 4. Download the cleaned text file, edit, and upload.

---
""")

default_idx = VOICES.index(DEFAULT_VOICE) if DEFAULT_VOICE in VOICES else 0
voice = st.selectbox("Voice", VOICES, index=default_idx, key="voice")
rate_pct = st.slider("Rate (% change)", -20, 20, 0, 1, key="rate")
pitch_hz = st.slider("Pitch (Hz change)", -20, 20, 0, 1, key="pitch")

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
    chunks = st.session_state.get('chunks', [])
    if not chunks:
        st.warning("No chunks available yet. Upload a file and process it first.")
        st.stop()

    total = len(chunks)
    prog = st.progress(0, text="Starting… 0%")
    status = st.empty()  # small, inline status text
    started = time.monotonic()

    try:
        with tempfile.TemporaryDirectory() as td:
            part_paths = []

            for i, ch in enumerate(chunks, 1):
                if not ch.strip():
                    continue

                status.write(f"🔊 Generating audio… {i}/{total}")
                part_path = os.path.join(td, f"part_{i:03d}.mp3")
                safe_chunk = sanitize_for_tts(ch)

                asyncio.run(synthesize_mp3_async(
                    safe_chunk, voice, part_path,
                    rate_pct, pitch_hz
                ))
                part_paths.append(part_path)

                frac = i / total
                prog.progress(frac, text=f"Generating… {int(frac * 100)}%")

            prog.progress(1.0, text="Merging audio…")
            final_bytes = b"".join(open(p, "rb").read() for p in part_paths)

        st.session_state.mp3_bytes = final_bytes
        out_base = Path(uploaded.name).stem
        st.session_state.mp3_filename = f"{out_base}.mp3"
        st.session_state.txt_filename = f"{out_base}.clean.txt"

        elapsed = time.monotonic() - started
        prog.progress(1.0, text=f"Done in {elapsed:.1f}s")

    except Exception as e:
        prog.progress(0.0, text="Failed")
        st.error(f"Error on chunk {i}: {e}")
        st.text_area("Problematic Text", ch, height=200)
        st.session_state.mp3_bytes = None

    finally:
        # clear transient status widgets so the success UI is visible beneath
        status.empty()
        # keep the final progress text visible; comment the next line if you'd prefer it to stay
        # prog.empty()

if st.session_state.get('mp3_bytes'):
    st.success("✅ Your audiobook is ready!")
    c1, c2 = st.columns(2)
    c1.download_button( "⬇️ Download MP3", data=st.session_state.mp3_bytes, file_name=st.session_state.mp3_filename, mime="audio/mpeg")
    c2.download_button("⬇️ Download Cleaned Text", data=st.session_state.cleaned_text.encode("utf-8"), file_name=st.session_state.txt_filename, mime="text/plain")
    
    if st.button("🔄 Reset and Start Over"):
        st.session_state.clear()
        st.rerun()