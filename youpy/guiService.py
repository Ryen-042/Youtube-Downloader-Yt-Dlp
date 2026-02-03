"""
Backend service layer for the Flask GUI.
Wraps existing core logic for web consumption.
"""

import os
import queue
import threading
import sqlite3
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
from datetime import datetime
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

import downloadHelper as dh
import streamsHelper as sh

# Impersonate target for bypassing YouTube restrictions
IMPERSONATE_TARGET = ImpersonateTarget.from_str("chrome-116:windows-10")

# Thread-safe queue for progress updates (SSE consumption)
progress_queue = queue.Queue()

# Track active downloads
active_downloads: dict[str, dict] = {}
downloads_lock = threading.Lock()


def web_progress_hook(progress: dict) -> None:
    """
    Progress hook for yt_dlp that pushes updates to the progress queue.
    Used instead of the terminal-based ProgressBar for web GUI.
    """
    video_id = progress.get("info_dict", {}).get("id", "unknown")
    title = progress.get("info_dict", {}).get("title", "Unknown")
    status = progress.get("status", "unknown")
    
    update = {
        "video_id": video_id,
        "title": title,
        "status": status,
    }
    
    if status == "downloading":
        downloaded = progress.get("downloaded_bytes", 0) or 0
        total = progress.get("total_bytes") or progress.get("total_bytes_estimate") or 0
        speed = progress.get("speed", 0) or 0
        eta = progress.get("eta", 0) or 0
        
        update.update({
            "downloaded_bytes": downloaded,
            "total_bytes": total,
            "speed": speed,
            "eta": eta,
            "percent": round((downloaded / total * 100), 2) if total > 0 else 0
        })
    
    elif status == "finished":
        update["percent"] = 100
    
    elif status == "error":
        update["error"] = progress.get("error", "Unknown error")
    
    with downloads_lock:
        active_downloads[video_id] = update
    
    # Push to queue for SSE
    try:
        progress_queue.put_nowait(update)
    except queue.Full:
        pass  # Drop if queue is full


def format_bytes(bytes_val: float) -> str:
    """Format bytes into human-readable string."""
    if bytes_val < 1:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"


def get_streams(url: str) -> dict:
    """
    Fetch available streams for a YouTube video.
    Returns JSON-serializable stream data.
    """
    video_id = dh.idExtractor(url)
    if not video_id:
        return {"error": "Invalid YouTube URL"}
    
    # Minimal options for fetching info - no impersonation needed here (much faster)
    yt_opts = {
        "quiet": True,
        "consoletitle": True,
        "noplaylist": True,
    }
    
    try:
        with yt_dlp.YoutubeDL(yt_opts) as ydl:
            meta = ydl.extract_info(url, download=False)
    except Exception as e:
        return {"error": str(e)}
    
    if not meta or "formats" not in meta:
        return {"error": "Could not extract video info"}
    
    grouped = sh.groupYoutubeStreams(meta["formats"])
    
    # Convert to JSON-serializable format
    streams_data = {}
    for category, streams in grouped.items():
        streams_data[category] = []
        for stream in streams:
            filesize = stream.get("filesize") or stream.get("filesize_approx") or 0
            streams_data[category].append({
                "format_id": stream.get("format_id"),
                "format_note": stream.get("format_note", ""),
                "ext": stream.get("ext", ""),
                "filesize": filesize,
                "filesize_formatted": format_bytes(filesize),
                "asr": stream.get("asr"),
                "tbr": stream.get("tbr"),
                "fps": stream.get("fps"),
                "vcodec": stream.get("vcodec") if stream.get("vcodec") != "none" else None,
                "acodec": stream.get("acodec") if stream.get("acodec") != "none" else None,
                "resolution": stream.get("resolution", ""),
            })
    
    # Check if already downloaded
    conn = dh.initDatabase()
    c = conn.cursor()
    result = c.fetchone() if c.execute("SELECT * FROM History WHERE video_id=?", (video_id,)) else None
    result = c.fetchone()
    conn.close()
    
    return {
        "video_id": video_id,
        "title": meta.get("title", ""),
        "duration": meta.get("duration_string", ""),
        "upload_date": meta.get("upload_date", ""),
        "thumbnail": meta.get("thumbnail", ""),
        "streams": streams_data,
        "already_downloaded": result is not None,
        "meta": {
            "webpage_url": meta.get("webpage_url"),
            "title": meta.get("title"),
            "duration": meta.get("duration"),
            "description": meta.get("description", ""),
            "id": meta.get("id"),
            "display_id": meta.get("display_id"),
            "fulltitle": meta.get("fulltitle"),
        }
    }


