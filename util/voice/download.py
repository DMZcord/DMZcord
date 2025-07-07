import asyncio
import yt_dlp
import os

class MusicDownloader:
    @staticmethod
    async def download_youtube(url: str, outtmpl: str):
        ydl_opts = {
            'format': 'bestaudio[abr<=128]/bestaudio/best',
            'quiet': True,
            'outtmpl': outtmpl,
            'noplaylist': True,
            'cachedir': False,
            'no_color': True,
        }
        loop = asyncio.get_running_loop()
        info, filename = await loop.run_in_executor(
            None,
            lambda: MusicDownloader._yt_dlp_download(ydl_opts, url)
        )
        return info, filename

    @staticmethod
    def _yt_dlp_download(ydl_opts, url):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        return info, filename
