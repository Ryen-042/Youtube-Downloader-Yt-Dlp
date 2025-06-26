"""This module contains various download functions defining pipelines tailored for different download modes."""

import os, yt_dlp, concurrent.futures
from datetime import datetime

from common import console
import downloadHelper as dh
import streamsHelper as sh


def downloadSingleVideo(video_link: str, write_desc=False, best_audio=False) -> str:
    """
    Description:
        Downloads a single youtube video or audio file.
    ---
    Parameters:
        `video_link -> str`: The link of the youtube video to download.
        
        `write_desc -> bool`: A flag that indicates whether to write the video description into a text file or not. Defaults to `False`.
        
        `best_audio -> bool`: A flag that indicates whether to download only the audio stream with the highest quality without prompting the user for selection. Defaults to `False`.
    
    ---
    Returns:
        `str` => The name of the download folder.
    """
    
    folderName = datetime.now().strftime("%Y-%m-%d")
    downloadLocation = os.path.join(os.path.dirname(__file__), "downloads", folderName)
    os.makedirs(downloadLocation, exist_ok=True)
    
    conn = dh.initDatabase()
    c = conn.cursor()
    
    video_id = dh.idExtractor(video_link)
    if not video_id:
        return folderName # Invalid video link
    
    result = c.execute("SELECT * FROM History WHERE video_id=?", (video_id,)).fetchone()
    
    if result:
        downloaded_file_name = result[1]
        downloaded_file_directory = result[2]
        download_date = result[3]
        
        if dh.isFilePresent(downloaded_file_directory, downloaded_file_name, download_date):
            conn.close()
            return folderName # File already downloaded
    
    yt_extra_opts = {
        "noprogress": True,
        "progress_hooks": [dh.ProgressBar.progressBarHook]
    }
    dh.ProgressBar.enable_progress_bar = True
    
    if best_audio:
        yt_extra_opts |= {
            "format": "bestaudio",
            "quiet": True,
            "consoletitle": True,
            "noplaylist": True
        }
        
        with yt_dlp.YoutubeDL(yt_extra_opts) as ydl:
            # Extract information before downloading
            meta = ydl.extract_info(video_link, download=False)
            download_dict = {"yt_opts": yt_extra_opts, "meta": meta, "fileExtension": "m4a", "size": meta.get('filesize', None) or meta.get("filesize_approx")}  # type:ignore
    
    else:
        download_dict = sh.parseAndSelectStreams(0, video_link, video_id, yt_extra_opts)
    
    if not download_dict:
        conn.close()
        return folderName # User canceled the download process
    
    # https://github.com/yt-dlp/yt-dlp/issues/630#issuecomment-893659460
    download_dict["yt_opts"] |= {"outtmpl": os.path.join(downloadLocation, "%(title)s.%(ext)s")} # type: ignore
    
    query = dh.downloadFromYoutube(download_dict["yt_opts"], download_dict["meta"], download_dict["fileExtension"], downloadLocation, result is not None, write_desc) # type: ignore
    
    if len(query) == 2:
        c.execute(*query)
        conn.commit()
    
    conn.close()
    
    dh.showResults(download_dict["size"], download_dict["meta"]["duration"]) # type:ignore
    
    return folderName