def get_playlist(url: str) -> dict:
    """
    Fetch playlist information.
    Returns JSON-serializable playlist data.
    """
    # Minimal options for fetching info - no impersonation needed here (much faster)
    yt_opts = {
        "quiet": True,
        "noprogress": True,
        "consoletitle": True,
        "extract_flat": True,
        # "impersonate": IMPERSONATE_TARGET, "remote_components": ["ejs:github"], // Slows down extraction
    }
    
    try:
        with yt_dlp.YoutubeDL(yt_opts) as ydl:
            playlist_meta = ydl.extract_info(url, download=False)
    except Exception as e:
        return {"error": str(e)}
    
    if not playlist_meta:
        return {"error": "Could not extract playlist info"}
    
    entries = []
    conn = dh.initDatabase()
    c = conn.cursor()
    
    for entry in playlist_meta.get("entries", []):
        video_id = entry.get("id")
        c.execute("SELECT * FROM History WHERE video_id=?", (video_id,))
        result = c.fetchone()
        
        duration = entry.get("duration", 0) or 0
        mins, secs = divmod(duration, 60)
        
        entries.append({
            "id": video_id,
            "title": entry.get("title", ""),
            "duration": duration,
            "duration_formatted": f"{int(mins):02}:{int(secs):02}",
            "url": entry.get("url", ""),
            "downloaded": result is not None,
        })
    
    conn.close()
    
    return {
        "playlist_id": playlist_meta.get("id"),
        "title": playlist_meta.get("title", ""),
        "count": len(entries),
        "entries": entries,
    }


def start_download(url: str, format_ids: str, audio_only: bool = False, write_desc: bool = False) -> dict:
    """
    Start a download in a background thread.
    Returns immediately with task status.
    """
    video_id = dh.idExtractor(url)
    if not video_id:
        return {"error": "Invalid YouTube URL"}
    
    def download_task():
        folder_name = datetime.now().strftime("%Y-%m-%d")
        download_location = os.path.join(os.path.dirname(__file__), "downloads", folder_name)
        os.makedirs(download_location, exist_ok=True)
        
        conn = dh.initDatabase()
        c = conn.cursor()
        
        result = c.execute("SELECT * FROM History WHERE video_id=?", (video_id,)).fetchone()
        downloaded_before = result is not None
        
        yt_opts = {
            "quiet": True,
            "consoletitle": True,
            "noplaylist": True,
            "noprogress": True,
            "progress_hooks": [web_progress_hook],
            "outtmpl": os.path.join(download_location, "%(title)s.%(ext)s"),
            "js_runtimes": {
                "node": {
                    "executable": r"C:\Program Files\nodejs\node.exe"
                }
            },
            # Impersonation to bypass 403 errors
            # "impersonate": IMPERSONATE_TARGET, "remote_components": ["ejs:github"],
        }
        
        if audio_only:
            yt_opts["format"] = "bestaudio/best"
            file_ext = "m4a"
        else:
            # Use format selector with fallback instead of specific IDs
            # Format IDs can become stale, so use a robust fallback
            if format_ids and format_ids not in ["bestvideo+bestaudio/best", ""]:
                yt_opts["format"] = f"{format_ids}/bestvideo+bestaudio/best"
            else:
                yt_opts["format"] = "bestvideo+bestaudio/best"
            file_ext = "mkv"
        
        try:
            with yt_dlp.YoutubeDL(yt_opts) as ydl:
                meta = ydl.extract_info(url, download=False)
                
            if not meta:
                progress_queue.put({"video_id": video_id, "status": "error", "error": "Failed to extract info"})
                return
            
            query = dh.downloadFromYoutube(yt_opts, meta, file_ext, download_location, downloaded_before, write_desc)
            
            if len(query) == 2:
                c.execute(*query)
                conn.commit()
                progress_queue.put({"video_id": video_id, "status": "completed", "title": meta.get("title", "")})
            else:
                progress_queue.put({"video_id": video_id, "status": "error", "error": "Download failed"})
        
        except Exception as e:
            progress_queue.put({"video_id": video_id, "status": "error", "error": str(e)})
        
        finally:
            conn.close()
    
    thread = threading.Thread(target=download_task, daemon=True)
    thread.start()
    
    return {"status": "started", "video_id": video_id}


