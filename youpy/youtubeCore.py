"""This module contains various download functions defining pipelines tailored for different download modes."""

import os, yt_dlp, concurrent.futures
from datetime import datetime
from glob import glob

from common import console
import downloadHelper as dh
import streamsHelper as sh
import tui


def downloadSingleVideo(vidLink: str, subDir="", write_desc=False) -> int:
    """
    Description:
        Downloads a single youtube video or audio file.
    ---
    Parameters:
        `vidLink -> str`: The link of the youtube video to download.
        
        `subDir -> str`: An optional parameter to specify a sub-directory to download the videos to.
        
        `write_desc -> bool`: A flag that indicates whether to write the [normal2]video description[/] to a text file or not. Defaults to `False`.
    
    ---
    Returns:
        `int` => The exit code of the download process. One of the following:
        
        Value | Meaning
        ------|--------
        `-4`  | The video is already downloaded.
        `-3`  | The video has been downloaded before but the file is missing and the user refused to download the video again when prompted.
        `-2`  | User canceled the download process by not selecting any stream formats.
        `-1`  | Something went wrong while downloading.
        `0`   | The download process completed successfully.
    """
    
    if subDir:
        downloadLocation = os.path.join(os.path.dirname(__file__), "downloads", subDir)
    else:
        downloadLocation = os.path.join(os.path.dirname(__file__), "downloads")
    
    os.makedirs(downloadLocation, exist_ok=True)
    
    yt_opts = {
        "quiet": True, "progress": True, "consoletitle": True, "noplaylist": True,
    }
    
    with yt_dlp.YoutubeDL(yt_opts) as ydl:
        with console.status("[normal1]Fetching available streams...[/]"):
            try:
                meta = ydl.extract_info(vidLink, download=False)
            
            except yt_dlp.utils.DownloadError:
                meta = None
        
        if meta is None or "formats" not in meta:
            raise ConnectionAbortedError("No video found at the given link. Please check your internet connection and the video link.")
        
        conn = dh.initDatabase()
        c = conn.cursor()
        
        c.execute("SELECT * FROM History WHERE video_id = ?", (meta["id"],))
        
        downloadedBefore = False
        result = c.fetchone()
        
        if result:
            if glob(f"{os.path.join(result[2], os.path.splitext(result[1])[0])}*"):
                console.print(f"[normal1]The \"[normal2]{meta['title']}[/]\" video has already been downloaded on [normal2]{result[3]}[/].[/]")
                console.print(f"[normal1]File location: '[normal2]{os.path.join(result[2], result[1])}[/]'[/]""")
                
                conn.close()
                
                return -4 # File is already downloaded.
            
            console.print(f"[normal1]The \"[normal2]{result[1]}[/]\" video has been downloaded before on [normal2]{result[3]}[/] but the file is missing.[/]")
            console.print(f"[normal1]Last known location is: '[normal2]{os.path.join(result[2], result[1])}[/]'[/]\n")
            
            if not tui.yesNoQuestion("Do you want to download it again?", 0, [1, 0], ["Yes", "No"], [1, 2]):
                conn.close()
                
                return -3 # File is missing and user doesn't want to download it again.
            
            downloadedBefore = True
        
        conn.close()
        
        console.print("\n[normal1]Available [normal2]streams[/] are:[/]")
        console.print(f"[normal1]{'='*22}[/]")
        
        groupedStreams = sh.groupYoutubeStreams(meta["formats"])
        categoriesLengths = sh.printStreamsTable(groupedStreams)
        
        console.print(f"[normal1]Video Title : [normal2]{meta['title']}[/][/]")
        console.print(f"[normal1]Duration    : [normal2]{meta['duration_string']}[/] min[/]", end="  |  ")
        console.print(f"[normal1]Release Date: [normal2]{datetime.strptime(meta['upload_date'], '%Y%m%d').strftime('%d/%m/%Y')}[/][/]\n")
        
        selectedStreams = sh.selectStreams(categoriesLengths, groupedStreams)
        if not selectedStreams:
            conn.close()
            
            return -2 # User canceled the download process
        
        selectedFormats, streamsSize = sh.extractFormatIdsFromSelectedStreams(selectedStreams)
        streamsSize /= (1024 * 1024)
        
        console.print(f"[normal1]Total file size: [normal2]{format(streamsSize / 1024, '.2f')+'[/] GB' if streamsSize >= 1024 else format(streamsSize, '.2f')+'[/] MB'}[/]\n")
        
        # https://github.com/yt-dlp/yt-dlp/issues/630#issuecomment-893659460
        yt_opts |= {
            "format": selectedFormats,
            "outtmpl": os.path.join(downloadLocation, "%(title)s.%(ext)s"),
        }
        
        fileExtension = "mp4" if len(selectedStreams) == 2 else selectedStreams[0]["ext"]
        
        return dh.downloadFromYoutube(yt_opts, meta, fileExtension, downloadLocation, downloadedBefore, write_desc=write_desc) # type: ignore