def downloadYoutubePlaylist(playlist_link: str, start_from=0, end_with=0, write_desc=False, best_audio=False, show_playlist_table=False) -> str:
    """
    Description:
        Downloads one or more videos from a youtube playlist.
    ---
    Parameters:
        `playlistLink -> str`: The link of the youtube playlist to download.
        
        `start_from -> int`: The playlist entry number to start downloading from.
        
        `end_with -> int`: The last playlist entry to download.
        
        `write_desc -> bool`: A flag that indicates whether to write the video description for each entry into a text file. Defaults to `False`.
        
        `best_audio -> bool`: A flag that indicates whether to download only the audio stream with the highest quality without prompting the user for selection. Defaults to `False`.
        
        `show_playlist_table -> bool`: A flag that indicates whether to print the playlist videos table or not. Defaults to `False`.
    
    ---
    Returns:
        `str` => The name of the download folder.
    """
    
    yt_opts = {
        "quiet": True, 'noprogress': True,
        "consoletitle": True, "extract_flat": True,
    }
    
    with yt_dlp.YoutubeDL(yt_opts) as ydl:
        with console.status("[normal1]Parsing the playlist info...[/]"):
            try:
                playlistMeta = ydl.extract_info(playlist_link, download=False)
            except yt_dlp.utils.DownloadError:
                playlistMeta = None
    
    if playlistMeta is None:
        raise ConnectionAbortedError("No playlist found at the given link. Please check your internet connection and the playlist link.")
    
    folderName = yt_dlp.utils.sanitize_filename(playlistMeta["title"])
    downloadLocation = os.path.join(os.path.dirname(__file__), "downloads", folderName)
    os.makedirs(downloadLocation, exist_ok=True)
    
    playlistEntries = [{"id": entry["id"], "title": entry["title"], "duration": entry["duration"], "url": entry["url"]} for entry in playlistMeta["entries"]]
    
    conn = dh.initDatabase()
    c = conn.cursor()
    
    results = []
    for entry in playlistEntries:
        c.execute("SELECT * FROM History WHERE video_id = ?", (entry["id"],))
        results.append(c.fetchone())
        entry["downloaded"] = results[-1] is not None

    if show_playlist_table:
        console.print("[normal1]Availabe video in the playlist:[/]\n")
        sh.printPlaylistTable(playlistEntries)

    console.print(fr"[normal1]Playlist: [normal2]{playlistMeta['title']}[/] \[[normal2]{len(playlistEntries)}[/] Videos][/]")
    console.print(f"[normal1]{'='* (10 + len(playlistMeta['title']))}[/]\n")
    
    firstEntry, lastEntry = sh.getPlaylistStartAndEnd(len(playlistEntries), start_from, end_with)
    
    downloadThreads = []
    totalSize     = 0.0
    totalDuration = 0.0
    
    if best_audio:
        dh.ProgressBar.enable_progress_bar = True
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for i, entry in enumerate(playlistEntries[firstEntry-1:lastEntry], firstEntry):
            video_link = entry["url"]
            video_id = entry['id']
            downloaded_before = entry["downloaded"]
            
            if downloaded_before:
                full_name = results[i-1][1]
                directory = results[i-1][2]
                download_date = results[i-1][3]
                
                if dh.isFilePresent(directory, full_name, download_date):
                    continue
            
            yt_extra_opts = {
                "noprogress": True,
                "progress_hooks": [dh.ProgressBar.progressBarHook],
                "postprocessor_args": [
                    "-metadata", f"comment=https://www.youtube.com/watch?v={video_id}&list={playlist_link.split('list=')[-1]}"
                ]
            }
            
            if best_audio:
                yt_extra_opts |= {
                    "format": "bestaudio",
                    "quiet": True,
                    "consoletitle": True,
                    "noplaylist": True
                }
                
                with yt_dlp.YoutubeDL(yt_extra_opts) as ydl:
                    # Extract information before downloading
                    meta = ydl.extract_info(video_link, download=False)
                    download_dict = {"yt_opts": yt_extra_opts, "meta": meta, "fileExtension": "m4a", "size": meta.get('filesize', None) or meta.get("filesize_approx")}  # type:ignore
            else:
                download_dict = sh.parseAndSelectStreams(i, video_link, video_id, yt_extra_opts)
            
            if not download_dict:
                continue
            
            download_dict["yt_opts"] |= {"outtmpl": os.path.join(downloadLocation, f"({i}). %(title)s.%(ext)s")} # type: ignore
            
            totalDuration += download_dict["meta"]["duration"] # type: ignore
            totalSize     += download_dict["size"] # type: ignore
            
            thread = executor.submit(dh.downloadFromYoutube, download_dict["yt_opts"], download_dict["meta"], download_dict["fileExtension"], downloadLocation, downloaded_before, write_desc) # type: ignore
            downloadThreads.append(thread)
        
        dh.ProgressBar.enable_progress_bar = True
    
    failedDownloads = []
    for future in downloadThreads:
        query = future.result()
        if len(query) == 2:
            c.execute(*query)
            conn.commit()
        
        else:
            failedDownloads.append(query)
    
    conn.close()
    
    dh.showResults(totalSize, totalDuration)
    
    if failedDownloads:
            console.print("[warning1]The following downloads failed:[/]")
            for download in failedDownloads:
                console.print(f"[warning2]{download[1]}[/]")
    
    return folderName


