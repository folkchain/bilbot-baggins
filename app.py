# -*- coding: utf-8 -*-
import os
import gc
import asyncio
import tempfile
from pathlib import Path
import time
import hashlib

import streamlit as st
from PIL import Image
import base64

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
    initial_sidebar_state="auto",
)


# ============================================================================
# YOUR ORIGINAL CSS - KEEPING EXACTLY AS IS
# ============================================================================


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

      /* The "Drag and drop…" helper text */
      [data-testid="stFileUploaderDropzoneInstructions"] {{
        color: #2E2A22 !important;
      }}
      [data-testid="stFileUploaderDropzoneInstructions"] * {{
        color: inherit !important;
      }}

      /* The "Browse files" button that lives with the dropzone */
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
        names = sorted(
            {v["ShortName"] for v in en_voices if "Neural" in v["ShortName"]}
        )
        if DEFAULT_VOICE in names:
            names.remove(DEFAULT_VOICE)
            names.insert(0, DEFAULT_VOICE)
        return names
    except Exception:
        # Fallback to static list for reliability
        return [
            "en-US-AndrewNeural",
            "en-US-JennyNeural",
            "en-US-GuyNeural",
            "en-US-AriaNeural",
            "en-US-DavisNeural",
            "en-US-EmmaNeural",
            "en-US-JacobNeural",
            "en-US-JasonNeural",
            "en-US-MichelleNeural",
            "en-US-NancyNeural",
            "en-US-TonyNeural",
        ]


VOICES = load_english_neural_voices()

# --- Helper Functions --------------------------------------------------------
SAFE_MAX = 1800  # conservative per-call limit for edge-tts


def pick_chunk_size(text: str) -> int:
    """
    Determine optimal chunk size based on text characteristics.
    """
    try:
        sents = split_into_sentences(text)
        if not sents:
            return 2800

        avg_sent_len = sum(len(s) for s in sents) / len(sents)
        max_sent_len = max(len(s) for s in sents)

        # Adjust based on sentence characteristics
        if max_sent_len > 3200:
            return 2400  # Very long sentences, use smaller chunks
        elif avg_sent_len > 300:
            return 2600  # Long average sentences
        elif avg_sent_len < 120:
            return 3200  # Short sentences, can use larger chunks
        else:
            return 2800  # Default

    except Exception:
        return 2800


def coalesce_chunks(chunks, target=3300, hard_cap=3800):
    """
    Greedily merge adjacent chunks up to target size without exceeding hard_cap.
    """
    if not chunks:
        return []

    merged = []
    current = []
    current_size = 0

    for chunk in chunks:
        chunk_len = len(chunk)

        if not current:
            current = [chunk]
            current_size = chunk_len
        elif current_size + chunk_len + 2 <= hard_cap:  # +2 for "\n\n"
            # Can add this chunk
            current.append(chunk)
            current_size += chunk_len + 2
        else:
            # Start new merged chunk
            merged.append("\n\n".join(current))
            current = [chunk]
            current_size = chunk_len

    if current:
        merged.append("\n\n".join(current))

    return merged


def signed(val: int) -> str:
    return f"+{val}" if val >= 0 else str(val)


def sanitize_for_tts(text: str) -> str:
    """Light sanitization for TTS."""
    return text.replace("&", " and ").replace("<", "").replace(">", "")


# ============================================================================
# OPTIMIZED AUDIO GENERATION
# ============================================================================


async def synthesize_mp3_async(
    text: str, voice: str, out_path: str, rate_pct: int, pitch_hz: int
):
    """Async synthesis."""
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=f"{signed(rate_pct)}%",
        pitch=f"{signed(pitch_hz)}Hz",
    )
    await communicate.save(out_path)


def synthesize_with_retry(
    text: str,
    voice: str,
    out_path: str,
    rate_pct: int,
    pitch_hz: int,
    tries: int = 3,
    delay: float = 0.8,
) -> bool:
    """Enhanced retry."""
    for attempt in range(1, tries + 1):
        try:
            asyncio.run(synthesize_mp3_async(text, voice, out_path, rate_pct, pitch_hz))
            return True
        except Exception:
            if attempt < tries:
                time.sleep(delay * attempt)
    return False


# ============================================================================
# CACHING FOR FILE PROCESSING
# ============================================================================


