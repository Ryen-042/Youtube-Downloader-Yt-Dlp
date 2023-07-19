# Youtube downloader with `yt-dlp`

YouTube downloader utility powered by `yt-dlp`. Unlike `pytube`, `yt-dlp` offers improved stability and reliability in downloading YouTube videos, with a vibrant and active community maintaining its development.

## Why `yt-dlp`?

In the past, `pytube` was the go-to library for me for downloading YouTube videos. However, one major drawback was the time it took to fix issues caused by changes in the YouTube APIs. This delay often left me waiting for updates to regain functionality or until someone found a solution in the project's github issues.

`yt-dlp`, on the other hand, benefits from a huge community that actively maintains and updates the library. With this support, any potential issues resulting from YouTube API changes are promptly addressed, ensuring a more reliable downloading experience.

## Features

- Download YouTube videos with various stream formats and resolutions.

- Download from YouTube playlists.

- Downloads and embedding subtitles, video sections, video thumbnail, and other metadata.

- Selecting two streams for download automatically merges them.

- Implemented simple download history to prevent downloading duplicate videos.

## Getting Started

1. Download source files or clone the repository:

```bash
git clone https://github.com/Ryen-042/Youtube-Downloader-Yt-Dlp.git
```

2. Install the required dependencies. Use the `make install-reqs` command or or install the dependencies manually:

```bash
pip install -r requirements.txt
```
You can also install the package from the source files using the `make install` command or by running `pip install .` in the project directory:

## Usage

You can either run this script normally by entering inputs as asked or simply use terminal arguments to skip the input steps. Ex:

- Step by step: `python "main.py"`.

- With terminal args: `python "main.py" [script_mode] [youtube_link] [start_video_number] [end_video_number]`.

There are four script modes available:

- `1`: Download a single YouTube video.

- `2`: Download individual YouTube videos from links in a text file.

- `3`: Download videos from a YouTube playlist.

- `4`: Download individual YouTube videos from links entered in the terminal.

Here are some general usage instructions:

- Run python `"main.py" --help` for more information on the available terminal arguments.

- Provide inputs when prompted.

- Select one or two stream formats by entering the category index followed by the desired format index, separated by spaces. Leave the input empty to skip downloading.

- The selected video format(s) will be downloaded to the `downloads` folder.

## Makefile Commands

In the project files, there is a Makefile that contains several useful commands running, installing the project and dependencies, etc... Here are some of the most useful commands:

- `make run`: Run the script.

- `make install`: Install the project from the source files.

- `make install-reqs`: Install the required dependencies.

- `make clean`: Remove the `__pycache__` and build folders.
