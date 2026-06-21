"""
diarizer.py — Speaker diarization using pyannote-audio, merged with
              Whisper transcription to produce speaker-attributed transcripts.

Why this matters:
    Without diarization, action items like "Amit committed to X" rely
    purely on names appearing in the transcript text — the system has
    no actual understanding of who spoke. With diarization, we know
    WHO said WHAT, by timestamp — enabling genuinely speaker-attributed
    retrieval instead of text pattern matching.

Pipeline:
    1. pyannote identifies speaker segments (who spoke when)
    2. Whisper provides word/segment-level timestamps
    3. We merge both by timestamp overlap to produce:
       "SPEAKER_00: Let's go over action items..."
       "SPEAKER_01: I'll have that done by Friday."

Why pyannote over alternatives:
    pyannote-audio is the open-source standard for diarization,
    used in production by major transcription services. Free,
    MIT-style license, runs locally — no per-minute API cost.
"""

import os
import torch
import soundfile as sf
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_pipeline_cache = None


def get_diarization_pipeline():
    """Lazy-load the pyannote pipeline once and cache it."""
    global _pipeline_cache
    if _pipeline_cache is None:
        from pyannote.audio import Pipeline
        _pipeline_cache = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=os.getenv("HF_TOKEN"),
        )
    return _pipeline_cache


def diarize_audio(audio_path: str) -> list[dict]:
    """
    Run speaker diarization on an audio file.

    Returns:
        List of dicts: [{"speaker": "SPEAKER_00", "start": 0.0, "end": 8.0}, ...]
    """
    pipeline = get_diarization_pipeline()

    audio_np, sample_rate = sf.read(audio_path, dtype="float32")
    if audio_np.ndim == 1:
        audio_np = audio_np[np.newaxis, :]
    else:
        audio_np = audio_np.T

    waveform = torch.from_numpy(audio_np)

    output = pipeline({"waveform": waveform, "sample_rate": sample_rate})
    annotation = output.speaker_diarization

    segments = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        segments.append({
            "speaker": speaker,
            "start":   round(turn.start, 2),
            "end":     round(turn.end, 2),
        })

    # Merge consecutive segments from the same speaker
    merged = []
    for seg in segments:
        if merged and merged[-1]["speaker"] == seg["speaker"] and seg["start"] - merged[-1]["end"] < 1.0:
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(seg)

    return merged


def merge_transcript_with_speakers(
    whisper_segments: list[dict],
    speaker_segments: list[dict],
) -> str:
    """
    Merge Whisper's text segments with pyannote's speaker segments
    by timestamp overlap, producing a speaker-labeled transcript.

    Args:
        whisper_segments — [{"start": float, "end": float, "text": str}, ...]
        speaker_segments — [{"speaker": str, "start": float, "end": float}, ...]

    Returns:
        Speaker-labeled transcript text:
        "SPEAKER_00: Let's go over action items.
         SPEAKER_01: I'll have that done by Friday."
    """
    def find_speaker(ts_start: float, ts_end: float) -> str:
        """Find which speaker's segment overlaps most with this time window."""
        best_speaker = "UNKNOWN"
        best_overlap = 0.0
        for seg in speaker_segments:
            overlap = min(ts_end, seg["end"]) - max(ts_start, seg["start"])
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = seg["speaker"]
        return best_speaker

    lines = []
    current_speaker = None
    current_text = []

    for ws in whisper_segments:
        speaker = find_speaker(ws["start"], ws["end"])

        if speaker != current_speaker:
            if current_speaker is not None:
                lines.append(f"{current_speaker}: {' '.join(current_text).strip()}")
            current_speaker = speaker
            current_text = [ws["text"].strip()]
        else:
            current_text.append(ws["text"].strip())

    if current_speaker is not None:
        lines.append(f"{current_speaker}: {' '.join(current_text).strip()}")

    return "\n".join(lines)


# ── Test directly ─────────────────────────────────────────────────
if __name__ == "__main__":
    audio_path = Path(__file__).resolve().parents[2] / "test_audio" / "test_meeting.mp3"

    print("Running diarization...")
    speakers = diarize_audio(str(audio_path))
    print(f"Found {len(speakers)} speaker segments:")
    for s in speakers:
        print(f"  {s['speaker']}: {s['start']}s - {s['end']}s")