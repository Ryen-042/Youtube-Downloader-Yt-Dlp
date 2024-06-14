"""This module contains helper functions dealing with youtube streams."""

from datetime import datetime
from rich import box
from rich.table import Table
import yt_dlp

from common import console
import downloadHelper as dh

import sys

SHOW_THUMBNAILS = False
if any([arg in sys.argv for arg in ["-st", "--show-thumbnails"]]):
    import climage, requests
    from io import BytesIO
    from PIL import Image
    
    SHOW_THUMBNAILS = True
    sys.argv.remove("-st") if "-st" in sys.argv else sys.argv.remove("--show-thumbnails")


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
    
    groupedStreams: dict[str, list[dict[str, object]]] = dict()
    
    for stream in streams:
        # Filter out bad and unwanted streams.
        if (stream.get("format_note") in [None, 'Default']) or (stream.get("format_note")[:4].upper() == "DASH") or (stream["ext"] in ["mhtml", "3gp"]) or not (stream.get("filesize") or stream.get("filesize_approx")): # type: ignore
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
        
        else:
            if f"audio-video/{stream['ext']}" not in groupedStreams:
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
        duration = divmod(entry["duration"], 60) if entry["duration"] else [-1, -1] # type: ignore
        durationStr = f"[normal2]{duration[0]:02}[/]:[normal2]{duration[1]:02}[/] min{'s' if duration[0] > 1 else ''}"
        
        table.add_row(f"({i})", durationStr, f"{'[exists]Yes' if entry['downloaded'] else '[red]No'}[/]", str(entry["title"]))
    
    console.print(table)
    print("")

def getPlaylistStartAndEnd(playlist_count: int, start_from=0, end_with=0) -> list[int]:
    """
    Description:
        Prompts the user to enter two numbers representing from where to start and end downloading playlist videos.

        If no numbers are given or if they are not valid numbers, it asks the user again.

    ---
    Parameters:
        `playlist_count -> int`: The count of the videos in the playlist.

        `start_from -> int`: The playlist entry number to start downloading from.

        `end_with -> int`: The last playlist entry to download.
    ---
    Returns:
        A tuple containing two numbers representing the first and last video numbers.
    """

    if not start_from or not end_with:
        console.print("[normal1]Enter two nubmers separated by a [normal2]space[/] to specify the [normal2]start[/] and [normal2]end[/] of the playlist to download or [normal2]leave empty[/] to download the whole playlist: [/]", end="")
        startEnd = input().strip().split(" ")
    elif start_from == -1 and end_with in [-1, 0]:
        return [1, playlist_count]
    else:
        startEnd = [start_from, end_with]

    while True:
        # The user left the input blank, meaning they want to download all the videos in the playlist.
        if len(startEnd) == 1 and not startEnd[0]:
            return [1, playlist_count]

        elif len(startEnd) == 2:
            try:
                if int(startEnd[0]) > playlist_count or int(startEnd[1]) > playlist_count:
                    console.print(f"\n[warning1]The [warning2]start[/] and [warning2]end[/] cannot be greater than the [warning2]limit[/] ([warning2]{playlist_count}[/]). Your input: [warning2]{startEnd}[/]\nTry again: [/]", end="")

                # elif start_end[0] == 0:
                    # return [1, int(start_end[1])]

                # If end number is -1, then return the start and limit
                elif int(startEnd[1]) == -1:
                    return [int(startEnd[0]), playlist_count]

                elif int(startEnd[0]) > int(startEnd[1]):
                    console.print(f"\n[warning1]The [warning2]start[/] cannot be greater than the [warning2]end[/]. Your input: [warning2]{startEnd}[/]\nTry again: [/]", end="")

                else:
                    return [int(startEnd[0]), int(startEnd[1])]
            except Exception:
                console.print(f"\n[warning1]Invalid input: [warning2]{startEnd}[/]\nTry again: [/]", end="")
        else:
            console.print(f"\n[warning1]Invalid input. Requested [warning2]two numbers[/] but got [warning2]{len(startEnd)}[/] inputs: [warning2]{startEnd}[/]\nTry again: [/]", end="")

        startEnd = input().strip().split(" ")


