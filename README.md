# Dependencies

1. Visit https://github.com/BtbN/FFmpeg-Builds/releases and download the appropriate one that isn't shared
2. Extract the 3 .exe files to the repository (ffmpeg.exe, ffplay.exe, ffprobe.exe)
3. Install python from official website (Ensure PIP is installed as well as python is added to path during set up)
4. Run the command 'pip install -r requirements.txt' in command line

# Usage

1. download.bat will visit all bandori sites and download the songs and place them inside bushiroad/songs
2. convert.bat will convert the songs into mp3 (if there are multiple types of a song, only the one with the shortest name will be converted). This process can take anywhere from a few minutes to up to an hour depending on how ancient your computer is

# Architecture for downloading songs

All the code for downloading songs are located within bushiroad/spiders/bandori_spider.py
The spider first uses the urls located within its start_urls class attribute to visit the three category pages:
https://bandori.fandom.com/wiki/Category:Original_Songs
https://bandori.fandom.com/wiki/Category:Extra_Songs
https://bandori.fandom.com/wiki/Category:Cover_Songs
and pass the response to the parse method.

The parse method extracts all the band names from as well as category from the url (e.g Original_Songs)
It then extracts the links to each song page using the band names. A request is started for each link and the response,
together with the associated band name and category are sent to parse_song_page method.

parse_song_page extracts all the download links (dl_links) for the song page within the response.
The song_names are extracted from the dl_links and a file_path for them to be stored in is generated here.
A request is made to each dl_link and the response (song file) as well as the file_path are sent to the parse_song_download_link method

parse_song_download_link stores the file using the given file_path.

# Architecture for converting songs from ogg to mp3

All the code for converting songs are located within convert.py
