"""This module provides functions for interacting with yt-dlp."""

from datetime import datetime
from rich import box
from rich.table import Table
import os, yt_dlp, sqlite3, threading, playsound, subprocess
from common import console, SFX_LOC
import downloadHelper as dh
import tui

def groupYoutubeStreams(streams: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    """
    Description:
        Groups the streams of a youtube video into `streamType/extension` categories. Streams are sorted by `yt-dlp` default behavior.
    ---
    Parameters:
        `streams -> list[dict[str, object]]`: A dictionary containing the metadata of the youtube video.
    ---
    Returns:
        `dict[str, list[dict[str, object]]]` => A dictionary containing the grouped streams in this format `{"stream-type/ext": list[stream]}`.
        
        For example: `{"audio/m4a": [{}], "audio/webm": [{}], "video/mp4": [{}], "audio-video/mp4": [{}]}`
    """
    
    groupedStreams: dict[str, list[dict[str, object]]] = {}
    
    for stream in streams:
        if (stream.get("format_note") in [None, 'Default']) or (stream.get("format_note")[:4].upper() == "DASH") or (stream["ext"] in ["mhtml", "3gp"]) or not (stream.get("filesize") or stream.get("filesize_approx")):
            continue
        
        # Can also be filtered with stream["width"] or stream["height"] as both are None for audio only streams.
        if stream["resolution"] == "audio only":
            if f"audio/{stream['ext']}" in groupedStreams:
                groupedStreams[f"audio/{stream['ext']}"].append(stream)
            
            else:
                groupedStreams[f"audio/{stream['ext']}"] = [stream]
        
        elif stream["vcodec"] != "none" and stream["acodec"] == "none":
            if f"video/{stream['ext']}" not in groupedStreams:
                groupedStreams[f"video/{stream['ext']}"] = [stream]
            
            else:
                groupedStreams[f"video/{stream['ext']}"].append(stream)
        
        elif f"audio-video/{stream['ext']}" not in groupedStreams:
            groupedStreams[f"audio-video/{stream['ext']}"] = [stream]
        
        else:
            groupedStreams[f"audio-video/{stream['ext']}"].append(stream)
    
    # # Sort streams by filesize -> Not needed as yt-dlp sorts streams by default.
    # for groupName in groupedStreams:
    #     groupedStreams[groupName].sort(key = lambda x: x["filesize"] if x["filesize"] else x["filesize_approx"])
    
    return groupedStreams


def printStreamsTable(streams: dict[str, list[dict[str, object]]]) -> list[int]:
    """
    Description:
        Prints the grouped streams of a youtube video in a tabular format.
    ---
    Parameters:
        `streams -> dict[str, list[dict[str, object]]]`: A dictionary containing the grouped streams of a youtube video.
    ---
    Returns:
        `list[int]` => A list containing the number of streams in each category.
    """
    
    bgColor = " on #00005f"
    
    table = Table(
        style=f"bold blue1{bgColor}",
        row_styles=[
            f"bold medium_purple3{bgColor}",
            f"bold dark_violet{bgColor}",
        ],
        header_style=f"bold deep_pink1{bgColor}",
        show_lines=True,
        box=box.DOUBLE,
    )
    
    table.add_column("Category", justify="left", no_wrap=True, vertical="middle")
    table.add_column("Quality",  justify='left')
    table.add_column("Size",  justify='right')
    table.add_column("ASR",  justify='right')
    table.add_column("TBR",     justify="right")
    table.add_column("FPS", justify="left")
    table.add_column("vCodec", justify="left")
    table.add_column("aCodec", justify="left")
    
    groupedStreamsCounts = []
    for i, groupName in enumerate(streams, 1):
        groupedStreamsCounts.append(len(streams[groupName]))
        
        qualities   = []
        sizes       = []
        audioSampleRates = [] # Hz
        totalBitrates = []    # kbps
        framerates = []
        vCodecs     = []
        aCodecs     = []
        
        for j, stream in enumerate(streams[groupName], 1):
            qualities.append(f"{j}) {stream['format_note']}")
            
            streamSize: int = stream["filesize"] or stream["filesize_approx"] # type: ignore
            if streamSize > 1023*1024*1024:
                sizes.append(f"{round(streamSize/1024/1024/1024, 2):7.2f} GB")
            
            else:
                sizes.append(f"{streamSize/1024/1024:7.2f} MB")
            
            audioSampleRates.append(f"{int(stream['asr']//1000)} kHz" if stream["asr"] else "") # type: ignore
            totalBitrates.append(f"{int(stream['tbr'])} kbps") # type: ignore
            framerates.append(str(stream['fps']) if stream['fps'] else "")
            vCodecs.append(stream['vcodec'] if stream['vcodec'] != "none" else "")
            aCodecs.append(stream['acodec'] if stream['acodec'] != "none" else "")
        
        table.add_row(f"({i}) {groupName}", "\n".join(qualities),
                      "\n".join(sizes), "\n".join(audioSampleRates),
                      "\n".join(totalBitrates), "\n".join(framerates),
                      "\n".join(vCodecs), "\n".join(aCodecs))
    
    console.print(table)
    print("")
    
    return groupedStreamsCounts


def extractSelectedStreams(grouped_streams: dict[str, list[dict[str, object]]], selected_streams_indexes: list[int]) -> tuple[str, int, bool]:
    """
    Description:
        Extracts the format ids of the selected streams from the `grouped_streams` dict based on the specified indexes.
    ---
    Parameters:
        - `grouped_streams -> dict[str, list[dict[str, object]]]`: A dict containing grouped streams, where the keys are stream
            categories and the values are lists of streams within each category.
        
        - `selected_streams_indexes -> list[int]`: A list of indexes that specify which streams to extract from the `grouped_streams` dict.
    
    ---
    Returns:
        `tuple[str, int, bool]`: => A tuple containing the selected stream formats, the total size, and a boolean indicating wether a video format is selected.
    """
    
    streamCategories = list(grouped_streams.keys())
    selectedStreams: dict[str, dict[str, object]] = {}
    
    if "video" in streamCategories[selected_streams_indexes[0]].split("/")[0]:
        selectedStreams["video"] = grouped_streams[streamCategories[selected_streams_indexes[0]-1]][selected_streams_indexes[1]-1]

        if len(selected_streams_indexes) > 2:
            selectedStreams["audio"] = grouped_streams[streamCategories[selected_streams_indexes[2]-1]][selected_streams_indexes[3]-1]
        
    else:
        selectedStreams["audio"] = grouped_streams[streamCategories[selected_streams_indexes[0]-1]][selected_streams_indexes[1]-1]
        
        if len(selected_streams_indexes) > 2:
            selectedStreams["video"] = grouped_streams[streamCategories[selected_streams_indexes[2]-1]][selected_streams_indexes[3]-1]
    
    selectedFormats = ""
    totalSize = 0
    if "video" in selectedStreams:
        selectedFormats = f"{selectedStreams['video']['format_id']}"
        totalSize += selectedStreams["video"]["filesize"] if "filesize" in selectedStreams["video"] else selectedStreams["video"]["filesize_approx"] # type: ignore
    
    if "audio" in selectedStreams:
        selectedFormats += f"{'+' if 'video' in selectedStreams else ''}{selectedStreams['audio']['format_id']}"
        totalSize += selectedStreams["audio"]["filesize"] if "filesize" in selectedStreams["audio"] else selectedStreams["audio"]["filesize_approx"] # type: ignore
    
    return (selectedFormats, totalSize, "video" in selectedStreams)


def downloadYoutubeVideo(yt_opts: dict[str, object], meta: dict[str, object], download_location: str, downloaded_before=False) -> int:
    """
    Description:
        Downloads a YouTube video using the provided options, updates download history database, stores the video description into a text file.
    ---
    Parameters:
        `yt_opts -> dict[str, object]`: A dict containing options for configuring the behavior of the `yt-dlp` downloader.
        
        `meta -> dict[str, object]`: A dict containing YouTube video metadata.
        
        `download_location -> str`: Specifies where the downloaded video will be saved
        
        `downloaded_before -> bool`: A flag that indicates whether the video has been downloaded before.
            If `True`, the function will update the download history instead of adding a new record.
    
    ---
    Returns:
        `int` => The status code of the download operation.
    """
    
    yt_opts |= {
        "checkformats": "selected",
        "addmetadata": True,
        "writethumbnail": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "embedthumbnail": True,
        "embedsubtitles": True,
        "subtitleslangs": ["ar", "en"],
        "concurrent_fragment_downloads": "5",
        "compat_opts": {"no-keep-subs"},
    }
    
    yt_opts["postprocessors"] = yt_opts.get("postprocessors", []) + [
        # The order of the postprocessors is important as some of them may affect the output of the previous ones.
        {
            "key": "FFmpegMetadata",
            "add_chapters": True,
            "add_metadata": True,
            "add_infojson": "if_exists",
        },
        {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False},
        {"key": "EmbedThumbnail", "already_have_thumbnail": False},
    ] # type: ignore
    
    
    with yt_dlp.YoutubeDL(yt_opts) as ydl:
        if statusCode := ydl.download(meta["webpage_url"]):
            console.print(f"[warning1]Warning! Download operation exitted with status code {statusCode}.[/]")
            
            return statusCode
        
        filename = os.path.splitext(ydl.prepare_filename(meta))[0]
        conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "download_history.db"))
        c = conn.cursor()
        
        if downloaded_before:
            query = "UPDATE History SET filename = :filename, location = :location, date = :date WHERE video_id = :video_id"
        
        else:
            query = "INSERT INTO History VALUES (:video_id, :filename, :location, :date)"
        
        c.execute(query, {"video_id": meta["id"], "filename": filename, "location": download_location,
                          "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S")})
        
        conn.commit()
        conn.close()
        
        if not os.path.exists(f"{filename}.txt"):
            with open(f"{filename}.txt", "w") as f:
                f.write(f"Title: {str(meta['title'].encode('utf-8'))}\nLink: {str(meta['webpage_url'].encode('utf-8'))}\nDescription:\n{str(meta['description'].encode('utf-8'))}")
        
        return statusCode


