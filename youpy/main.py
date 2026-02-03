"""This is the main entry point for the entire script."""

import sys
from common import console


if any([arg in sys.argv for arg in ["-h", "--help"]]):
    console.print(r"""
[normal1]python "[normal1]main.py" \[[normal2]script_mode[/]] \[[normal2]target_link[/]] \[[normal2]from_video[/]] \[[normal2]to_video[/]] \[[normal2]options/flags[/]]

[normal2]script_mode[/] : [normal2]1[/] -> download one video
            : [normal2]2[/] -> download videos with links from a file
            : [normal2]3[/] -> download a playlist[/]
            : [normal2]4[/] -> same as [normal2]2[/] but pass links as arguments or later in the script

[normal2]target_link[/] : A link to a youtube [normal2]video[/] when downloading in mode [normal2]"1"[/].
            : A link to a youtube [normal2]playlist[/] when downloading in mode [normal2]"3"[/].
            : Space-separated links to youtube [normal2]videos[/] when downloading in mode [normal2]"4"[/].

[normal2]from_video[/]  : The [normal2]video number[/] from where to start downloading when downloading a [normal2]playlist[/].

[normal2]to_video[/]    : The [normal2]video number[/] of the last video you want when downloading a [normal2]playlist[/].

Options/Flags:
=============
    '[normal2]-ao[/]' or '[normal2]--audio-only[/]' -> Download only the audio stream with the highest quality without prompting the user for selection.

    '[normal2]-d[/]' or '[normal2]--description[/]' -> Determines whether to write the [normal2]video description[/] to a text file or not.

    '[normal2]-h[/]' or '[normal2]--help[/]' -> Shows this help message and exit.

    '[normal2]-st[/]' or '[normal2]--show-thumbnails[/]' -> Prints [normal2]video thumbnail[/] to the console.

    '[normal2]-spt[/]' or '[normal2]--show-playlist-table[/]' -> Determines whether to show the playlist videos table in playlist mode ot not. Defaults to `False`.
[/]""")
    
    sys.exit(0)

import os
from glob import glob

sys.path.append(os.path.dirname(__file__))

import downloadHelper as dh
import youtubeCore as ytc
import tui

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__))))
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads"), exist_ok=True)


def downloadSingleFile(video_link: str, write_desc=False, best_audio=False) -> tuple[bool, str]:
    """
    Description:
        Download one youtube video.
    ---
    Parameters:
        `video_link -> str`: A link to a youtube video.
        
        `write_desc -> bool`: A flag that indicates whether to write the video description into a text file or not. Defaults to `False`.
        
        `best_audio -> bool`: A flag that indicates whether to download the best audio stream only. Defaults to `False`.
    
    ---
    Returns:
        `tuple[bool, str]` => Whether to continue the script with the same mode or end it and the name of the download folder.
    """
    
    if not video_link:
        console.print("[normal1]Enter a [normal2]link[/] to a YouTube [normal2]video[/]:[/]", end=" ")
        video_link = input().strip()
        print("")
    
    folderName = ytc.downloadSingleVideo(video_link=video_link, write_desc=write_desc, best_audio=best_audio)
    
    continueChoice = tui.yesNoQuestion("Download another video?")
    print("")
    
    return continueChoice != 0, folderName


def downloadPlaylist(playlist_link: str, from_video=0, to_video=0, write_desc=True, best_audio=False, show_playlist_table=False) -> tuple[bool, str]:
    """
    Description:
        Downloads one or more videos from a youtube playlist.
    ---
    Parameters:
        `playlist_link -> str`: The link of the youtube playlist to download.
        
        `start_from -> int`: The playlist entry number to start downloading from.
        
        `end_with -> int`: The last playlist entry to download.
        
        `write_desc -> bool`: A flag that indicates whether to write the video description for each video into a text file or not. Defaults to `True`.
        
        `best_audio -> bool`: A flag that indicates whether to download the best audio stream only. Defaults to `False`.
        
        `show_playlist_table -> bool`: A flag that indicates whether to print the playlist videos table or not. Defaults to `False`.
    
    ---
    Returns:
        `tuple[bool, str]` => Whether to continue the script with the same mode or not and the name of the download folder.
    """
    
    if not playlist_link:
        console.print("[normal1]Enter a [normal2]link[/] to a YouTube [normal2]playlist[/]:[/]", end=" ")
        playlist_link = input().strip()
        print("")
    
    folderName = ytc.downloadYoutubePlaylist(playlist_link, from_video, to_video, write_desc=write_desc, best_audio=best_audio, show_playlist_table=show_playlist_table)
    
    continueChoice = tui.yesNoQuestion("Download another playlist?")
    print("")
    
    return continueChoice != 0, folderName


