import os
import torch
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from pyannote.audio import Pipeline

print("Loading diarization pipeline...")

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    token=os.getenv("HF_TOKEN"),
)

print("✅ Pipeline loaded successfully!")

audio_path = Path(__file__).resolve().parents[2] / "test_audio" / "test_meeting.mp3"
print(f"Loading audio: {audio_path}")

# Load audio with soundfile — avoids torchcodec entirely
import soundfile as sf
import numpy as np

audio_np, sample_rate = sf.read(str(audio_path), dtype="float32")
if audio_np.ndim == 1:
    audio_np = audio_np[np.newaxis, :]   # mono -> (1, samples)
else:
    audio_np = audio_np.T                 # (samples, channels) -> (channels, samples)

waveform = torch.from_numpy(audio_np)

print(f"Audio loaded: {waveform.shape}, sample_rate={sample_rate}")
print("Running diarization...")

diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})

print("\nSpeaker segments:")
print(f"Output type: {type(diarization)}")
print(f"Available attributes: {[a for a in dir(diarization) if not a.startswith('_')]}")

# pyannote 4.x DiarizeOutput — try common access patterns
if hasattr(diarization, "speaker_diarization"):
    annotation = diarization.speaker_diarization
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        print(f"  {speaker}: {turn.start:.1f}s - {turn.end:.1f}s")
elif hasattr(diarization, "annotation"):
    annotation = diarization.annotation
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        print(f"  {speaker}: {turn.start:.1f}s - {turn.end:.1f}s")
else:
    print(diarization)