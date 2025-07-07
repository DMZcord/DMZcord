import asyncio
import threading
import yt_dlp
import os
from .cache import MusicCacheManager

class MusicDownloader:
    def __init__(self, download_cache, cache_locks, cache_refcounts, downloading):
        self.download_cache = download_cache
        self.cache_locks = cache_locks
        self.cache_refcounts = cache_refcounts
        self.downloading = downloading

    async def download_song(self, ctx, url, force_download=False):
        """Download a song from YouTube with caching."""
        lock = self.cache_locks.setdefault(url, threading.Lock())

        def download_with_lock():
            with lock:
                if not force_download and url in self.download_cache:
                    info, filename = self.download_cache[url]
                    self.cache_refcounts[filename] = self.cache_refcounts.get(filename, 0) + 1
                    return info, filename

                if not force_download and url in self.downloading:
                    event = self.downloading[url]
                    event.wait()
                    info, filename = self.download_cache[url]
                    self.cache_refcounts[filename] = self.cache_refcounts.get(filename, 0) + 1
                    return info, filename

                event = threading.Event()
                self.downloading[url] = event
                try:
                    outtmpl = MusicCacheManager.get_music_cache_path(ctx.guild.id, "%(id)s", "%(ext)s")
                    ydl_opts = {
                        'format': 'bestaudio[abr<=128]/bestaudio/best',
                        'quiet': True,
                        'outtmpl': outtmpl,
                        'noplaylist': True,
                        'cachedir': False,
                        'no_color': True,
                        'progress': False,
                        'noprogress': True,
                        'ratelimit': None,
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        filename = ydl.prepare_filename(info)
                    self.download_cache[url] = (info, filename)
                    self.cache_refcounts[filename] = 1
                    return info, filename
                finally:
                    event.set()
                    self.downloading.pop(url, None)

        return await asyncio.to_thread(download_with_lock)

    async def force_download_cleanup(self, ctx, url):
        """Force download cleanup for stuck downloads."""
        self.downloading.pop(url, None)
        self.download_cache.pop(url, None)
        self.cache_locks.pop(url, None)
        
        try:
            outtmpl = MusicCacheManager.get_music_cache_path(ctx.guild.id, "%(id)s", "%(ext)s")
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                video_id = info_dict.get('id')
                for ext in ['webm', 'm4a', 'mp3', 'opus']:
                    part_file = MusicCacheManager.get_music_cache_path(ctx.guild.id, video_id, ext) + ".part"
                    if os.path.exists(part_file):
                        os.remove(part_file)
        except Exception:
            pass