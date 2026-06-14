from gtts import gTTS
from pathlib import Path

text = """
Okay team, let's go over today's action items.
Sarah will finish the analytics dashboard by Friday.
We decided to push the product launch to next month due to performance issues.
Amit, can you follow up with the design team on the new mockups by Wednesday?
Also, Priya raised a concern about the budget for Q3.
We agreed to revisit the budget allocation in next week's meeting.
"""

output_path = Path(__file__).resolve().parents[2] / "test_audio"
output_path.mkdir(exist_ok=True)

tts = gTTS(text=text.strip(), lang="en")
tts.save(str(output_path / "test_meeting.mp3"))

print(f"Audio saved to: {output_path / 'test_meeting.mp3'}")