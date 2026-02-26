import yt_dlp
import os

queue = []

async def download_song(song_name):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'song.%(ext)s',
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"ytsearch1:{song_name}"])

    return "song.webm"