def findStreamType(stream: dict[str, object]) -> str:
    """
    Description:
        Returns the type of the given stream.
    ---
    Parameters:
        `stream` -> `dict[str, object]`: A dictionary containing the stream information.
    ---
    Returns:
        str: The type of the stream. Possible values: `video`, `audio`, `audio-video`, `none`.
    """

    vcodec = stream.get("vcodec", "none") or "none"
    acodec = stream.get("acodec", "none") or "none"

    if vcodec != "none" and acodec != "none":
        return "audio-video"

    elif vcodec != "none":
        return "video"

    elif acodec != "none":
        return "audio"

    else:
        return "none"


def selectStreams(categories_lengths: list[int], groupedStreams: dict[str, list[dict[str, object]]]) -> tuple[dict[str, object], ...]:
    """
    Description:
        Prompts the user to select from the available stream options. User can select one or two stream formats by specifying the category index followed by the desired format index, separated by spaces.
        If the user wishes to skip downloading, they can simply leave the input empty.

        For example, if the user wishes to download the `first` stream format in the `third` category, they can simply enter `3 1` and press enter.

        If the user also wishes to download the `second` stream format in the `fifth` category, they can simply enter `3 1 5 2` and press enter.

    ---
    Parameters:
        `categories_lengths` -> list[int]`: The number of streams in each category.

        `groupedStreams` -> `dict[str, list[dict[str, object]]]`: A dictionary containing the available stream formats grouped by their category.

    ---
    Returns:
        `tuple[dict[str, obj]]` => A tuple containing the selected streams.
    """

    while True:
        console.print("[normal1]Select [normal2]one[/] or [normal2]two[/] stream formats by specifying the [normal2]category index[/] followed by the desired [normal2]format index[/], separated by spaces.\nIf you wish to skip downloading, simply [normal2]leave the input empty[/]:[/] ", end='')
        choices = input().strip().split(" ")
        print("")

        # If choices is empty (i.e., [""]) return an empty list.
        if len(choices) == 1 and not choices[0]:
            return tuple()

        if len(choices) > 4:
            console.print(f"[warning1]Invalid input. Requested at most [warning2]4[/] numbers, but got [warning2]{len(choices)}[/] inputs[/]\n")
            continue

        elif len(choices) < 2:
            console.print(f"[warning1][warning2]Not enough data[/]. Requested at least [warning2]2[/] numbers, but got [warning2]{len(choices)}[/] input.[/]\n")
            continue

        try:
            # Stream 1 validation.
            if 0 < int(choices[0]) <= len(categories_lengths):  # Valid category number.
                if 0 < int(choices[1]) <= categories_lengths[int(choices[0]) - 1]:  # Valid stream number.
                    if len(choices) == 2:
                        stream = groupedStreams[list(groupedStreams.keys())[int(choices[0]) - 1]][int(choices[1]) - 1]
                        stream["type"] = findStreamType(stream)

                        return (stream,)

                    # Stream 2 validation.
                    elif 0 < int(choices[2]) <= len(categories_lengths):
                        if 0 < int(choices[3]) <= categories_lengths[int(choices[2]) - 1]:
                            # Make sure that the user didn't select two streams of the same type (i.e., 2 video or 2 audio streams).
                            stream1 = groupedStreams[list(groupedStreams.keys())[int(choices[0]) - 1]][int(choices[1]) - 1]
                            stream2 = groupedStreams[list(groupedStreams.keys())[int(choices[2]) - 1]][int(choices[3]) - 1]

                            stream1["type"] = findStreamType(stream1)
                            stream2["type"] = findStreamType(stream2)

                            if "audio-video" in [stream1["type"], stream2["type"]]:
                                console.print("[warning1][warning2]Warning[/]! You are attempting to download a video that has both audio and video streams with another audio or video stream. This is not supported.[/]\n")

                            elif stream1["type"] == stream2["type"]:
                                console.print("[warning1][warning2]Warning[/]! You are attempting to download two streams of the same type. This is not supported.[/]\n")

                            else:
                                return (stream1, stream2)

                        else:
                            console.print("[warning1][warning2]Error Encountered[/]. Make sure the [warning2]second[/] selected [warning2]format index[/] is correct.[/]\n")

                    else:
                        console.print("[warning1][warning2]Error Encountered[/]. Make sure the [warning2]second[/] selected [warning2]category index[/] is correct.[/]\n")

                else:
                    console.print("[warning1][warning2]Error Encountered[/]. Make sure the [warning2]first[/] selected [warning2]format index[/] is correct.[/]\n")

            else:
                console.print("[warning1][warning2]Error Encountered[/]. Make sure the [warning2]first[/] selected [warning2]category index[/] is correct.[/]\n")

        except Exception:
            console.print("[warning1]Invalid input. You have entered something wrong.[/]\n")