def run():
    """Manages and runs the whole script."""
    
    linkFromTerminalArgument = ""
    if len(sys.argv) > 1:
        if sys.argv[1] == "1":
            choice = 1
        
        elif sys.argv[1] == "2":
            choice = 2
        
        elif sys.argv[1] == "3":
            choice = 3
        
        elif sys.argv[1] == "4":
            choice = 4
        
        else:
            choice = 0
        
        if len(sys.argv) > 2:
            linkFromTerminalArgument = sys.argv[2]
    else:
        choice = tui.selectionQuestion("Choose one mode:", ("One Video", "Links From File", "Playlist", "Multiple Video Links"), 0, (1, 2, 3, 4))
        print("")
    
    write_desc = False
    if any(arg in ("-d", "--description") for arg in sys.argv):
        write_desc = True
        sys.argv.remove("-d") if "-d" in sys.argv else sys.argv.remove("--description")
    
    if choice != -999:
        downloadBestAudio = False
        if any(arg in ("-ao", "--audio-only") for arg in sys.argv):
            downloadBestAudio = True
            sys.argv.remove("-ao") if "-ao" in sys.argv else sys.argv.remove("--audio-only")
        
        showPlaylistTable = False
        if any(arg in ("-spt", "--show-playlist-table") for arg in sys.argv):
            showPlaylistTable = True
        
        if choice == 4:
            videoLinks = []
            if len(sys.argv) > 2:
                videoLinks.extend((" ".join(sys.argv[2:])).split(" "))
            else:
                console.print("[normal1]Enter the [normal2]links[/] to the [normal2]youtube videos[/] you want to download (enter a [normal2]blank line[/] to continue):[/]")
                while True:
                    link = input(f"> Link {len(videoLinks)+1:02}: ").strip()
                    if link == "":
                        break
                    videoLinks.extend(link.split(" "))
            
            videoLinks = dh.removeDuplicateLinks(videoLinks)
            dh.writeLinksToFile(videoLinks) # type: ignore
            
            print("")
            
            choice = 2
        
        while True:
            if choice == 1:
                continueOption, folderName = downloadSingleFile(linkFromTerminalArgument, write_desc=write_desc, best_audio=downloadBestAudio)
            
            elif choice == 2:
                folderName = ytc.downloadMultipleYoutubeVideos(write_desc=write_desc, best_audio=downloadBestAudio)
                continueOption = False
            
            elif choice == 3:
                if len(sys.argv) > 4:
                    continueOption, folderName = downloadPlaylist(playlist_link=linkFromTerminalArgument, from_video=int(sys.argv[3]), to_video=int(sys.argv[4]), write_desc=write_desc, best_audio=downloadBestAudio, show_playlist_table=showPlaylistTable)
                else:
                    continueOption, folderName = downloadPlaylist(playlist_link=linkFromTerminalArgument, write_desc=write_desc, best_audio=downloadBestAudio, show_playlist_table=showPlaylistTable)
            
            else:
                console.print("[warning1]Invalid choice. Exiting...[/]")
                continueOption = False
                folderName = ""
            
            if not continueOption:
                console.print("[normal1][normal2]Opening[/] the [exists]download directory[/] and [normal2]terminating[/] the script...[/]")
                
                if listOfFiles := glob(os.path.join(os.path.dirname(__file__), "downloads", folderName, "*.m[p4][4a]")):
                    os.system(f"explorer /select, \"{max(listOfFiles, key=os.path.getctime)}\"")
                else:
                    os.startfile(os.path.join(os.path.dirname(__file__), "downloads", folderName))
                
                break
            
            # Clear the previously entered video link and terminal arguments if another iteration is happening:
            linkFromTerminalArgument = ""
            videoLinks = ""
            sys.argv = [sys.argv[0]]


if __name__ == "__main__":
    run()
    # downloadPlaylist("https://www.youtube.com/playlist?list=PL62tSREI9C-cHV28v-EqWinveTTAos8Pp", from_video=0, to_video=0, write_desc=True, best_audio=False)

#TODO: when downloading only audio files, make sure to remux into mp3 or m4a (for thumnail and so on).
