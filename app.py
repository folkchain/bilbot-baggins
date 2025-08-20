# -*- coding: utf-8 -*-
import os
import gc
import asyncio
import tempfile
from pathlib import Path
import time

import streamlit as st
from PIL import Image
import base64

import edge_tts
from edge_tts import VoicesManager

from text_processor import TextProcessor
from textproc.chunking import split_into_sentences

# add this import (assumes you added clean_document into textproc/cleaners.py)
try:
    from textproc.cleaners import clean_document
except Exception:
    # Fallback: if you haven't created clean_document yet, fall back to existing TextProcessor.clean_text
    def clean_document(text: str, kind: str) -> str:
        # PDF flags from your UI are handled later; here we just reuse your old clean_text
        return TextProcessor.clean_text(
            text, remove_running_headers=True, remove_bottom_footnotes=True
        )


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
# MEMORY MANAGEMENT FOR STREAMLIT CLOUD
# ============================================================================


def get_memory_info():
    """Get memory usage stats for monitoring."""
    try:
        import psutil

        process = psutil.Process()
        mem_info = process.memory_info()
        return {
            "rss_mb": mem_info.rss / 1024 / 1024,
            "percent": psutil.virtual_memory().percent,
        }
    except:
        return {"rss_mb": 0, "percent": 0}


def check_and_clean_memory(threshold_percent=85):
    """Check memory and clean if needed."""
    mem = get_memory_info()
    if mem["percent"] > threshold_percent:
        gc.collect()
        # Clear Streamlit caches if critical
        if mem["percent"] > 90:
            st.cache_data.clear()
            st.cache_resource.clear()
        return get_memory_info()["percent"] < threshold_percent
    return True


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


def coalesce_chunks(chunks, target=3300, hard_cap=3800):
    """
    Greedily merge adjacent chunks up to ~target without exceeding hard_cap.
    Keeps order; reduces chunk count.
    """
    out, buf, size = [], [], 0
    for ch in chunks:
        L = len(ch)
        if not buf:
            buf, size = [ch], L
            continue
        if size + 1 + L <= hard_cap and (
            size + 1 + L <= target or size < target * 0.75
        ):
            buf.append(ch)
            size += 1 + L  # +1 for join newline/space
        else:
            out.append("\n\n".join(buf))
            buf, size = [ch], L
    if buf:
        out.append("\n\n".join(buf))
    return out


def signed(val: int) -> str:
    return f"+{val}" if val >= 0 else str(val)


def pick_chunk_size(text: str) -> int:
    """
    Aim for larger text chunks, then let TTS enforce SAFE_MAX later.
    """
    try:
        sents = split_into_sentences(text)
        if not sents:
            return 3000
        avg = sum(len(s) for s in sents) / max(1, len(sents))
        mx = max(len(s) for s in sents)

        # Base target
        size = 3000

        # If you have very long sentences, back off
        if mx > 3200:
            size = 2600
        elif avg > 300:
            size = 2800
        elif avg < 120:
            size = 3200

        # Bound it
        return max(2000, min(size, 3400))
    except Exception:
        return 3000


def sanitize_for_tts(text: str) -> str:
    # very light sanitizer — we avoid aggressive transforms here
    return text.replace("&", " and ").replace("<", "").replace(">", "")


# ============================================================================
# OPTIMIZED AUDIO GENERATION WITH MEMORY MANAGEMENT
# ============================================================================


async def synthesize_mp3_async(
    text: str, voice: str, out_path: str, rate_pct: int, pitch_hz: int
):
    """Async synthesis with memory awareness."""
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
    """
    Enhanced retry with memory checking.
    """
    for attempt in range(1, tries + 1):
        # Check memory before each attempt
        if not check_and_clean_memory(85):
            return False  # Skip if memory is too high

        try:
            asyncio.run(synthesize_mp3_async(text, voice, out_path, rate_pct, pitch_hz))
            return True
        except Exception:
            time.sleep(delay * attempt)
    return False


# ============================================================================
# CACHING FOR FILE PROCESSING
# ============================================================================

import hashlib


