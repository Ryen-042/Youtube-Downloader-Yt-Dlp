"""
This module provides functions for selecting, formatting, and downloading streams.
"""

import os
from common import console


def selectStreams(categories_lengths: list[int]) -> list[int]:
    """
    Description:
        Prompts the user to select from the available stream options. User can select one or two stream formats by specifying the category index followed by the desired format index, separated by spaces.
        If the user wishes to skip downloading, they can simply leave the input empty.
        
        For example, if the user wishes to download the `first` stream format in the `third` category, they can simply enter `3 1` and press enter.
        
        If the user also wishes to download the `second` stream format in the `fifth` category, they can simply enter `3 1 5 2` and press enter.
    
    ---
    Parameters:
        `categories_lengths` -> list[int]`: The number of streams in each category.
    
    ---
    Returns:
        `list[int]` => A list containing the selected category/ies and resolution/s.
    """
    
    validChoices = False
    while not validChoices:
        console.print("[normal1]Select [normal2]one[/] or [normal2]two[/] stream formats by specifying the [normal2]category index[/] followed by the desired [normal2]format index[/], separated by spaces.\nIf you wish to skip downloading, simply [normal2]leave the input empty[/]:[/] ", end='')
        choices = input().strip().split(" ")
        print("")

        # If choices is empty (i.e., [""]) return []
        if len(choices) == 1 and not choices[0]:
            return []

        if len(choices) > 4:
            console.print(f"[warning1]Invalid input. Requested at most [warning2]4[/] numbers, but got [warning2]{len(choices)}[/] inputs[/]\n")
            continue

        elif len(choices) < 2:
            console.print(f"[warning1][warning2]Not enough data[/]. Requested at least [warning2]2[/] numbers, but got [warning2]{len(choices)}[/] input.[/]\n")
            continue

        try:
            if int(choices[0]) <= len(categories_lengths):
                if int(choices[1]) <= categories_lengths[int(choices[0]) - 1]:
                    if len(choices) == 2:
                        validChoices = True
                    
                    elif int(choices[2]) <= len(categories_lengths):
                        if int(choices[3]) <= categories_lengths[int(choices[2]) - 1]:
                            validChoices = True
                        
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
    
    return [int(choice) for choice in choices] # type: ignore


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
