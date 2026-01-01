import os
import subprocess
from pathlib import Path
import yt_dlp

HLS_DIR = "streams/hls"

def download_and_convert_to_hls(tg_url):
    video_id = tg_url.split("/")[-1].split("?")[0]
    output_dir = Path(HLS_DIR) / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    input_file = output_dir / "input.mkv"

    # 1️⃣ Download BEST with all audio + subs
    ydl_opts = {
        "outtmpl": str(input_file),
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mkv",
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["all"],
        "quiet": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([tg_url])

    master = output_dir / "master.m3u8"

    # 2️⃣ FFmpeg → real HLS with tracks
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_file),

        # VIDEO (browser-safe)
        "-map", "0:v:0",
        "-c:v", "libx264",
        "-profile:v", "main",
        "-level", "4.0",
        "-pix_fmt", "yuv420p",

        # AUDIO (ALL TRACKS)
        "-map", "0:a?",
        "-c:a", "aac",

        # SUBTITLES → WebVTT
        "-map", "0:s?",
        "-c:s", "webvtt",

        # HLS FLAGS
        "-f", "hls",
        "-hls_time", "6",
        "-hls_playlist_type", "vod",
        "-hls_flags", "independent_segments",
        "-hls_segment_type", "mpegts",
        "-hls_segment_filename", f"{output_dir}/seg_%v_%03d.ts",

        # STREAM MAPPING
        "-var_stream_map",
        "v:0,a:0,agroup:audio "
        "a:1,agroup:audio "
        "s:0,sgroup:subs "
        "s:1,sgroup:subs",

        str(master)
    ]

    subprocess.run(cmd, check=True)

    return str(master)