@st.cache_data(max_entries=3, ttl=900)
def process_file_unified(
    file_bytes: bytes,
    file_name: str,
    remove_headers: bool,
    remove_footnotes: bool,
) -> dict:
    """
    One function to:
      - detect kind (txt/pdf)
      - extract/decode
      - clean with the right path
      - chunk
    Returns a dict with raw_text, cleaned_text, chunks, meta.
    """
    name = file_name or "upload"
    ext = Path(name).suffix.lower()
    is_pdf = ext == ".pdf" or file_bytes.startswith(b"%PDF-")
    kind = "pdf" if is_pdf else "txt"

    # 1) extract / decode
    if is_pdf:
        raw_text = TextProcessor.read_pdf_file(file_bytes)
    else:
        raw_text = TextProcessor.read_text_file(file_bytes)

    if not raw_text or not raw_text.strip():
        return {
            "raw_text": raw_text or "",
            "cleaned_text": "",
            "chunks": [],
            "meta": {"kind": kind, "error": "Empty after extraction"},
        }

    # 2) clean with correct path
    # clean_document handles kind=txt without page logic, kind=pdf with page logic
    cleaned_text = clean_document(raw_text, kind=kind)

    if len(cleaned_text.strip()) < max(50, int(0.02 * len(raw_text))):
        cleaned_text = raw_text  # fallback to raw rather than return nearly empty

    # Optionally honor UI toggles for PDF path
    if is_pdf:
        # If the router’s PDF path already did headers/footnotes, you can skip this.
        # If you want to enforce per-toggle behavior, you can lightly re-run:
        cleaned_text = TextProcessor.clean_text(
            cleaned_text,
            remove_running_headers=remove_headers,
            remove_bottom_footnotes=remove_footnotes,
        )

    # 3) chunk
    def pick_chunk_size_for(text: str) -> int:
        try:
            sents = split_into_sentences(text)
            if not sents:
                return 2200
            avg = sum(len(s) for s in sents) / max(1, len(sents))
            size = 2200
            if max(len(s) for s in sents) > 2400:
                size = 1800
            elif avg > 300:
                size = 2000
            elif avg < 120:
                size = 2600
            return max(1500, min(size, 2800))
        except Exception:
            return 2200

    chunk_size = pick_chunk_size_for(cleaned_text)
    chunks = TextProcessor.smart_split_into_chunks(cleaned_text, max_length=chunk_size)
    chunks = coalesce_chunks(chunks, target=3300, hard_cap=3800)

    return {
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "chunks": chunks,
        "meta": {
            "kind": kind,
            "file_name": name,
            "chars_raw": len(raw_text),
            "chars_clean": len(cleaned_text),
            "chunk_size": chunk_size,
            "num_chunks": len(chunks),
        },
    }


def make_file_id(file_bytes: bytes, file_name: str) -> str:
    # stable cache key to drive reprocessing decisions
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

# Memory monitor in sidebar
with st.sidebar:
    mem_info = get_memory_info()
    if mem_info["percent"] > 80:
        st.warning(f"⚠️ Memory: {mem_info['percent']:.0f}%")
        if st.button("Clear Memory"):
            # Keep user preferences
            keys_to_keep = {"voice", "rate", "pitch", "rm_hdr", "rm_foot"}
            for key in list(st.session_state.keys()):
                if key not in keys_to_keep:
                    del st.session_state[key]
            st.cache_data.clear()
            gc.collect()
            st.rerun()
    else:
        st.success(f"Memory: {mem_info['percent']:.0f}% OK")

# File uploader with 50MB limit
uploaded = st.file_uploader(
    "Upload a PDF or TXT (max 50MB)", type=["pdf", "txt"], key="upload"
)

# Check file size
if uploaded:
    file_size_mb = uploaded.size / (1024 * 1024)
    if file_size_mb > 50:
        st.error(f"File too large ({file_size_mb:.1f}MB). Maximum size is 50MB.")
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

