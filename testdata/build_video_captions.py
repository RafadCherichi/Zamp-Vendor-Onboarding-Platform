"""Build timed narration captions from the verified recording timeline."""

import json
import os
import subprocess
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
scenes = json.loads((ROOT / "testdata/demo_script.json").read_text(encoding="utf-8"))
result = json.loads((ROOT / "testdata/demo_rehearsal_results.json").read_text(encoding="utf-8"))
timeline = result["scenes"]
assert len(scenes) == len(timeline)


def timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def chunks(text: str) -> list[str]:
    # Short, complete clauses read comfortably without covering the screen.
    words = text.split()
    groups = []
    while words:
        count = min(14, len(words))
        if len(words) > 14 and len(words) - count < 6:
            count = len(words) - 6
        for index in range(max(8, count - 4), count):
            if words[index - 1].endswith((".", ":", ";", "?", "!")):
                count = index
                break
        groups.append(" ".join(words[:count]))
        words = words[count:]
    return groups


zero = timeline[0]["start"]
captions = []
number = 0
for scene, item in zip(scenes, timeline):
    groups = chunks(scene["text"])
    word_total = sum(len(group.split()) for group in groups)
    elapsed_words = 0
    audio_start = item["start"] - zero
    for group in groups:
        start = audio_start + item["duration"] * elapsed_words / word_total
        elapsed_words += len(group.split())
        end = audio_start + item["duration"] * elapsed_words / word_total
        number += 1
        captions.append(f"{number}\n{timestamp(start)} --> {timestamp(end)}\n{group}\n")

destination = ROOT / "grade_evidence/zamp-submission-demo.srt"
destination.write_text("\n".join(captions), encoding="utf-8")
video = ROOT / "grade_evidence/zamp-submission-demo.mp4"
captioned = ROOT / "grade_evidence/zamp-submission-demo-captioned.mp4"
subprocess.run([
    imageio_ffmpeg.get_ffmpeg_exe(), "-y",
    "-i", str(video), "-i", str(destination),
    "-map", "0:v:0", "-map", "0:a:0", "-map", "1:0",
    "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
    "-metadata:s:s:0", "language=eng", "-metadata:s:s:0", "title=English captions",
    "-movflags", "+faststart", str(captioned),
], check=True, capture_output=True)
os.replace(captioned, video)
print(f"Wrote {number} English captions and embedded them in {video}")
