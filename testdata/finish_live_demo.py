"""Burn readable, speech-timed subtitles into the live browser recording."""

import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
SCENES = json.loads((ROOT / "testdata/live_demo_script.json").read_text(encoding="utf-8"))
RESULT = json.loads((ROOT / "testdata/live_demo_results.json").read_text(encoding="utf-8"))
TIMELINE = RESULT["scenes"]
assert len(SCENES) == len(TIMELINE)
OUTPUT = ROOT / "grade_evidence"
NARRATION = OUTPUT / "narration"


def seconds(value: str) -> float:
    hours, minutes, rest = value.split(":")
    whole, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(whole) + int(millis) / 1000


def stamp(value: float) -> str:
    milliseconds = round(value * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{whole:02},{milliseconds:03}"


def captions(text: str) -> list[str]:
    words = text.split()
    return [" ".join(words[index:index + 11]) for index in range(0, len(words), 11)]


blocks = []
last_end = 0.0
zero = TIMELINE[0]["start"]
for index, item in enumerate(TIMELINE):
    raw = (NARRATION / f"live-scene-{index}.srt").read_text(encoding="utf-8-sig")
    entries = re.findall(
        r"\d+\s*\n(\d\d:\d\d:\d\d,\d\d\d) --> (\d\d:\d\d:\d\d,\d\d\d)\s*\n(.+?)(?=\n\s*\n|\Z)",
        raw, re.S,
    )
    assert entries, index
    offset = item["start"] - zero
    for start_text, end_text, content in entries:
        phrases = captions(" ".join(content.split()))
        word_count = sum(len(phrase.split()) for phrase in phrases)
        elapsed = 0
        cue_start = offset + seconds(start_text)
        duration = seconds(end_text) - seconds(start_text)
        for phrase in phrases:
            start = max(last_end, cue_start + duration * elapsed / word_count)
            elapsed += len(phrase.split())
            end = max(start + 0.25, cue_start + duration * elapsed / word_count)
            blocks.append(f"{len(blocks) + 1}\n{stamp(start)} --> {stamp(end)}\n{phrase}\n")
            last_end = end

subtitle_file = OUTPUT / "zamp-live-demo.srt"
subtitle_file.write_text("\n".join(blocks), encoding="utf-8")

source = OUTPUT / "zamp-live-demo-narrated.mp4"
rendered = OUTPUT / "zamp-live-demo-subtitled.mp4"
voiceover_ready = OUTPUT / "zamp-live-demo-voiceover-ready.mp4"
subtitle_filter = (
    "scale=1422:800:flags=lanczos,"
    "pad=1600:900:89:0:color=0x173d2c,"
    "subtitles=grade_evidence/zamp-live-demo.srt:"
    "force_style='FontName=Arial,FontSize=10,PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00221911,BorderStyle=1,Outline=0.5,Shadow=0,"
    "Alignment=2,MarginV=5'"
)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run(
    [
        ffmpeg, "-y", "-loglevel", "error", "-i", str(source),
        "-vf", subtitle_filter, "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy", "-movflags", "+faststart", str(rendered),
    ],
    cwd=ROOT, check=True,
)
subprocess.run(
    [
        ffmpeg, "-y", "-loglevel", "error", "-i", str(rendered),
        "-map", "0:v:0", "-c:v", "copy", "-an", "-movflags", "+faststart",
        str(voiceover_ready),
    ],
    cwd=ROOT, check=True,
)
rendered.replace(source)
print(f"Burned {len(blocks)} captions into {source.name}; also wrote {voiceover_ready.name}")
