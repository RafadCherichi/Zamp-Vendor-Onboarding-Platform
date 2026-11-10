"""Render a two-second sample of the human walkthrough subtitle style."""

from pathlib import Path
import subprocess
import imageio_ffmpeg

root = Path(__file__).resolve().parent.parent
folder = root / "grade_evidence" / "human_walkthrough"
raw = max(folder.glob("*.webm"), key=lambda path: path.stat().st_mtime)
filter_text = (
    "scale=1600:900:flags=lanczos,"
    "pad=1600:1000:0:0:color=0x173d2c,"
    "subtitles=grade_evidence/human_walkthrough/zamp-rafad-walkthrough.srt:"
    "force_style='FontName=Arial,FontSize=9,PrimaryColour=&H00F8F5EC,"
    "OutlineColour=&H0015221B,BorderStyle=1,Outline=0.6,Shadow=0,"
    "Alignment=2,MarginV=4'"
)
subprocess.run(
    [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", "56", "-i", str(raw),
     "-t", "2", "-vf", filter_text, "-an", "-c:v", "libx264", "-crf", "20",
     str(folder / "qa-caption-test.mp4")],
    cwd=root, check=True,
)
subprocess.run(
    [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", "1", "-i",
     str(folder / "qa-caption-test.mp4"), "-frames:v", "1", str(folder / "qa-caption-test.png")],
    check=True,
)
