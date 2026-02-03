"""
This module provides functions for selecting, formatting, and downloading streams.
"""

import os, threading, yt_dlp, sqlite3, re, time, playsound
from collections import OrderedDict
from datetime import datetime
from glob import glob

from common import console, SFX_LOC
import tui

class ProgressBar:
    """
    Description:
        A class that provides a progress bar that can be used to display the progress of multiple downloads.
    ---
    Parameters:
        `downloads_dict -> OrderedDict[int, dict]`: A dictionary containing the information of the files being downloaded.
    """
    
    enable_progress_bar = False
    downloads_dict: OrderedDict[int, dict] = OrderedDict()
    throttle_lock = threading.Lock()
    throttle_timespan = 0.2
    last_execution_time = 0
    
    @classmethod
    def progressBarHook(cls, progress: dict) -> None:
        """
        Description:
            A hook to be used with `yt_dlp` to update the downloads_dict with the progress information.
        ---
        Details:
            Yt_dlp parses and returns a dictionary containing the following information:
            
            Parameter            | Type  | Description
            ---------------------|-------|------------
            status               | str   | Possible values: `'downloading'`, `'finished'`, `'error'`.
            info_dict            | dict  | Contains extracted information about the downloading file.
            filename             | str   | The final filename.
            downloaded_bytes     | int   | The number of bytes downloaded so far.
            total_bytes          | int   | The total number of bytes to download.
            total_bytes_estimate | int   | The estimated total number of bytes to download.
            tmpfilename          | str   | The filename we are currently writing to.
            elapsed              | float | The number of seconds passed since the download started.
            eta                  | float | The estimated time in seconds until the download is finished.
            speed                | float | The download speed in bytes/second.
        ---
        Parameters:
            `progress` -> dict: A dictionary containing the progress information.
        """
        
        id = progress.get("info_dict", dict()).get("id", "-1")
        
        if progress['status'] == 'finished':
            if id in cls.downloads_dict:
                cls.downloads_dict[id].update({"status": "finished"})
        
        elif progress['status'] == 'downloading':
            downloaded_bytes = progress.get('downloaded_bytes', -1) or -1
            total_bytes = progress.get('total_bytes', -1) or -1 # Avoid division by zero
            
            if total_bytes > 1:
                remaining_bytes = total_bytes - downloaded_bytes
            else:
                total_bytes = -1
                remaining_bytes = -1
            
            download_speed = progress.get('speed', -1) or -1
            eta_seconds = progress.get('eta', -1) or -1
            
            if id not in cls.downloads_dict:
                cls.downloads_dict[id] = dict()
            
            cls.downloads_dict[id].update({
                "status": "downloading",
                "total_bytes": total_bytes,
                "remaining_bytes": remaining_bytes,
                "download_speed": download_speed,
                "eta_seconds": eta_seconds
            })
        
        if not cls.enable_progress_bar:
            return
        
        with cls.throttle_lock:
            current_time = time.time()
            if current_time - cls.last_execution_time >= cls.throttle_timespan:
                cls.displayProgressBars()
                
                cls.last_execution_time = current_time
    
    
    @staticmethod
    def _formatEta(seconds):
        """Format ETA in seconds into a human-readable string."""
        if seconds is None or seconds < 0:
            return "???"
        
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
    
    
    @staticmethod
    def _formatBytes(bytes: float) -> str:
        """Format bytes into a human-readable string."""
        
        if bytes < 1:
            return "???"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unit}"
            
            bytes /= 1024.0
        
        return f"{bytes:.2f} TB"
    
    
    @classmethod
    def getProgressBarText(cls, filesize: float, bytes_remaining: float, download_speed: float, eta_seconds: float) -> str:
        """Returns a styled progress bar text."""
        
        # Styling
        char_empty   = "░" # ▄ ░ ▒ ▓
        char_fill    = "█"
        
        # Sizing
        scale        = 0.35
        columns = os.get_terminal_size().columns
        max_width    = int(columns * scale)
        fill_width   = int(round(max_width * (filesize - bytes_remaining) / filesize))
        remaining_width = max_width - fill_width
        
        # Data
        total_filesize  = cls._formatBytes(filesize)
        downloaded_size = cls._formatBytes(filesize - bytes_remaining)
        percent      = ((filesize - bytes_remaining) / filesize) * 100
        
        # Text
        progress_text = fr"\[[normal2]{downloaded_size:>10}[/] of [normal2]{total_filesize:>10}[/]] at [normal2]{cls._formatBytes(download_speed):>10}[/]/s"
        progress_bar = f"[exists]{char_fill * fill_width}[/][normal2]{char_empty * remaining_width}[/]"
        eta = f"ETA: [normal2]{cls._formatEta(eta_seconds):8}[/]"
        final_text = f"[normal1]{progress_text} | {progress_bar} | {eta} ([normal2]{format(percent, '.2f')}%[/])[/]\033[K"
        
        return final_text
    
    
    @classmethod
    def _printProgressBar(cls, downloads_dict: OrderedDict[int, dict]):
        """Prints the progress bars for all the downloads."""
        
        progress_bars_texts = []
        for id, download_info in downloads_dict.items():
            progress_bars_texts.append(
                cls.getProgressBarText(
                    filesize=download_info.get("total_bytes", -1) or -1,
                    bytes_remaining=download_info.get("remaining_bytes", -1) or -1,
                    download_speed=download_info.get("download_speed", -1) or -1,
                    eta_seconds=download_info.get("eta_seconds", -1) or -1
            ))
        
        console.print("\n".join(progress_bars_texts))
    
    
    @classmethod
    def _moveCursorUp(cls, downloads_dict: OrderedDict[int, dict]):
        """Moves the cursor up and clears the area of the finished progress bars."""
        
        fishied_ids = {id for id, download_info in downloads_dict.items() if download_info.get("status", "downloading") == "finished"}
        
        # To prevent flickering, we don't clear the area of the working progress bars.
        finished_progress_bars_clearing_text = f"\033[F\033[K" * len(fishied_ids)
        working_progress_bars_clearing_text = f"\033[F" * (len(downloads_dict) - len(fishied_ids))
        print(finished_progress_bars_clearing_text + working_progress_bars_clearing_text, end="\r")
        
        # Remove the finished downloads from the downloads_dict and finshed_ids.
        for id in fishied_ids:
            del cls.downloads_dict[id]
    
    
    @classmethod
    def displayProgressBars(cls) -> None:
        """Executes the progress bar printing and cursor moving functions."""
        
        downloads_dict = dict()
        
        # Because cls.dowloads_dict is not guranteed to be constant during the execution of this function, we need to make a copy.
        downloads_dict = cls.downloads_dict.copy()
        
        # Print the progress bars and move up the cursor and clear the area of the finished progress bars.
        cls._printProgressBar(downloads_dict)
        cls._moveCursorUp(downloads_dict)


