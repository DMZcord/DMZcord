
import datetime
from util.core.utils import TimeUtils

class Formatter:
    @staticmethod
    def format_queue(now_playing, now_playing_start, queue, download_cache):
        display_queue = []
        if now_playing:
            if now_playing_start:
                elapsed = (datetime.datetime.now() - now_playing_start).total_seconds()
                duration = now_playing.get('duration', 0)
                remaining = max(0, duration - int(elapsed))
                elapsed_str = TimeUtils.format_mmss(elapsed)
                duration_str = TimeUtils.format_mmss(duration)
                remaining_str = TimeUtils.format_mmss(remaining)
                time_str = f"{elapsed_str}/{duration_str} - {remaining_str} left"
            else:
                time_str = None
            title = now_playing.get('title', 'Unknown Title')
            queued_by = now_playing.get('queued_by', 'Unknown')
            if time_str:
                display_queue.append(f"1. {title} ({time_str}) (queued by {queued_by})")
            else:
                display_queue.append(f"1. {title} (queued by {queued_by})")
        for i, item in enumerate(queue):
            cache_entry = download_cache.get(item.get('url'))
            title = cache_entry[0].get('title', "Fetching...") if cache_entry and cache_entry[0] else "Fetching..."
            display_queue.append(f"{i+2}. {title} (queued by {item.get('queued_by', 'Unknown')})")
        return display_queue