@st.cache_data(max_entries=3, ttl=900)
def process_file_unified(
    file_bytes: bytes,
    file_name: str,
    remove_headers: bool,
    remove_footnotes: bool,
) -> dict:
    """
    Unified file processing that properly uses TextProcessor.
    """
    # Detect file type
    ext = Path(file_name).suffix.lower()
    is_pdf = ext == ".pdf" or file_bytes.startswith(b"%PDF-")

    # Extract text
    if is_pdf:
        raw_text = TextProcessor.read_pdf_file(file_bytes)
    else:
        raw_text = TextProcessor.read_text_file(file_bytes)

    if not raw_text or not raw_text.strip():
        return {
            "raw_text": "",
            "cleaned_text": "",
            "chunks": [],
            "meta": {"error": "Could not extract text from file"},
        }

    # Clean text using TextProcessor
    cleaned_text = TextProcessor.clean_text(
        text=raw_text,
        remove_running_headers=remove_headers,
        remove_bottom_footnotes=remove_footnotes,
        is_pdf=is_pdf,
    )

    # Fallback if cleaning removed too much
    if len(cleaned_text.strip()) < max(50, int(0.02 * len(raw_text))):
        cleaned_text = raw_text

    # Chunk the text
    chunk_size = pick_chunk_size(cleaned_text)
    chunks = TextProcessor.smart_split_into_chunks(cleaned_text, max_length=chunk_size)

    # Coalesce small chunks
    chunks = coalesce_chunks(chunks, target=3300, hard_cap=3800)

    return {
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "chunks": chunks,
        "meta": {
            "kind": "pdf" if is_pdf else "txt",
            "file_name": file_name,
            "chars_raw": len(raw_text),
            "chars_clean": len(cleaned_text),
            "chunk_size": chunk_size,
            "num_chunks": len(chunks),
        },
    }


def make_file_id(file_bytes: bytes, file_name: str) -> str:
    """Create stable cache key."""
    h = hashlib.md5(file_bytes[:1_000_000]).hexdigest()
    return f"{file_name}:{len(file_bytes)}:{h}"


# --- UI & State Initialization ------------------------------------------------
st.session_state.setdefault("last_file_identifier", None)
st.session_state.setdefault("last_options", None)
st.session_state.setdefault("chunks", [])
st.session_state.setdefault("cleaned_text", "")
st.session_state.setdefault("mp3_bytes", None)
st.session_state.setdefault("mp3_filename", "")
st.session_state.setdefault("txt_filename", "")


# File uploader
uploaded = st.file_uploader(
    "Upload a PDF or TXT",  # non-empty for accessibility
    type=["pdf", "txt"],
    key="upload",
    label_visibility="collapsed",  # keeps clean UI
)

if uploaded:
    st.write("Filename:", uploaded.name)
    st.write("MIME type:", uploaded.type)
    st.write("Size (bytes):", uploaded.size)


# Check file size
if uploaded:
    file_size_mb = uploaded.size / (1024 * 1024)
    if file_size_mb > 200:
        st.error(f"File too large ({file_size_mb:.1f}MB). Maximum size is 200MB.")
        st.stop()

st.markdown("""
---
### **Important Notes**

- **Audio quality depends on your source file** - Clear text files produce better results than scanned/image-based PDFs.
- **OCR is complex** - Advanced text extraction and cleaning is applied, but some documents may still have errors.
- **Work in progress** - Regular improvements are made to text processing and cleaning algorithms.
- **For Better Results** - 1. Save a copy of your PDF. 2. Prepare the copy by deleting all blank pages, title page, copyright page, table of contents, index, & endnotes. 3. Crop the PDF to remove page headers and footers. 4. Download the cleaned text file, edit, and upload.

---
""")

# Voice settings
default_idx = VOICES.index(DEFAULT_VOICE) if DEFAULT_VOICE in VOICES else 0
voice = st.selectbox("Voice", VOICES, index=default_idx, key="voice")
rate_pct = st.slider("Rate (% change)", -20, 20, 0, 1, key="rate")
pitch_hz = st.slider("Pitch (Hz change)", -20, 20, 0, 1, key="pitch")

st.write("---")
st.markdown("##### Text Cleaning Options")
remove_headers = st.checkbox(
    "Remove running headers/page numbers", value=True, key="rm_hdr"
)
remove_footnotes = st.checkbox("Remove footnote markers", value=True, key="rm_foot")
st.write("---")

# Process uploaded file
if uploaded:
    file_bytes = uploaded.getvalue()
    file_name = uploaded.name

    # Check if reprocessing needed
    file_identifier = make_file_id(file_bytes, file_name)
    current_options = (remove_headers, remove_footnotes)
    needs_processing = file_identifier != st.session_state.get(
        "last_file_identifier"
    ) or current_options != st.session_state.get("last_options")

    if needs_processing:
        st.session_state.last_file_identifier = file_identifier
        st.session_state.last_options = current_options
        st.session_state.mp3_bytes = None
        st.session_state.mp3_filename = ""
        st.session_state.txt_filename = ""

        # Clear old data
        for key in ("chunks", "cleaned_text"):
            if key in st.session_state:
                del st.session_state[key]
        gc.collect()

        with st.spinner("Analyzing and cleaning text..."):
            result = process_file_unified(
                file_bytes=file_bytes,
                file_name=file_name,
                remove_headers=remove_headers,
                remove_footnotes=remove_footnotes,
            )

            err = result["meta"].get("error")
            if err:
                st.error(err)
                st.session_state.chunks = []
                st.session_state.cleaned_text = ""
            else:
                st.session_state.cleaned_text = result["cleaned_text"]
                st.session_state.chunks = result["chunks"]

                # Show stats
                meta = result["meta"]
                st.success(
                    f"**{meta['kind'].upper()}** • "
                    f"Raw: {meta['chars_raw']:,} chars • "
                    f"Clean: {meta['chars_clean']:,} chars • "
                    f"Chunks: {meta['num_chunks']}"
                )

