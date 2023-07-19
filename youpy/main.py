"""This is the main entry point for the entire script."""


import os, playsound
import sys

sys.path.append(os.path.dirname(__file__))

from glob import glob
from common import console
import downloadHelper as dh
import youtubeCore as ytc
import tui

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__))))
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads"), exist_ok=True)


def YoutubeVideoDownloader(video_link: str) -> bool:
    """
    Description:
        Download one youtube video.
    ---
    Parameters:
        `video_link -> str`: A link to a youtube video.
    ---
    Returns:
        `bool` => Whether to continue the script with the same mode or end it.
    """
    
    if not video_link:
        console.print("[normal1]Enter a [normal2]link[/] to a YouTube [normal2]video[/]:[/]", end=" ")
        video_link = input().strip()
    
    print("")
    statusCode = ytc.downloadSingleYoutubeVideo(video_link)
    
    if statusCode == 0:
        playsound.playsound(os.path.join(os.path.dirname(os.path.abspath(__file__)), "SFX/Yay.mp3").replace("\\", "/"))
    
    continueChoice = tui.yesNoQuestion("Download another video?")
    print("")
    
    return continueChoice != 0


def YoutubePlaylistDownloader(playlist_link: str, from_video=0, to_video=0, sub_dir="") -> bool:
    """
    Description:
        Downloads one or more videos from a youtube playlist.
    ---
    Parameters:
        `playlist_link -> str`: The link of the youtube playlist to download.
        
        `start_from -> int`: The playlist entry number to start downloading from.
        
        `end_with -> int`: The last playlist entry to download.
        
        `subDir -> str`: An optional parameter to specify a sub-directory to download the videos to.
    
    ---
    Returns:
        `bool` => Whether to continue the script with the same mode or not.
    """
    
    if not playlist_link:
        console.print("[normal1]Enter a [normal2]link[/] to a YouTube [normal2]playlist[/]:[/]", end=" ")
        playlist_link = input().strip()
    
    print("")
    ytc.downloadYoutubePlaylist(playlist_link, from_video, to_video, sub_dir)
    
    continue_option_choice = tui.yesNoQuestion("Download another playlist?")
    print("")
    return continue_option_choice != 0


def YoutubeDownloaderFromFileLinks(filename="video-links.txt") -> bool:
    """
    Description:
        Download youtube videos with the links from the specified file.
    ---
    Parameters:
        `file_name -> str`: The name of the file containing the youtube video links.
    
    ---
    Returns:
        `bool` => Whether the links file was found or not.
    """
    
    if not os.path.exists(filename):
        return False
    
    with open(filename, "r") as file:
        for video_link in file:
            print("")
            ytc.downloadSingleYoutubeVideo(video_link)
    
    playsound.playsound(os.path.join(os.path.dirname(os.path.abspath(__file__)), "SFX/Yay.mp3").replace("\\", "/"))
    
    return True


def run():
    """Manages and runs the whole script."""
    
    console.print("[exists]Initializing script...[/]")
    
    linkFromTerminalArgument = ""
    if len(sys.argv) > 1:
        if sys.argv[1] in ["?", "help", "-h", "--help"]:
            console.print("""
[normal1]python "[normal1]main.py" \[[normal2]script_mode[/]] \[[normal2]target_link[/]] \[[normal2]from_video[/]] \[[normal2]to_video[/]]

[normal2]script_mode[/] : [normal2]1[/] -> download one video
            : [normal2]2[/]       -> download videos with links from a file
            : [normal2]3[/]       -> download a playlist[/]
            : [normal2]4[/]       -> same as [normal2]2[/] but pass links as arguments or later in the script

[normal2]target_link[/] : A link to a youtube [normal2]video[/] when downloading in mode [normal2]"1"[/].
            : A link to a youtube [normal2]playlist[/] when downloading in mode [normal2]"3"[/].
            : Space-separated links to youtube [normal2]videos[/] when downloading in mode [normal2]"4"[/].

[normal2]from_video[/]  : The [normal2]video number[/] from where to start downloading when downloading a [normal2]playlist[/].

[normal2]to_video[/]    : The [normal2]video number[/] of the last video you want when downloading a [normal2]playlist[/].
[/]""")
            
            choice = -999 # Skip and end the script.
        
        elif sys.argv[1] == "1":
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
        
        dh.writeLinksToFile(videoLinks)
        print("")
        
        choice = 2
    
    if choice != -999:
        while True:
            if choice == 1:
                continueOption = YoutubeVideoDownloader(linkFromTerminalArgument)
            elif choice == 2:
                continueOption = YoutubeDownloaderFromFileLinks()
            elif choice == 3:
                if len(sys.argv) > 4:
                    continueOption = YoutubePlaylistDownloader(playlist_link = linkFromTerminalArgument, from_video=int(sys.argv[3]), to_video=int(sys.argv[4]))
                else:
                    continueOption = YoutubePlaylistDownloader(playlist_link = linkFromTerminalArgument)
            else:
                console.print("[warning1]Invalid choice. Exiting...[/]")
                continueOption = False
            
            if not continueOption:
                console.print("[normal1][normal2]Terminating[/]the script and [normal2]opening[/] the [normal2]download directory[/].[/]")
                
                if listOfFiles := glob("downloads/*.mp4"):
                    os.system(f"explorer /select, \"{max(listOfFiles, key=os.path.getctime)}\"")
                else:
                    os.startfile(os.getcwd())
                break
            
            # Clear the previously entered video link and terminal arguments if another iteration is happening:
            linkFromTerminalArgument = ""
            sys.argv = [sys.argv[0]]


if __name__ == "__main__":
    run()
