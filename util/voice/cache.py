import os
import logging
from util.core import SizeUtils

logger = logging.getLogger(__name__)

class MusicCacheManager:
    MUSIC_CACHE_DIR = os.path.join(os.path.dirname(__file__), "music_cache")

    @classmethod
    def get_music_cache_path(cls, guild_id, video_id, ext):
        """Get the file path for cached music."""
        return os.path.join(cls.MUSIC_CACHE_DIR, f"song_{guild_id}_{video_id}.{ext}")

    @classmethod
    def clear_music_cache(cls):
        """Delete all files in the music_cache directory."""
        removed = 0
        total_size = 0

        if os.path.exists(cls.MUSIC_CACHE_DIR):
            for f in os.listdir(cls.MUSIC_CACHE_DIR):
                file_path = os.path.join(cls.MUSIC_CACHE_DIR, f)
                try:
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
                        os.remove(file_path)
                        removed += 1
                except Exception as e:
                    logger.warning(f"Failed to remove {file_path}: {e}")
        else:
            os.makedirs(cls.MUSIC_CACHE_DIR, exist_ok=True)

        return f"✅ Music cache cleared. Files removed: {removed}, Total size freed: {SizeUtils.format_size(total_size)}"

    @staticmethod
    def decrement_cache(download_cache, cache_refcounts, cache_locks, filename):
        """Decrement cache reference count and cleanup if needed."""
        refcount = cache_refcounts.get(filename, 0)
        if refcount > 1:
            cache_refcounts[filename] = refcount - 1
        else:
            cache_refcounts.pop(filename, None)
            for url, (info, fname) in list(download_cache.items()):
                if fname == filename:
                    download_cache.pop(url)
                    cache_locks.pop(url, None)
            try:
                os.remove(filename)
            except Exception:
                pass