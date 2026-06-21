"""
transcriber.py — Audio meeting transcription using Groq Whisper API.

Why Groq Whisper over OpenAI Whisper:
    Groq's Whisper API is completely free with the same API key
    already used for the LLM. whisper-large-v3 offers near-perfect
    transcription quality for clear speech, at zero cost.

Why API-based over local Whisper:
    Local Whisper models require significant RAM and GPU for
    reasonable speed — same deployment constraint as embeddings.
    API-based keeps the deployment lightweight.
"""

import os
from pathlib import Path
from datetime import datetime, date
from dotenv import load_dotenv
from groq import Groq

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DATA_PATH = Path(__file__).resolve().parents[2] / "data"

SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm"}


def get_whisper_client() -> Groq:
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    """
    Transcribe audio bytes to text using Groq Whisper.
    Kept for backward compatibility — returns plain text only.
    """
    client = get_whisper_client()

    transcription = client.audio.transcriptions.create(
        file=(filename, audio_bytes),
        model="whisper-large-v3",
        response_format="text",
    )

    return transcription.strip()


def transcribe_audio_with_segments(audio_bytes: bytes, filename: str) -> dict:
    """
    Transcribe audio bytes to text using Groq Whisper, returning
    both the full text and segment-level timestamps.

    Why this exists separately from transcribe_audio():
        verbose_json is needed for speaker diarization (timestamp
        merging) but costs slightly more response parsing overhead.
        Keeping both lets callers choose based on whether they need
        diarization or just plain text.

    Args:
        audio_bytes — raw audio file content
        filename    — original filename (used for format detection)

    Returns:
        {
            "text": str,
            "segments": [{"start": float, "end": float, "text": str}, ...]
        }
    """
    client = get_whisper_client()

    transcription = client.audio.transcriptions.create(
        file=(filename, audio_bytes),
        model="whisper-large-v3",
        response_format="verbose_json",
    )

    segments = [
        {
            "start": seg.start if hasattr(seg, "start") else seg["start"],
            "end":   seg.end   if hasattr(seg, "end")   else seg["end"],
            "text":  (seg.text if hasattr(seg, "text") else seg["text"]).strip(),
        }
        for seg in transcription.segments
    ]

    return {
        "text":     transcription.text.strip(),
        "segments": segments,
    }


def save_transcript(
    transcript_text: str,
    meeting_title: str,
    meeting_date: str = None,
) -> dict:
    """
    Save a transcript as a .txt file in data/ following the
    naming convention meeting_YYYY_MM_DD.txt so it integrates
    seamlessly with the existing ingest pipeline.

    Args:
        transcript_text — the transcribed text
        meeting_title   — title for the meeting (added as header)
        meeting_date    — optional date string "YYYY-MM-DD",
                          defaults to today

    Returns:
        dict with status, filename, and path
    """
    if not meeting_date:
        meeting_date = date.today().strftime("%Y-%m-%d")

    # Validate date format
    try:
        datetime.strptime(meeting_date, "%Y-%m-%d")
    except ValueError:
        meeting_date = date.today().strftime("%Y-%m-%d")

    date_underscored = meeting_date.replace("-", "_")
    filename = f"meeting_{date_underscored}.txt"
    file_path = DATA_PATH / filename

    # If file already exists, append a suffix to avoid overwriting
    counter = 1
    while file_path.exists():
        filename  = f"meeting_{date_underscored}_{counter}.txt"
        file_path = DATA_PATH / filename
        counter  += 1

    # Build content with header — matches the format expected by
    # extract_metadata() and extract_title() in ingest.py
    content = (
        f"Meeting Title: {meeting_title}\n"
        f"Date: {meeting_date}\n"
        f"Participants: (transcribed from audio)\n\n"
        f"{transcript_text}\n"
    )

    DATA_PATH.mkdir(exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

    return {
        "status":   "success",
        "filename": filename,
        "path":     str(file_path),
    }


# ── Test directly ─────────────────────────────────────────────────
if __name__ == "__main__":
    audio_path = Path(__file__).resolve().parents[2] / "test_audio" / "test_meeting.mp3"

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    print("Transcribing audio...")
    text = transcribe_audio(audio_bytes, "test_meeting.mp3")
    print(f"Transcript: {text}\n")

    print("Saving transcript...")
    result = save_transcript(
        transcript_text=text,
        meeting_title="Test Recorded Meeting",
        meeting_date="2024-12-01",
    )
    print(f"Saved: {result}")