def downloadYoutubePlaylist(playlist_link: str, start_from=0, end_with=0, subDir="", write_desc=True) -> tuple[int, str]:
    """
    Description:
        Downloads one or more videos from a youtube playlist.
    ---
    Parameters:
        `playlistLink -> str`: The link of the youtube playlist to download.
        
        `start_from -> int`: The playlist entry number to start downloading from.
        
        `end_with -> int`: The last playlist entry to download.
        
        `subDir -> str`: An optional parameter to specify a sub-directory to download the videos to.
        
        `write_desc -> bool`: A flag that indicates whether to write the [normal2]video description[/] to a text file for the selected entries. Defaults to `True`.
    
    ---
    Returns:
        `tuple[int, str]` => Always returns the status code `0` (success) and the name of the download folder.
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
    
    folderName = subDir or playlistMeta["title"]
    
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
    
    console.print("[normal1]Availabe video in the playlist:[/]\n")
    sh.printPlaylistTable(playlistEntries)
    
    console.print(fr"[normal1]Playlist: [normal2]{playlistMeta['title']}[/] \[[normal2]{len(playlistMeta['entries'])}[/] Videos][/]")
    console.print(f"[normal1]{'='* (10 + len(playlistMeta['title']))}[/]")
    
    startEnd = sh.getPlaylistStartAndEnd(len(playlistMeta), start_from, end_with)
    
    downloadThreads = []
    totalSize     = 0.0
    totalDuration = 0.0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for i, entry in enumerate(playlistEntries[startEnd[0]-1:startEnd[1]], startEnd[0]):
            video_link = entry["url"]
            video_id = entry['id']
            downloaded_before = entry["downloaded"]
            
            if downloaded_before:
                full_name = results[i-1][1]
                directory = results[i-1][2]
                download_date = results[i-1][3]
                
                if dh.isFilePresent(directory, full_name, download_date):
                    continue
            
            download_dict = sh.parseAndSelectStreams(i, video_link, video_id)
            
            if not download_dict:
                continue
            
            download_dict["yt_opts"] |= {"outtmpl": os.path.join(downloadLocation, f"({i}). %(title)s.%(ext)s")}
            
            totalDuration += download_dict["meta"]["duration"]
            totalSize     += download_dict["size"]
            
            thread = executor.submit(dh.downloadFromYoutube, download_dict["yt_opts"], download_dict["meta"], download_dict["fileExtension"], downloadLocation, downloaded_before, write_desc, True)
            downloadThreads.append(thread)
        
        dh.ProgressBar.enable_progress_bar = True
    
    for future in downloadThreads:
        future.result()
    
    conn.commit()
    conn.close()
    
    dh.showResults(totalSize, totalDuration)
    
    return 0, folderName

def downloadMultipleYoutubeVideos(filename="video-links.txt", write_desc=False) -> tuple[int, str]:
    """
    Description:
        Download youtube videos with the links from the specified file.
    ---
    Parameters:
        `file_name -> str`: The name of the file containing the youtube video links.
        
        `write_desc -> bool`: A flag that indicates whether to write the [normal2]video description[/] to a text file for the specified entries. Defaults to `False`.
    
    ---
    Returns:
        `tuple[bool, str]` => Always returns `False` and the name of the download folder.
    """
    
    if not os.path.exists(filename) and not os.path.getsize(filename):
        console.print(f"[warning1]The file [warning2]{filename}[/] either [warning2]doesn't exist[/] or is [warning2]empty[/].[/]")
        
        return False, ""
    
    conn = dh.initDatabase()
    c = conn.cursor()
    
    downloadThreads = []
    totalSize     = 0.0
    totalDuration = 0.0
    
    folderName = datetime.now().strftime("%d-%m-%Y")
    downloadLocation = os.path.join(os.path.dirname(__file__), "downloads", folderName)
    os.makedirs(downloadLocation, exist_ok=True)
    
    with open(filename, "r") as file:
        video_links = [line.strip() for line in file.readlines()]
    
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
            
            download_dict = sh.parseAndSelectStreams(i, video_link, video_id)
            
            if not download_dict:
                continue
            
            download_dict["yt_opts"] |= {"outtmpl": os.path.join(downloadLocation, "%(title)s.%(ext)s")}
            
            totalDuration += download_dict["meta"]["duration"]
            totalSize     += download_dict["size"]
            
            thread = executor.submit(dh.downloadFromYoutube, download_dict["yt_opts"], download_dict["meta"], download_dict["fileExtension"], downloadLocation, result is not None, write_desc, True)
            downloadThreads.append(thread)
        
        dh.ProgressBar.enable_progress_bar = True
    
    for future in downloadThreads:
        future.result()
    
    conn.commit()
    conn.close()
    
    dh.showResults(totalSize, totalDuration)
    
    # Clearing the file's content.
    with open(filename, 'w') as file:
        pass
    
    return 0, folderName


