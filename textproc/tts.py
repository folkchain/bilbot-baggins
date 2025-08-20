# textproc/tts.py
import asyncio
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal, Callable

import edge_tts  # in requirements
from aiofiles import open as aioopen

TTS_ERRORS_TRANSIENT = (
    edge_tts.CommunicationError,
    edge_tts.TimeoutError,
    ConnectionError,
)

def _slug(s: str, n: int = 16) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:n]

_SANITIZER = re.compile(r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]")

def sanitize(text: str) -> str:
    # Strip control chars that can break SSML/TTS
    txt = _SANITIZER.sub(" ", text)
    # Collapse extreme whitespace
    txt = re.sub(r"[ \t]{2,}", " ", txt)
    # Guard against bare '&' in SSML path (edge-tts builds SSML under the hood)
    txt = txt.replace("&", " and ")
    return txt.strip()

@dataclass
class TTSConfig:
    voice: str
    rate_pct: int  # -50..50
    pitch_hz: int  # e.g., -300..+300

    def rate_str(self) -> str:
        sign = "+" if self.rate_pct >= 0 else ""
        return f"{sign}{self.rate_pct}%"

    def pitch_str(self) -> str:
        sign = "+" if self.pitch_hz >= 0 else ""
        return f"{sign}{self.pitch_hz}Hz"

async def synth_chunk(
    text: str,
    out_dir: Path,
    cfg: TTSConfig,
    chunk_idx: int,
    max_retries: int = 5,
    first_delay: float = 0.8,
    jitter: Callable[[int], float] | None = None,
) -> Path:
    """
    Synthesize one chunk with backoff retries. Returns the mp3 path.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    text = sanitize(text)
    mp3_path = out_dir / f"{chunk_idx:05d}_{_slug(text)}.mp3"

    # Idempotency: if already exists and > 0 bytes, reuse
    if mp3_path.exists() and mp3_path.stat().st_size > 0:
        return mp3_path

    # Build the client and try with backoff
    attempt = 0
    delay = first_delay
    while True:
        attempt += 1
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=cfg.voice,
                rate=cfg.rate_str(),
                pitch=cfg.pitch_str(),
            )

            async with aioopen(mp3_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        await f.write(chunk["data"])
            # Basic sanity check: non-empty
            if mp3_path.stat().st_size < 2000:
                raise RuntimeError("Tiny MP3 output — likely silent failure.")
            return mp3_path

        except TTS_ERRORS_TRANSIENT as e:
            if attempt >= max_retries:
                raise RuntimeError(f"TTS failed after {attempt} attempts") from e
        except Exception as e:
            # Treat as transient unless it's clearly a config error
            if attempt >= max_retries:
                raise
        # backoff
        sleep_for = delay + (0.3 if jitter is None else jitter(attempt))
        await asyncio.sleep(sleep_for)
        delay = min(delay * 1.8, 8.0)
