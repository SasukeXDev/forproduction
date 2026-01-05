from flask import Flask, request, jsonify
import subprocess
import os
import hashlib

app = Flask(__name__)

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/channel")
def index():
    return render_template("index.html")

@app.route('/watch')
def video():
    return render_template("video.html")

@app.route('/dl')
def dl():
    return render_template("dl.html")

# Directory to store HLS segments
HLS_OUTPUT_DIR = "static/streams"
if not os.path.exists(HLS_OUTPUT_DIR):
    os.makedirs(HLS_OUTPUT_DIR)

@app.route('/convert', methods=['POST'])
def convert():
    video_url = request.json.get('url')
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    # Create a unique ID for this stream based on the URL
    stream_id = hashlib.md5(video_url.encode()).hexdigest()
    output_path = os.path.join(HLS_OUTPUT_DIR, stream_id)
    
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        # FFmpeg command to convert remote link to HLS
        # We use -reconnect to handle network drops from remote links
        cmd = [
            'ffmpeg', '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5',
            '-i', video_url,
            '-map', '0:v:0', '-map', '0:a?', '-map', '0:s?',
            '-c:v', 'copy', '-c:a', 'aac', '-c:s', 'webvtt',
            '-f', 'hls', '-hls_time', '6', '-hls_list_size', '0',
            os.path.join(output_path, 'index.m3u8')
        ]
        # Run in background so the user doesn't wait for full conversion
        subprocess.Popen(cmd)

    return jsonify({
        "hls_link": f"/static/streams/{stream_id}/index.m3u8"
    })

if __name__ == '__main__':
# Render provides a PORT environment variable. If not found, use 5000.
    port = int(os.environ.get("PORT", 8080))
    # host='0.0.0.0' allows external access
    app.run(host='0.0.0.0', port=port)