def downloadSingleYoutubeVideo(vidLink: str, subDir="") -> int:
    """
    Description:
        Downloads a single youtube video.
    ---
    Parameters:
        `vidLink -> str`: The link of the youtube video to download.
        
        `subDir -> str`: An optional parameter to specify a sub-directory to download the videos to.
    
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
        
        conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "download_history.db"))
        c = conn.cursor()
        
        c.execute("""CREATE TABLE IF NOT EXISTS History (
            video_id TEXT PRIMARY KEY,
            filename text,
            location text,
            date text)""")
        
        c.execute("SELECT * FROM History WHERE video_id = ?", (meta["id"],))
        
        downloadedBefore = False
        if result := c.fetchone():
            if os.path.isfile(os.path.join(result[2], result[1]+".mp4")) or os.path.isfile(os.path.join(result[2], result[1]+".m4a")):
                console.print(f"[normal1]The \"[normal2]{meta['title']}[/]\" video has already been downloaded on [normal2]{result[3]}[/].[/]")
                conn.close()
                return -4 # File is already downloaded.
            
            console.print(f"[normal1]The \"[normal2]{meta['title']}[/]\" video has been downloaded before on [normal2]{result[3]}[/] but the file is missing from '{os.path.join(result[2], result[1])}'.[/]\n")
            if not tui.yesNoQuestion("Do you want to download it again?", 0, [1, 0], ["Yes", "No"], [1, 2]):
                conn.close()
                return -3 # File is missing and user doesn't want to download it again.
            
            downloadedBefore = True
        
        console.print("\n[normal1]Available [normal2]streams[/] are:[/]")
        console.print(f"[normal1]{'='*22}[/]")
        groupedStreams = groupYoutubeStreams(meta["formats"])
        categoriesLengths = printStreamsTable(groupedStreams)
        
        console.print(f"[normal1]Video Title : [normal2]{meta['title']}[/][/]")
        console.print(f"[normal1]Duration    : [normal2]{meta['duration_string']}[/] min[/]", end="  |  ")
        console.print(f"[normal1]Release Date: [normal2]{datetime.strptime(meta['upload_date'], '%Y%m%d').strftime('%d/%m/%Y')}[/][/]\n")
        
        # Ex: [1, 5, 4, 1] => (cat, res, cat, res)
        selectedStreamsIndexes = dh.selectStreams(categoriesLengths)
        if not selectedStreamsIndexes:
            conn.close()
            return -2 # User canceled the download process
        
        selectedFormats, streamsSize, videoSelected = extractSelectedStreams(groupedStreams, selectedStreamsIndexes)
        streamsSize /= (1024 * 1024)
        
        console.print(f"[normal1]Total file size: [normal2]{format(streamsSize / 1024, '.2f')+'[/] GB' if streamsSize >= 1024 else format(streamsSize, '.2f')+'[/] MB'}[/]")
        print("")

        # https://github.com/yt-dlp/yt-dlp/issues/630#issuecomment-893659460
        yt_opts |= {
            "format": selectedFormats,
            "outtmpl": os.path.join(downloadLocation, "%(title)s.%(ext)s"),
        }
        
        return downloadYoutubeVideo(yt_opts, meta, downloadLocation, downloadedBefore) # type: ignore


def printPlaylistTable(playlist_entries: list[dict[str, str | int]]) -> None:
    """
    Description:
        Prints the streams of a youtube playlist in a tabular format.
    ---
    Parameters:
        `playlistEntries -> list[dict[str, str|int]]]`: A list of youtube playlist videos.
    """
    
    bgColor = " on #00005f"
    table = Table(
        style=f"bold blue1{bgColor}",
        row_styles=[f"bold medium_purple3{bgColor}", f"bold dark_violet{bgColor}"],
        header_style=f"bold deep_pink1{bgColor}",
        show_lines=True,
        box=box.SQUARE,
    )
    
    table.add_column("Index", justify="center")
    table.add_column("Duration",  justify='left')
    table.add_column("Downloaded",  justify='center')
    table.add_column("Name", justify="left", no_wrap=True)
    
    for i, entry in enumerate(playlist_entries, 1):
        duration = divmod(entry["duration"], 60) # type: ignore
        durationStr = f"[normal2]{duration[0]:02}[/]:[normal2]{duration[1]:02}[/] min{'s' if duration[0] > 1 else ''}"
        
        table.add_row(f"({i})", durationStr, f"{'[exists]Yes' if entry['downloaded'] else '[red]No'}[/]", str(entry["title"]))
    
    console.print(table)
    print("")


def downloadYoutubePlaylist(playlist_link: str, start_from=0, end_with=0, subDir="") -> tuple[int, str]:
    """
    Description:
        Downloads one or more videos from a youtube playlist.
    ---
    Parameters:
        `playlistLink -> str`: The link of the youtube playlist to download.
        
        `start_from -> int`: The playlist entry number to start downloading from.
        
        `end_with -> int`: The last playlist entry to download.
        
        `subDir -> str`: An optional parameter to specify a sub-directory to download the videos to.
    
    ---
    Returns:
        `tuple[int, str]` => Always returns the status code `0` (success) and the name of the download folder.
    """
    
    yt_opts = {
        "quiet": True, "progress": True,
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
    
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "download_history.db"))
    c = conn.cursor()
    
    c.execute("""CREATE TABLE IF NOT EXISTS History (
        video_id TEXT PRIMARY KEY,
        filename text,
        location text,
        date text)""")
    
    results = []
    for entry in playlistEntries:
        c.execute("SELECT * FROM History WHERE video_id = ?", (entry["id"],))
        results.append(c.fetchone())
        entry["downloaded"] = results[-1] is not None
    
    conn.close()
    
    console.print("[normal1]Availabe video in the playlist:[/]\n")
    printPlaylistTable(playlistEntries)
    console.print(f"[normal1]Playlist: [normal2]{playlistMeta['title']}[/] \[[normal2]{len(playlistMeta['entries'])}[/] Videos][/]")
    console.print(f"[normal1]{'='* (10 + len(playlistMeta['title']))}[/]")
    
    startEnd = dh.getPlaylistStartAndEnd(len(playlistMeta), start_from, end_with)
    
    downloadThreads = []
    totalSize     = 0.0
    totalDuration = 0.0
    for i, entry in enumerate(playlistEntries[startEnd[0]-1:startEnd[1]], startEnd[0]):
        if entry["downloaded"]:
            if os.path.isfile(os.path.join(results[i-1][2], results[i-1][1])):
                console.print(f"[normal1]The \"[normal2]{entry['title']}[/]\" video has already been downloaded on [normal2]{results[i-1][3]}[/].[/]")
                
                continue
            
            console.print(f"[normal1]The \"[normal2]{entry['title']}[/]\" video has been downloaded before on [normal2]{results[i-1][3]}[/] but the file is missing.[/]\n")
            if not tui.yesNoQuestion("Do you want to download it again?", 0, [1, 0], ["Yes", "No"], [1, 2]):
                continue
        
        yt_opts = {
            "quiet": True, "progress": True, "consoletitle": True, "noplaylist": True,
            "outtmpl": os.path.join(downloadLocation, "%(title)s.%(ext)s"),
        }
        
        with yt_dlp.YoutubeDL(yt_opts) as ydl:
            with console.status("[normal1]Fetching available streams...[/]"):
                try:
                    meta = ydl.extract_info(entry["url"], download=False)
                except yt_dlp.utils.DownloadError:
                    meta = None
        
        if meta is None or "formats" not in meta:
            console.print(f"[warning1]ConnectionAbortedError: Could not [warning2]extract[/] the youtube video info with id=[waring2]{entry['id']}[/].[/]")
            continue
        
        console.print("\n[normal1]Available [normal2]streams[/] are:[/]")
        console.print(f"[normal1]{'='*22}[/]")
        groupedStreams = groupYoutubeStreams(meta["formats"])
        categoriesLengths = printStreamsTable(groupedStreams)
        
        console.print(f"[normal1]Video #{i} : [normal2]{meta['title']}[/][/]")
        console.print(f"[normal1]Duration    : [normal2]{meta['duration_string']}[/] min[/]", end="  |  ")
        console.print(f"[normal1]Release Date: [normal2]{datetime.strptime(meta['upload_date'], '%Y%m%d').strftime('%d/%m/%Y')}[/][/]\n")
        
        selectedStreamsIndexes = dh.selectStreams(categoriesLengths)
        if not selectedStreamsIndexes:
            continue # User skipped the video.
        
        selectedFormats, streamsSize, videoSelected = extractSelectedStreams(groupedStreams, selectedStreamsIndexes)
        totalDuration += meta["duration"]
        totalSize     += streamsSize
        
        yt_opts |= {
            "format": selectedFormats,
            "outtmpl": os.path.join(downloadLocation, f"({i}). %(title)s.%(ext)s"),
        }
        
        thread = threading.Thread(target=downloadYoutubeVideo, args=(yt_opts, meta, downloadLocation, entry["downloaded"]))
        thread.start()
        downloadThreads.append(thread)
    
    for thread in downloadThreads:
        thread.join()
    
    playsound.playsound(SFX_LOC)
    
    mins, secs = divmod(totalDuration, 60)
    hours = 0
    if mins > 59:
        hours, mins = divmod(mins, 60)
    hours, mins, secs = int(hours), int(mins), int(secs)
    
    totalSize /= (1024 * 1024)
    
    console.print(f"[normal1]Total content size:     [normal2]{format(totalSize / 1024, '.2f')+'[/] GB' if totalSize >= 1024 else format(totalSize, '.2f')+'[/] MB'}[/]")
    console.print(f"[normal1]Total content duration: {'[normal2]'+format(hours, '02')+'[/]:' if hours else ''}[normal2]{mins:02}[/]:[normal2]{secs:02}[/][/]mins")
    print("")
    
    return 0, folderName


# TODO: Download part of a video -> Videos can be downloaded partially based on either timestamps or chapters using --download-sections
