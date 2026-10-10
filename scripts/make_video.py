"""Assemble a 35-second screenshot walkthrough; requires optional FFmpeg."""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets"
SCENES = [
    ("overview.jpg", "Projenk turns synthetic CSV orders into an automated business report."),
    ("performance.jpg", "Explore monthly revenue, channels, category performance and business observations."),
    ("pipeline.jpg", "A real Python pipeline reads, cleans, validates and calculates the metrics."),
    ("audit.jpg", "832 source rows: 805 accepted, 58 normalized and 27 rejected with reasons."),
    ("reports.jpg", "Generate a standalone report and an email with the report attached. Preview only."),
    ("executive-report.jpg", "September: $54,335.43 net revenue and 289 completed orders. All data is synthetic."),
    ("project.jpg", "Inspect the source and setup guide on GitHub. The portfolio is hosted on GitHub Pages.")
]


def timestamp(seconds, separator="."):
    return f"00:{seconds // 60:02d}:{seconds % 60:02d}{separator}000"


def build():
    for name, _ in SCENES:
        if not (ASSETS / name).exists():
            raise SystemExit(f"Capture {name} from the running demo first")
    vtt = "WEBVTT\n\n" + "\n\n".join(f"{timestamp(i*5)} --> {timestamp((i+1)*5)}\n{text}" for i, (_,text) in enumerate(SCENES)) + "\n"
    (ASSETS / "demo.vtt").write_text(vtt)
    with tempfile.TemporaryDirectory(prefix="projenk-video-") as folder:
        temp = Path(folder)
        srt = "\n\n".join(f"{i+1}\n{timestamp(i*5,',')} --> {timestamp((i+1)*5,',')}\n{text}" for i, (_,text) in enumerate(SCENES)) + "\n"
        (temp / "captions.srt").write_text(srt)
        concat = "".join(f"file '{(ASSETS/name).as_posix()}'\nduration 5\n" for name,_ in SCENES)
        concat += f"file '{(ASSETS/SCENES[-1][0]).as_posix()}'\n"
        (temp / "frames.txt").write_text(concat)
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-f", "concat", "-safe", "0", "-i", str(temp/"frames.txt"),
            "-i", str(temp/"captions.srt"), "-map", "0:v", "-map", "1:s",
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p", "-r", "24",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
            "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-disposition:s:0", "default",
            "-t", "35", "-movflags", "+faststart", str(ASSETS/"demo.mp4")], check=True)
    print("Created docs/assets/demo.mp4 (35 seconds) and demo.vtt")


if __name__ == "__main__":
    build()