def extractFormatIdsFromSelectedStreams(selectedStreams: tuple[dict[str, object], ...]) -> tuple[str, int]:
    """
    Description:
        Extracts the format ids of the selected streams from the specified streams.
    ---
    Parameters:
        `selectedStreams -> tuple[dict[str, object]]`: A tuple containing the selected streams.
    ---
    Returns:
        `tuple[str, int]`: => A tuple containing the selected stream formats and the total size.
    """
    
    audioFromatId = ""
    videoFromatId = ""
    totalSize = 0
    
    for stream in selectedStreams:
        if stream["type"] == "audio":
            audioFromatId = stream["format_id"]
        
        elif stream["type"] in ["video", "audio-video"]:
            videoFromatId = stream["format_id"]
        
        totalSize += stream["filesize"] if "filesize" in stream else stream["filesize_approx"] # type: ignore
    
    selectedFormats = f"{videoFromatId}+{audioFromatId}" if audioFromatId and videoFromatId else videoFromatId or audioFromatId
    
    return (selectedFormats, totalSize) # type: ignore


def parseAndSelectStreams(video_number, video_link, video_id, yt_extra_opts=None) -> dict[str, object]:
    """Wires up the logic of parsing the video info and selecting the streams to download."""

    yt_opts = {
        "quiet": True, "consoletitle": True, "noplaylist": True,
    }
    
    if yt_extra_opts:
        yt_opts |= yt_extra_opts

    with yt_dlp.YoutubeDL(yt_opts) as ydl:
        with console.status("[normal1]Fetching available streams...[/]"):
            try:
                meta = ydl.extract_info(video_link, download=False)
            except yt_dlp.utils.DownloadError:
                meta = None

    if meta is None or "formats" not in meta:
        console.print(f"[warning1]ConnectionAbortedError: Could not [warning2]extract[/] the youtube video info with id=[waring2]{video_id}[/].[/]")
        return dict()

    console.print("\n[normal1]Available [normal2]streams[/] are:[/]")
    console.print(f"[normal1]{'='*22}[/]")

    if SHOW_THUMBNAILS:
        thumbnail_url = meta.get('thumbnail', '')
        if thumbnail_url:
            response = requests.get(thumbnail_url)

            # Convert to RGB, as files on the Internet may be greyscale, which are not supported.
            img = Image.open(BytesIO(response.content)).convert('RGB')

            # Convert the image to 80col, in 256 color mode, using unicode for higher def.
            converted = climage.convert_pil(img, is_unicode=True,  **climage.color_to_flags(climage.color_types.truecolor)) # type: ignore
            print(converted)

        else:
            console.print("[warning1]No [warning2]thumbnail[/] was found for this video.[/]")

    groupedStreams = groupYoutubeStreams(meta["formats"])
    categoriesLengths = printStreamsTable(groupedStreams)

    console.print(f"[normal1]Video #{f'{video_number}:<3' if video_number else 'Title '}: [normal2]{meta['title']}[/][/]")
    console.print(f"[normal1]Duration    : [normal2]{meta['duration_string']}[/] min[/]", end="  |  ")
    console.print(f"[normal1]Release Date: [normal2]{datetime.strptime(meta['upload_date'], '%Y%m%d').strftime('%d/%m/%Y')}[/][/]\n")

    selectedStreams = selectStreams(categoriesLengths, groupedStreams)
    if not selectedStreams:
        return dict() # User skipped the video.

    selectedFormats, streamsSize = extractFormatIdsFromSelectedStreams(selectedStreams)
    yt_opts |= {"format": selectedFormats}

    output = dict()
    output["meta"] = meta
    output["yt_opts"] = yt_opts
    output["size"] = streamsSize

    # Find the type of the selected streams and the expected output file extension.
    output["fileExtension"] = "mp4" if len(selectedStreams) == 2 else selectedStreams[0]["ext"]

    return output