current_options = (remove_headers, remove_footnotes)
# app.py upload handler
if uploaded:
    # Read once
    file_bytes = uploaded.getvalue()
    file_name = uploaded.name

    # Build file id and check for option or file changes
    file_identifier = make_file_id(file_bytes, file_name)
    needs_processing = file_identifier != st.session_state.get(
        "last_file_identifier"
    ) or (remove_headers, remove_footnotes) != st.session_state.get("last_options")

    if needs_processing:
        st.session_state.last_file_identifier = file_identifier
        st.session_state.last_options = (remove_headers, remove_footnotes)
        st.session_state.mp3_bytes = None
        st.session_state.mp3_filename = ""
        st.session_state.txt_filename = ""

        # memory hygiene
        for key in ("chunks", "cleaned_text"):
            if key in st.session_state:
                del st.session_state[key]
        gc.collect()

        if not check_and_clean_memory(80):
            st.error(
                "Insufficient memory. Use the sidebar button to clear and try again."
            )
            st.stop()

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

                # helpful telemetry
                meta = result["meta"]
                st.success(
                    f"Kind: {meta['kind'].upper()} • Raw: {meta['chars_raw']} chars • "
                    f"Clean: {meta['chars_clean']} chars • Chunks: {meta['num_chunks']} "
                    f"(~{meta['chunk_size']} chars)"
                )

    # Show quick status when not reprocessing
    if st.session_state.get("cleaned_text"):
        st.write(
            f"Raw chars: {len(st.session_state.cleaned_text) + 0} "
            f"→ Cleaned chars: {len(st.session_state.cleaned_text)}"
        )


if st.button(
    "🎧 Generate Audio", key="generate", disabled=not st.session_state.get("chunks")
):
    chunks = st.session_state.get("chunks", [])
    if not chunks:
        st.warning("No chunks available yet. Upload a file and process it first.")
        st.stop()

    total = len(chunks)
    prog = st.progress(0, text="Starting… 0%")
    status = st.empty()
    started = time.monotonic()

    try:
        with tempfile.TemporaryDirectory() as td:
            part_paths = []
            skipped = []

            for i, ch in enumerate(chunks, 1):
                if not ch.strip():
                    continue

                # Check memory periodically
                if i % 10 == 0 and not check_and_clean_memory(85):
                    st.warning(f"Memory limit reached. Processed {i}/{total} chunks.")
                    break

                status.write(f"🔊 Generating audio… {i}/{total}")
                base_path = os.path.join(td, f"part_{i:03d}")

                safe_chunk = sanitize_for_tts(ch)

                # Hard cap and split if needed
                if len(safe_chunk) > SAFE_MAX:
                    parts = [
                        safe_chunk[j : j + SAFE_MAX]
                        for j in range(0, len(safe_chunk), SAFE_MAX)
                    ]
                else:
                    parts = [safe_chunk]

                # Synthesize each part with retry
                for j, p in enumerate(parts, 1):
                    part_path = (
                        f"{base_path}_{j:02d}.mp3"
                        if len(parts) > 1
                        else f"{base_path}.mp3"
                    )
                    ok = synthesize_with_retry(
                        p, voice, part_path, rate_pct, pitch_hz, tries=3, delay=0.8
                    )
                    if ok:
                        part_paths.append(part_path)
                    else:
                        skipped.append(p)

                frac = i / total
                prog.progress(frac, text=f"Generating… {int(frac * 100)}%")

            if not part_paths:
                raise RuntimeError("All chunks failed to synthesize.")

            prog.progress(1.0, text="Merging audio…")

            # Merge in batches to manage memory
            audio_chunks = []
            for path in part_paths:
                with open(path, "rb") as f:
                    audio_chunks.append(f.read())

                # Periodically merge and clear to prevent memory buildup
                if len(audio_chunks) >= 50:
                    partial_merge = b"".join(audio_chunks)
                    audio_chunks = [partial_merge]
                    gc.collect()

            final_bytes = b"".join(audio_chunks)
            del audio_chunks
            gc.collect()

        st.session_state.mp3_bytes = final_bytes
        out_base = Path(uploaded.name).stem
        st.session_state.mp3_filename = f"{out_base}.mp3"
        st.session_state.txt_filename = f"{out_base}.clean.txt"

        elapsed = time.monotonic() - started
        prog.progress(1.0, text=f"Done in {elapsed:.1f}s")

        # Show any skipped fragments
        if skipped:
            with st.expander(f"⚠️ Skipped {len(skipped)} fragment(s)"):
                st.write(
                    "These fragments failed after retries. You can download and review them:"
                )
                skipped_txt = "\\n\\n---\\n\\n".join(skipped)
                st.download_button(
                    "⬇️ Download skipped fragments",
                    data=skipped_txt.encode("utf-8"),
                    file_name=f"{out_base}.skipped.txt",
                    mime="text/plain",
                )

    except Exception as e:
        prog.progress(0.0, text="Failed")
        st.error(f"Error: {str(e)}")
        if "i" in locals():
            st.text_area(
                "Problematic chunk", chunks[i - 1] if i > 0 else "", height=200
            )
        st.session_state.mp3_bytes = None

    finally:
        status.empty()

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
