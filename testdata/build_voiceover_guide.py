"""Prepare the scene-by-scene script for a human replacement narration."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
scenes = json.loads((ROOT / "testdata/live_demo_script.json").read_text(encoding="utf-8"))
result = json.loads((ROOT / "testdata/live_demo_results.json").read_text(encoding="utf-8"))
timeline = result["scenes"]
assert len(scenes) == len(timeline)


def clock(seconds: float) -> str:
    rounded = round(seconds)
    return f"{rounded // 60:02}:{rounded % 60:02}"


lines = [
    "# Zamp live demo — human voiceover guide",
    "",
    "This is a real browser recording using synthetic practice data. The spoken guide is optional. "
    "Read the paragraphs below in a natural conversational voice, or send a recording and the editor "
    "can align it with the footage. Each heading gives the approximate start time.",
    "",
]
zero = timeline[0]["start"]
for scene, item in zip(scenes, timeline):
    lines.extend([
        f"## {clock(item['start'] - zero)} — {scene['title']}",
        "",
        scene["text"],
        "",
    ])
lines.extend([
    "## Recording notes",
    "",
    "- Speak as if you are guiding one evaluator through the site; leave a small pause between scenes.",
    "- Say P-A-N and G-S-T number clearly. Keep the synthetic-data disclosure in the last scene.",
    "- A phone or laptop microphone in a quiet room is enough. Send a WAV, MP3, or M4A file for alignment.",
    "- The supplied voiceover-ready MP4 already has subtitles burned into the picture.",
    "",
])
destination = ROOT / "grade_evidence/zamp-live-demo-voiceover-guide.md"
destination.write_text("\n".join(lines), encoding="utf-8")
print(destination)