def downloadFromYoutube(yt_opts: dict[str, object], meta: dict[str, object], file_extension: str, download_location: str,
                         downloaded_before=False, write_desc=False) -> tuple[str, dict[str, str]] | tuple[str, str, str]:
    """
    Description:
        Downloads a YouTube video using the provided options, updates download history database, stores the video description into a text file.
    ---
    Parameters:
        `yt_opts -> dict[str, object]`: A dict containing options for configuring the behavior of the `yt-dlp` downloader.
        
        `meta -> dict[str, object]`: A dict containing YouTube video metadata.
        
        `file_extension -> str`: The expected extension of the file being downloaded.
        
        `download_location -> str`: Specifies where the downloaded video will be saved
        
        `downloaded_before -> bool`: A flag that indicates whether the video has been downloaded before.
            If `True`, the function will update the download history instead of adding a new record.
        
        `write_desc -> bool`: A flag that indicates whether to write the video description into a text file or not.
    
    ---
    Returns: `tuple[str, dict[str, str]] | tuple[str, str, str]`:  
        - Success: a tuple containing the query and parameters to be used for updating the database.  
        - Failure: a tuple containing the video URL, video ID, and video title.
    """
    
    yt_opts |= {
        "checkformats": "selected",
        "addmetadata": True,
        "writethumbnail": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "embedthumbnail": True,
        "embedsubtitles": True,
        "subtitleslangs": ["en"], # "ar", 
        "concurrent_fragment_downloads": "5",
        "compat_opts": {"no-keep-subs"},
        "merge_output_format": "mkv",
    }
    
    # if "postprocessor_args" not in yt_opts:
        # yt_opts["postprocessor_args"] = []
    
    # # Add FFmpeg postprocessor args to prevent audio re-encoding
    # # -c copy means "copy all codecs" (both audio and video streams)
    # yt_opts["postprocessor_args"].extend([
        # "-c", "copy",  # Copy all streams without re-encoding
    # ])
    
    if not "postprocessors" in yt_opts:
        yt_opts["postprocessors"] = list()
    
    if yt_opts["format"] == "bestaudio":
        yt_opts["postprocessors"].append({"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}) # type: ignore
    
    yt_opts["postprocessors"].extend([ # type: ignore
        # The order of the postprocessors is important as some of them may affect the output of the previous ones.
        {
            "key": "FFmpegMetadata",
            "add_chapters": True,
            "add_metadata": True,
            "add_infojson": "if_exists",
        },
        {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False},
        {"key": "EmbedThumbnail", "already_have_thumbnail": False},
    ])
    
    try:
        with yt_dlp.YoutubeDL(yt_opts) as ydl:
            if statusCode := ydl.download(meta["webpage_url"]):
                console.print(f"[warning1]Warning! Download operation exitted with status code {statusCode}.[/]")
                ProgressBar.downloads_dict.pop(meta["display_id"], None)  # type:ignore
                
                return (meta["webpage_url"], meta["display_id"], meta["fulltitle"])  # type:ignore
    
    except:
        console.print(f"[warning1]An error occurred while downloading the video with the ID: {meta['id']}.[/]")
        ProgressBar.downloads_dict.pop(meta["display_id"], None)  # type:ignore
        
        return (meta["webpage_url"], meta["display_id"], meta["fulltitle"])  # type:ignore
    
    filename = os.path.splitext(os.path.basename(ydl.prepare_filename(meta)))[0]
    
    if downloaded_before:
        query = "UPDATE History SET filename = :filename, location = :location, date = :date WHERE video_id = :video_id"
    
    else:
        query = "INSERT INTO History VALUES (:video_id, :filename, :location, :date)"
    
    params = {
        "video_id": meta["id"],
        "filename": f"{filename}.{file_extension}",
        "location": download_location,
        "date": datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    }
    
    descFullPath = os.path.join(download_location, f"{filename}.txt")
    if write_desc and (not os.path.exists(descFullPath) or os.path.getsize(descFullPath) == 0):
        with open(descFullPath, "w") as f:
            f.write(f"Title: {meta['title'].encode('utf-8')}\n\nLink: {meta['webpage_url'].encode('utf-8')}\n\nDescription:\n\n{meta['description'].encode('utf-8')}") # type: ignore
    
    return (query, params)


def removeDuplicateLinks(lst: list[str]) -> OrderedDict[str, None]:
    """Removes duplicates from a list while preserving its order."""
    
    return OrderedDict.fromkeys(lst)


def idExtractor(url):
    """
    Description:
        Extracts the video ID from a YouTube URL.
    ---
    Args:
        `url -> str`: A YouTube video URL.
    ---
    Parameters:
        str or None: The video ID if found, None otherwise.
    ---
    Returns:
        `str | None`: The video ID if found, None otherwise.
    """
    url = url.strip()

    # Define the URL pattern for YouTube links
    url_pattern = re.compile(r'https?://(?:www\.)?(?:m\.)?(?:youtu(?:be\.com/(?:watch\?v=|embed/|shorts/)|\.be/)|youtube\.com/v/)([\w\-_]*)')

    # Find the match in the text
    match = url_pattern.search(url)

    if match:
        video_id = match.group(1)
        return video_id
    else:
        return None


def writeLinksToFile(video_links: list[str], filename="video-links.txt") -> None:
    """
    Description:
        Get video links from user and add them to a file.
    ---
    Parameters:
        `path` (`str`)
            The path to the file containing where the video links will be stored.
    ---
    Returns: `None`.
    """
    
    pathToLinksFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    
    with open(pathToLinksFile, "w", encoding='utf-8') as linksFile:
        linksFile.write("\n".join(video_links))


def initDatabase():
    """Creates the database if it doesn't exist and returns a connection to it."""

    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "download_history.db"))
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS History (
        video_id TEXT PRIMARY KEY,
        filename text,
        location text,
        date text)""")

    return conn


def isFilePresent(directory, full_name, download_date) -> bool:
    """Checks if the specified file exists in the specified directory and prompts the user to download it again if it doesn't."""

    if glob(f"{os.path.join(directory, os.path.splitext(full_name)[0])}*"):
        console.print(f"[normal1]The \"[normal2]{full_name}[/]\" file has already been downloaded on [normal2]{download_date}[/].[/]")
        console.print(f"[normal1]File location: '[normal2]{os.path.join(directory, full_name)}[/]'[/]\n""")

        return True # File is found.

    console.print(f"[normal1]The \"[normal2]{full_name}[/]\" file has been downloaded before on [normal2]{download_date}[/] but the file is missing.[/]")
    console.print(f"[normal1]Last known location is: '[normal2]{os.path.join(directory, full_name)}[/]'[/]\n")

    # File is missing and user either wants to download it again or not.
    return not tui.yesNoQuestion("Do you want to download it again?", 0, [True, False], ["Yes", "No"], [1, 2])


def showResults(totalSize, totalDuration):
    mins, secs = divmod(totalDuration, 60)
    hours = 0
    if mins > 59:
        hours, mins = divmod(mins, 60)
    hours, mins, secs = int(hours), int(mins), int(secs)
    
    totalSize /= (1024 * 1024)
    
    console.print("[normal1]Download finished.[/]\033[K")
    console.print(f"[normal1]Total media size: [normal2]{format(totalSize / 1024, '.2f')+'[/] GB' if totalSize >= 1024 else format(totalSize, '.2f')+'[/] MB'}[/]")
    console.print(f"[normal1]Total duration  : {'[normal2]'+format(hours, '02')+'[/]:' if hours else ''}[normal2]{mins:02}[/]:[normal2]{secs:02}[/][/]\n")
    
    playsound.playsound(SFX_LOC)
