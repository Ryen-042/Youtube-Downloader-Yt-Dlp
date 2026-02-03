"""
Flask Web GUI for YouPy - YouTube Video Downloader
Run this file to start the web interface: python gui.py
"""

import os
import json
from flask import Flask, render_template, request, jsonify, Response

import guiService as gs

# Create Flask app with correct template/static paths
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)


@app.route("/")
def index():
    """Serve the main HTML page."""
    return render_template("index.html")


@app.route("/api/fetch-streams", methods=["POST"])
def fetch_streams():
    """Fetch available streams for a YouTube video."""
    data = request.get_json()
    url = data.get("url", "")
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    result = gs.get_streams(url)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)


@app.route("/api/fetch-playlist", methods=["POST"])
def fetch_playlist():
    """Fetch playlist information."""
    data = request.get_json()
    url = data.get("url", "")
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    result = gs.get_playlist(url)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)


@app.route("/api/download", methods=["POST"])
def start_download():
    """Start downloading a video."""
    data = request.get_json()
    url = data.get("url", "")
    format_ids = data.get("format_ids", "bestvideo+bestaudio/best")
    audio_only = data.get("audio_only", False)
    write_desc = data.get("write_desc", False)
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    result = gs.start_download(url, format_ids, audio_only, write_desc)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)


@app.route("/api/download-playlist", methods=["POST"])
def download_playlist():
    """Start downloading selected playlist entries."""
    data = request.get_json()
    playlist_url = data.get("playlist_url", "")
    entries = data.get("entries", [])
    audio_only = data.get("audio_only", False)
    write_desc = data.get("write_desc", False)
    
    if not playlist_url or not entries:
        return jsonify({"error": "Missing playlist URL or entries"}), 400
    
    result = gs.start_playlist_download(playlist_url, entries, audio_only, write_desc)
    
    return jsonify(result)


@app.route("/api/batch-links", methods=["GET"])
def get_batch_links():
    """Get contents of video-links.txt."""
    result = gs.get_batch_links()
    return jsonify(result)


@app.route("/api/batch-links", methods=["POST"])
def save_batch_links():
    """Save content to video-links.txt."""
    data = request.get_json()
    content = data.get("content", "")
    
    result = gs.save_batch_links(content)
    return jsonify(result)


@app.route("/api/download-batch", methods=["POST"])
def download_batch():
    """Start batch download from provided links."""
    data = request.get_json()
    links = data.get("links", [])
    audio_only = data.get("audio_only", False)
    write_desc = data.get("write_desc", False)
    
    if not links:
        return jsonify({"error": "No links provided"}), 400
    
    result = gs.start_batch_download(links, audio_only, write_desc)
    return jsonify(result)


@app.route("/api/progress")
def progress_stream():
    """SSE endpoint for real-time progress updates."""
    def generate():
        for update in gs.get_progress_updates():
            data = json.dumps(update)
            yield f"data: {data}\n\n"
    
    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  YouPy Web GUI")
    print("  Open http://localhost:5000 in your browser")
    print("="*50 + "\n")
    
    app.run(debug=True, port=5000, threaded=True)
