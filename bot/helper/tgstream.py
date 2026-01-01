import os
from bot.server.template.video import tg_url, filename
import subprocess
from pathlib import Path
import yt_dlp

HLS_BASE = Path("streams/hls")

def convert_tg_to_hls(tg_url: str, filename: str):
    """
    filename = <!-- Filename --> (SAME as video page)
    """

    output_dir = HLS_BASE / filename
    output_dir.mkdir(parents=True, exist_ok=True)

    input_file = output_dir / "input.mkv"
    master_playlist = output_dir / "master.m3u8"

    # 1️⃣ Download Telegram stream (all audio + subs)
    ydl_opts = {
        "outtmpl": str(input_file),
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mkv",
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["all"],
        "quiet": False
    }

    print("[INFO] Downloading Telegram stream...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([tg_url])

    # 2️⃣ Convert to TRUE multi-track HLS
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_file),

        # VIDEO (browser compatible)
        "-map", "0:v:0",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "main",
        "-level", "4.0",

        # AUDIO (ALL)
        "-map", "0:a?",
        "-c:a", "aac",

        # SUBS → WebVTT
        "-map", "0:s?",
        "-c:s", "webvtt",

        # HLS
        "-f", "hls",
        "-hls_time", "6",
        "-hls_playlist_type", "vod",
        "-hls_flags", "independent_segments",
        "-hls_segment_filename", f"{output_dir}/seg_%03d.ts",

        str(master_playlist)
    ]

    print("[INFO] Creating HLS...")
    subprocess.run(cmd, check=True)

    print(f"[SUCCESS] HLS READY → {master_playlist}")
    return master_playlist


# 🔹 Example usage
if __name__ == "__main__":