# Generate audio button (drop-in replacement)
if st.button(
    "🎧 Generate Audio", key="generate", disabled=not st.session_state.get("chunks")
):
    chunks = st.session_state.get("chunks", [])
    if not chunks:
        st.warning("No chunks available. Upload and process a file first.")
        st.stop()

    total = len(chunks)
    prog = st.progress(0.0, text="Starting… 0%")
    status = st.empty()
    started = time.monotonic()

    try:
        with tempfile.TemporaryDirectory() as td:
            part_paths = []
            skipped = []

            # precompute per-chunk progress width
            per_chunk = 1.0 / max(1, total)

            for i, chunk in enumerate(chunks, 1):
                if not chunk.strip():
                    continue

                # Heartbeat BEFORE doing work on this chunk
                start_frac = (i - 1) * per_chunk
                prog.progress(
                    start_frac,
                    text=f"Preparing chunk {i}/{total}… {int(start_frac * 100)}%",
                )
                status.write(f"🔊 Generating audio… chunk {i}/{total}")

                base_path = os.path.join(td, f"part_{i:03d}")

                safe_chunk = sanitize_for_tts(chunk)

                # Split if over TTS limit
                if len(safe_chunk) > SAFE_MAX:
                    parts = [
                        safe_chunk[j : j + SAFE_MAX]
                        for j in range(0, len(safe_chunk), SAFE_MAX)
                    ]
                else:
                    parts = [safe_chunk]

                # Progress within this chunk
                num_parts = len(parts)
                for j, part in enumerate(parts, 1):
                    # inner progress: advance within the chunk
                    inner_frac = start_frac + (j - 1) / max(1, num_parts) * per_chunk
                    prog.progress(
                        inner_frac,
                        text=f"Chunk {i}/{total}, part {j}/{num_parts}… {int(inner_frac * 100)}%",
                    )

                    part_path = (
                        f"{base_path}_{j:02d}.mp3"
                        if num_parts > 1
                        else f"{base_path}.mp3"
                    )
                    ok = synthesize_with_retry(
                        part, voice, part_path, rate_pct, pitch_hz
                    )
                    if ok:
                        part_paths.append(part_path)
                    else:
                        skipped.append(part)

                # Mark this whole chunk as done
                done_frac = i * per_chunk
                prog.progress(
                    done_frac,
                    text=f"Completed chunk {i}/{total}… {int(done_frac * 100)}%",
                )

            if not part_paths:
                raise RuntimeError("All chunks failed to synthesize.")

            prog.progress(1.0, text="Merging audio… 100%")

            # Merge audio files
            audio_chunks = []
            for path in part_paths:
                with open(path, "rb") as f:
                    audio_chunks.append(f.read())
                if len(audio_chunks) >= 50:
                    audio_chunks = [b"".join(audio_chunks)]
                    gc.collect()

            final_bytes = b"".join(audio_chunks)
            del audio_chunks
            gc.collect()

        # Save results to session
        st.session_state.mp3_bytes = final_bytes
        out_base = Path(uploaded.name).stem
        st.session_state.mp3_filename = f"{out_base}.mp3"
        st.session_state.txt_filename = f"{out_base}.clean.txt"

        elapsed = time.monotonic() - started
        prog.progress(1.0, text=f"Done in {elapsed:.1f}s")

        if skipped:
            with st.expander(f"⚠️ Skipped {len(skipped)} fragment(s)"):
                st.write("These fragments failed after retries:")
                skipped_txt = "\n\n---\n\n".join(skipped)
                st.download_button(
                    "⬇️ Download skipped fragments",
                    data=skipped_txt.encode("utf-8"),
                    file_name=f"{out_base}.skipped.txt",
                    mime="text/plain",
                )

    except Exception as e:
        prog.progress(0.0, text="Failed")
        st.error(f"Error: {str(e)}")
        st.session_state.mp3_bytes = None
    finally:
        status.empty()


# Download section
if st.session_state.get("mp3_bytes"):
    st.success("✅ Your audiobook is ready!")
    c1, c2 = st.columns(2)
    c1.download_button(
        "⬇️ Download MP3",
        data=st.session_state.mp3_bytes,
        file_name=st.session_state.mp3_filename,
        mime="audio/mpeg",
    )
    c2.download_button(
        "⬇️ Download Cleaned Text",
        data=st.session_state.cleaned_text.encode("utf-8"),
        file_name=st.session_state.txt_filename,
        mime="text/plain",
    )

    if st.button("🔄 Reset and Start Over"):
        # Clear everything except user preferences
        keys_to_keep = {"voice", "rate", "pitch", "rm_hdr", "rm_foot"}
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]
        gc.collect()
        st.rerun()