def start_playlist_download(playlist_url: str, entries: list[dict], audio_only: bool = False, write_desc: bool = False) -> dict:
    """
    Start downloading selected playlist entries in background.
    entries: list of {id, url, index} dicts
    """
    def playlist_download_task():
        # Extract playlist ID for folder naming
        yt_opts = {
            "quiet": True,
            "noprogress": True,
            "consoletitle": True,
            "extract_flat": True,
            "impersonate": IMPERSONATE_TARGET, "remote_components": ["ejs:github"],
            "js_runtimes": {
                "node": {
                    "executable": r"C:\Program Files\nodejs\node.exe"
                }
            }
        }
        
        try:
            with yt_dlp.YoutubeDL(yt_opts) as ydl:
                playlist_meta = ydl.extract_info(playlist_url, download=False)
            folder_name = yt_dlp.utils.sanitize_filename(playlist_meta["title"])
        except:
            folder_name = datetime.now().strftime("%Y-%m-%d")
        
        download_location = os.path.join(os.path.dirname(__file__), "downloads", folder_name)
        os.makedirs(download_location, exist_ok=True)
        
        conn = dh.initDatabase()
        c = conn.cursor()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            for entry in entries:
                video_id = entry["id"]
                video_url = entry["url"]
                index = entry.get("index", 0)
                
                result = c.execute("SELECT * FROM History WHERE video_id=?", (video_id,)).fetchone()
                downloaded_before = result is not None
                
                yt_opts = {
                    "quiet": True,
                    "consoletitle": True,
                    "noplaylist": True,
                    "noprogress": True,
                    "progress_hooks": [web_progress_hook],
                    "outtmpl": os.path.join(download_location, f"({index}). %(title)s.%(ext)s"),
                    "impersonate": IMPERSONATE_TARGET, "remote_components": ["ejs:github"],
                    "js_runtimes": {
                        "node": {
                            "executable": r"C:\Program Files\nodejs\node.exe"
                        }
                    }
                }
                
                if audio_only:
                    yt_opts["format"] = "bestaudio/best"
                    file_ext = "m4a"
                else:
                    yt_opts["format"] = "bestvideo+bestaudio/best"
                    file_ext = "mkv"
                
                try:
                    with yt_dlp.YoutubeDL(yt_opts) as ydl:
                        meta = ydl.extract_info(video_url, download=False)
                    
                    if meta:
                        executor.submit(
                            dh.downloadFromYoutube,
                            yt_opts, meta, file_ext, download_location, downloaded_before, write_desc
                        )
                except Exception as e:
                    progress_queue.put({"video_id": video_id, "status": "error", "error": str(e)})
        
        conn.close()
        progress_queue.put({"status": "playlist_completed", "message": "Playlist download completed"})
    
    thread = threading.Thread(target=playlist_download_task, daemon=True)
    thread.start()
    
    return {"status": "started", "count": len(entries)}


def get_batch_links() -> dict:
    """Read video-links.txt and return its contents."""
    links_file = os.path.join(os.path.dirname(__file__), "video-links.txt")
    
    if not os.path.exists(links_file):
        return {"links": [], "raw": ""}
    
    with open(links_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    links = [line.strip() for line in content.split("\n") if line.strip()]
    
    return {"links": links, "raw": content}


def save_batch_links(content: str) -> dict:
    """Save content to video-links.txt."""
    links_file = os.path.join(os.path.dirname(__file__), "video-links.txt")
    
    with open(links_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    return {"status": "saved"}


def start_batch_download(links: list[str], audio_only: bool = False, write_desc: bool = False) -> dict:
    """Start downloading multiple videos from a list of links."""
    
    def batch_download_task():
        folder_name = datetime.now().strftime("%Y-%m-%d")
        download_location = os.path.join(os.path.dirname(__file__), "downloads", folder_name)
        os.makedirs(download_location, exist_ok=True)
        
        conn = dh.initDatabase()
        c = conn.cursor()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            for url in links:
                video_id = dh.idExtractor(url)
                if not video_id:
                    continue
                
                result = c.execute("SELECT * FROM History WHERE video_id=?", (video_id,)).fetchone()
                downloaded_before = result is not None
                
                yt_opts = {
                    "quiet": True,
                    "consoletitle": True,
                    "noplaylist": True,
                    "noprogress": True,
                    "progress_hooks": [web_progress_hook],
                    "outtmpl": os.path.join(download_location, "%(title)s.%(ext)s"),
                    "impersonate": IMPERSONATE_TARGET, "remote_components": ["ejs:github"],
                    "js_runtimes": {
                        "node": {
                            "executable": r"C:\Program Files\nodejs\node.exe"
                        }
                    }
                }
                
                if audio_only:
                    yt_opts["format"] = "bestaudio/best"
                    file_ext = "m4a"
                else:
                    yt_opts["format"] = "bestvideo+bestaudio/best"
                    file_ext = "mkv"
                
                try:
                    with yt_dlp.YoutubeDL(yt_opts) as ydl:
                        meta = ydl.extract_info(url, download=False)
                    
                    if meta:
                        executor.submit(
                            dh.downloadFromYoutube,
                            yt_opts, meta, file_ext, download_location, downloaded_before, write_desc
                        )
                except Exception as e:
                    progress_queue.put({"video_id": video_id, "status": "error", "error": str(e)})
        
        conn.close()
        progress_queue.put({"status": "batch_completed", "message": "Batch download completed"})
    
    thread = threading.Thread(target=batch_download_task, daemon=True)
    thread.start()
    
    return {"status": "started", "count": len(links)}


def get_progress_updates():
    """Generator that yields progress updates for SSE."""
    while True:
        try:
            update = progress_queue.get(timeout=30)
            yield update
        except queue.Empty:
            # Send keepalive
            yield {"keepalive": True}
