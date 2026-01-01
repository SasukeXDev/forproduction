import os
from bot.server.template.video import tg_url, filename
import subprocess
from pathlib import Path
import yt_dlp
import re

BASE_DIR = Path("streams/hls")

def safe_id(filename: str) -> str:
    filename = name.lower()
    filename = re.sub(r"\.[^.]+$", "", filename)   # remove extension
    filename = re.sub(r"[^a-z0-9]+", "-", filename)
    return filename.strip("-")

def convert(tg_url: str, filename: str):
    video_id = safe_id(filename)
    out_dir = BASE_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    input_file = out_dir / "input.mp4"
    hls_file = out_dir / "master.m3u8"

    print("VIDEO ID:", video_id)

    # 1️⃣ Download video
    ydl_opts = {
        "outtmpl": str(input_file),
        "format": "best",
        "merge_output_format": "mp4",
        "quiet": False
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([tg_url])

    # 2️⃣ Convert to browser-safe HLS
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "main",
        "-level", "4.0",
        "-c:a", "aac",
        "-f", "hls",
        "-hls_time", "6",
        "-hls_list_size", "0",
        "-hls_flags", "independent_segments",
        "-hls_segment_filename", f"{out_dir}/seg_%03d.ts",
        str(hls_file)
    ]

    subprocess.run(cmd, check=True)
    print("HLS READY:", hls_file)


if __name__ == "__main__":
    convert(
        "TELEGRAM_STREAM_URL_HERE",
        "Stranger Things S05E08 720p 10bit WEBRip x265 HEVC.mkv"
    )

# 🔹 Example usage
if __name__ == "__main__":

