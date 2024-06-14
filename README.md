# YouTube Downloader with `yt-dlp`

This is a YouTube downloader utility powered by `yt-dlp`. Unlike `pytube`, `yt-dlp` offers improved stability and reliability in downloading YouTube videos, with an active community maintaining its development.

![Video Download](https://github.com/Ryen-042/Youtube-Downloader-Yt-Dlp/blob/main/images/video-download.gif?raw=true)

## Why `yt-dlp`?

When I used to download YouTube videos, my go-to module was `pytube`. One significant downside, though, was the time it took to fix issues caused by changes in the YouTube API. When I really wanted to download videos, this delay frequently left me waiting for module updates, which took a long time. Whenever this occurred, I had to look for fixes or workarounds to get the module back up and running. Fortunately, the helpful folks in the project's issues section helped me most of the time, but it was still a hassle.

`yt-dlp`, on the other hand, benefits from a large community that actively maintains and updates the library. With this support, any potential issues resulting from YouTube API changes are promptly addressed, ensuring a more reliable downloading experience.

## Features

### Overview

- Download audio and video streams in various formats and resolution options.
- Automatically merge selected audio and video streams into a single file when selecting both streams.
- Automatically include subtitles, video sections, video thumbnails, and other metadata with the downloaded video.

### Download Modes

- **Single Video**: Download a single YouTube video (script mode `1`).
- **Batch Download**: Download videos from links listed in `video-links.txt` (script mode `2`).
- **Playlist Download**: Download videos from a YouTube playlist (script mode `3`).
- **Terminal Input**: Download videos by entering links directly in the terminal (script mode `4`).
- **Audio Only**: Download the highest quality audio stream available without additional input (use `--audio-only` or `-ao`).

### Interface

- Maintain a download history to prevent duplicate downloads.
- Display a custom-made progress bar for multi-file downloads.
- Display video thumbnails in the terminal (use `--show-thumbnail` or `-st`).

## Getting Started

1. Clone the repository:

    ```bash
    git clone https://github.com/Ryen-042/Youtube-Downloader-Yt-Dlp.git
    ```

2. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```
    Or use the `make` command:

    ```bash
    make install-reqs
    ```

## Usage

You can run this script either interactively or with command-line arguments to skip input prompts.

- **Interactive Mode**: 

    ```bash
    python main.py
    ```

- **Command-Line Mode**:

    ```bash
    python main.py [script_mode] [youtube_link] [start_video_number] [end_video_number]
    ```

## Makefile Commands

The Makefile includes several useful commands for running, installing, and cleaning up the project:

- `make run`: Run the script.
- `make install`: Install the project from the source files.
- `make install-reqs`: Install the required dependencies.
- `make clean`: Remove the `__pycache__` and build folders.
