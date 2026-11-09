"""Generate a natural-sounding optional guide track and timed caption cues."""

import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
SCENES = json.loads((ROOT / "testdata/live_demo_script.json").read_text(encoding="utf-8"))
OUTPUT = ROOT / "grade_evidence/narration"
OUTPUT.mkdir(parents=True, exist_ok=True)
VOICE = "en-IN-PrabhatNeural"

for index, scene in enumerate(SCENES):
    media = OUTPUT / f"live-scene-{index}.mp3"
    captions = OUTPUT / f"live-scene-{index}.srt"
    wave = OUTPUT / f"live-scene-{index}.wav"
    subprocess.run(
        [
            sys.executable, "-m", "edge_tts", "--voice", VOICE, "--rate=-5%",
            "--text", scene["text"], "--write-media", str(media),
            "--write-subtitles", str(captions),
        ],
        check=True,
    )
    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
            "-i", str(media), "-ar", "22050", "-ac", "1", str(wave),
        ],
        check=True,
    )
    print(f"Voice scene {index + 1}/{len(SCENES)}: {scene['title']}", flush=True)
