import os
import subprocess
from pathlib import Path
from bot.server.template.video import tg_url
import yt_dlp

# Directory to store HLS output
HLS_DIR = "streams/hls"

def download_and_convert_to_hls(tg_url):
    """
    1. Download Telegram stream with yt-dlp
    2. Convert to HLS (.m3u8 + .ts) using ffmpeg
    """
    # Create unique folder
    filename = tg_url.split("/")[-1].split("?")[0]
    output_dir = os.path.join(HLS_DIR, filename)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Download video temporarily
    temp_file = os.path.join(output_dir, "temp.mp4")
    ydl_opts = {
        "outtmpl": temp_file,
        "format": "bestvideo+bestaudio/best",
        "quiet": False
    }

    print(f"[INFO] Downloading Telegram video: {tg_url}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([tg_url])

    # Convert to HLS
    master_file = os.path.join(output_dir, "master.m3u8")
    cmd = [
        "ffmpeg",
        "-y",
        "-i", temp_file,
        "-c:v", "copy",
        "-c:a", "copy",
        "-c:s", "webvtt",
        "-f", "hls",
        "-hls_time", "6",
        "-hls_list_size", "0",
        "-hls_flags", "independent_segments",
        "-hls_segment_filename", f"{output_dir}/seg_%03d.ts",
        master_file
    ]

    print(f"[INFO] Converting to HLS...")
    subprocess.run(cmd, check=True)

    # Remove temp file to save space
    os.remove(temp_file)

    print(f"[SUCCESS] HLS available at: {master_file}")
    return master_file

if __name__ == "__main__":
   #  tg_url = input("Enter Telegram stream URL: ")
  #   hls_master = download_and_convert_to_hls(tg_url)
  #   print(f"Use this HLS link in Video.js: {hls_master}")
