import asyncio
import datetime
import discord
from discord.ext import commands
from ..core.utils import TimeUtils
from .download import MusicDownloader
from .cache import MusicCacheManager
from .validation import MusicValidation

class MusicPlayback:
    def __init__(self, queues, download_cache, cache_locks, cache_refcounts, downloading, skip_votes, now_playing, now_playing_start, bot):
        self.queues = queues
        self.download_cache = download_cache
        self.cache_locks = cache_locks
        self.cache_refcounts = cache_refcounts
        self.downloading = downloading
        self.skip_votes = skip_votes
        self.now_playing = now_playing
        self.now_playing_start = now_playing_start
        self.bot = bot
        self.downloader = MusicDownloader(download_cache, cache_locks, cache_refcounts, downloading)

    async def play_audio(self, ctx, vc, info, filename):
        """Play audio file through Discord voice connection."""
        self.skip_votes[ctx.guild.id] = set()
        self.now_playing[0] = info
        self.now_playing_start[0] = datetime.datetime.now()

        def after_playing(error):
            fut = self.play_next(ctx, vc)
            asyncio.run_coroutine_threadsafe(fut, self.bot.loop)
            MusicCacheManager.decrement_cache(self.download_cache, self.cache_refcounts, self.cache_locks, filename)

        vc.play(discord.FFmpegPCMAudio(source=filename), after=after_playing)
        duration = info.get('duration')
        duration_str = TimeUtils.format_mmss(
            duration) if duration else "Unknown"
        coro = ctx.send(
            f"Now playing: {info.get('title', 'Unknown Title')} "
            f"({duration_str}) (queued by {info.get('queued_by', 'Unknown')})"
        )
        await coro

    async def play_next(self, ctx, vc):
        """Play the next song in queue."""
        queue = self.queues.get(ctx.guild.id, [])
        if not queue or vc.is_playing() or vc.is_paused():
            return

        song_entry = queue.pop(0)
        url = song_entry["url"]
        queued_by = song_entry.get("queued_by", "Unknown")

        force_download = False
        if url in self.downloading:
            await ctx.send("Song was not fully cached, downloading at full speed now...")
            await self.downloader.force_download_cleanup(ctx, url)
            force_download = True

        info, filename = await self.downloader.download_song(ctx, url, force_download=force_download)
        info['queued_by'] = queued_by

        # Check duration permissions
        duration = info.get('duration')
        allowed, message = MusicValidation.check_duration_permissions(
            ctx, duration)
        if not allowed:
            await ctx.send(message)
            return

        await self.play_audio(ctx, vc, info, filename)

    async def play_error(self, ctx, error):
        """Handle play command errors."""
        try:
            await ctx.message.delete()
        except Exception:
            pass
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You must provide a YouTube URL. Usage: `!play <url>`")
        else:
            await ctx.send(f"An error occurred: {error}")