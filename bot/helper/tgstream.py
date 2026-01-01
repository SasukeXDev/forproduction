import re
from pathlib import Path
import subprocess
from config import API_ID, API_HASH 
from pyrogram import Client

# 🔹 CONFIG
API_ID = ''         # Telegram API ID
API_HASH = ''
SESSION_NAME = "ano"   # or a custom session name
BASE_DIR = Path("streams/hls")

# 🔹 Helper to make browser-safe folder names
def safe_id(filename: str) -> str:
    name = filename.lower()
    name = re.sub(r"\.[^.]+$", "", name)
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")

# 🔹 Download video from Telegram
def download_from_telegram(chat_id: str, message_id: int, filename: str) -> Path:
    client = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)
    out_dir = BASE_DIR / safe_id(filename)
    out_dir.mkdir(parents=True, exist_ok=True)
    input_file = out_dir / "input.mp4"

    with client:
        print(f"⬇️ Downloading message {message_id} from {chat_id}")
        client.download_media(
            message=(chat_id, message_id),
            file_name=str(input_file)
        )
    print("✅ Download completed:", input_file)
    return input_file

# 🔹 Convert to HLS
def convert_to_hls(input_file: Path):
    out_dir = input_file.parent
    hls_file = out_dir / "master.m3u8"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "main",
        "-level", "4.0",
        "-c:a", "aac",
        "-ar", "48000",
        "-f", "hls",
        "-hls_time", "6",
        "-hls_list_size", "0",
        "-hls_flags", "independent_segments",
        "-hls_segment_filename", f"{out_dir}/seg_%03d.ts",
        str(hls_file)
    ]

    print("🔁 Converting to HLS...")
    subprocess.run(cmd, check=True)
    print("✅ HLS READY:", hls_file)
    return hls_file

# 🔹 MAIN FUNCTION
def process_telegram_video(chat_id: str, message_id: int, filename: str):
    input_file = download_from_telegram(chat_id, message_id, filename)
    hls_file = convert_to_hls(input_file)
    return hls_file

# 🔹 Example usage
if __name__ == "__main__":
    # Replace with your channel ID & message ID