def downloadMultipleYoutubeVideos(filename="video-links.txt", write_desc=False, best_audio=False) -> str:
    """
    Description:
        Download youtube videos with the links from the specified file.
    ---
    Parameters:
        `file_name -> str`: The name of the file containing the youtube video links.
        
        `write_desc -> bool`: A flag that indicates whether to write the video description for each entry into a text file. Defaults to `False`.
        
        `best_audio -> bool`: A flag that indicates whether to download only the audio stream with the highest quality without prompting the user for selection. Defaults to `False`.
    
    ---
    Returns:
        `str` => The name of the download folder.
    """
    
    if not os.path.exists(filename) or not os.path.getsize(filename):
        console.print(f"[warning1]The file [warning2]{filename}[/] either [warning2]doesn't exist[/] or is [warning2]empty[/].[/]")
        
        return ""
    
    downloadThreads = []
    totalSize     = 0.0
    totalDuration = 0.0
    
    folderName = datetime.now().strftime("%Y-%m-%d")
    downloadLocation = os.path.join(os.path.dirname(__file__), "downloads", folderName)
    os.makedirs(downloadLocation, exist_ok=True)
    
    with open(filename, "r") as file:
        video_links = [line.strip() for line in file.readlines()]
    
    conn = dh.initDatabase()
    c = conn.cursor()
    
    if best_audio:
        dh.ProgressBar.enable_progress_bar = True
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for i, video_link in enumerate(video_links, 1):
            video_id = dh.idExtractor(video_link)
            result = c.execute("SELECT * FROM History WHERE video_id=?", (video_id,)).fetchone()
            
            if result:
                downloaded_file_name = result[1]
                downloaded_file_directory = result[2]
                download_date = result[3]
                
                if dh.isFilePresent(downloaded_file_directory, downloaded_file_name, download_date):
                    continue
            
            yt_extra_opts = {
                "noprogress": True,
                "progress_hooks": [dh.ProgressBar.progressBarHook]
            }
            
            if best_audio:
                yt_extra_opts |= {
                    "format": "bestaudio",
                    "quiet": True,
                    "consoletitle": True,
                    "noplaylist": True
                }
                
                with yt_dlp.YoutubeDL(yt_extra_opts) as ydl:
                    # Extract information before downloading
                    meta = ydl.extract_info(video_link, download=False)
                    download_dict = {"yt_opts": yt_extra_opts, "meta": meta, "fileExtension": "m4a", "size": meta.get('filesize', None) or meta.get("filesize_approx")}  # type:ignore
            else:
                download_dict = sh.parseAndSelectStreams(i, video_link, video_id, yt_extra_opts)
            
            if not download_dict:
                continue
            
            download_dict["yt_opts"] |= {"outtmpl": os.path.join(downloadLocation, "%(title)s.%(ext)s")} # type: ignore
            
            totalDuration += download_dict["meta"]["duration"] # type:ignore
            totalSize     += download_dict["size"] # type:ignore
            
            thread = executor.submit(dh.downloadFromYoutube, download_dict["yt_opts"], download_dict["meta"], download_dict["fileExtension"], downloadLocation, result is not None, write_desc) # type:ignore
            downloadThreads.append(thread)
        
        dh.ProgressBar.enable_progress_bar = True
    
    failedDownloads = []
    for i, future in enumerate(downloadThreads):
        query = future.result()
        if len(query) == 2:
            c.execute(*query)
            conn.commit()
        else:
            failedDownloads.append((query, i))
    
    conn.close()
    
    dh.showResults(totalSize, totalDuration)
    
    if failedDownloads:
        console.print("[warning1]The following downloads failed:[/]")
        for download in failedDownloads:
            console.print(f"[{download[1]}] [warning2]{download[0][2]}[/]")
    
    # Clearing the file's content.
    with open(filename, 'w') as file:
        pass
    
    return folderName
