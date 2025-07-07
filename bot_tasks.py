import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from discord.ext import tasks
from util.core import Database, CommandLogger
from util.moderation import MuteUtils
from util.owner import BlacklistUtils

logger = logging.getLogger(__name__)

class CommandLogTasks:
    def __init__(self, bot):
        self.bot = bot
        self._command_log_cache = []
        self._command_log_lock = asyncio.Lock()
        self._flush_task = None

    def start(self):
        if not self._flush_task:
            self._flush_task = self.bot.loop.create_task(self._flush_command_logs_loop())

    def stop(self):
        if self._flush_task:
            self._flush_task.cancel()
            self._flush_task = None

    async def _flush_command_logs_loop(self):
        while True:
            await asyncio.sleep(60)
            try:
                count = len(self._command_log_cache)
                if count == 0:
                    continue
                await CommandLogger.flush_command_logs(self.bot, self._command_log_cache, self._command_log_lock, logger)
                logger.info(
                    f"Flushed {count} command log entries - {datetime.now(timezone.utc).isoformat(sep=' ', timespec='seconds')} UTC")
            except Exception as e:
                logger.error(f"Exception in _flush_command_logs_loop: {e}", exc_info=True)

    @property
    def cache(self):
        return self._command_log_cache

    @property
    def lock(self):
        return self._command_log_lock

class BlacklistCleanupTasks:
    def __init__(self, bot):
        self.bot = bot
        self._cleanup_task = None

    def start(self):
        if not self._cleanup_task:
            self._cleanup_task = self.bot.loop.create_task(self._blacklist_cleanup_loop())

    def stop(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

    async def _blacklist_cleanup_loop(self):
        while True:
            await asyncio.sleep(60)
            try:
                await BlacklistUtils.cleanup_expired_blacklists(self.bot)
            except Exception as e:
                logger.error(f"Failed to clean up expired blacklists: {e}", exc_info=True)

class StatsResetTasks:
    def __init__(self, bot):
        self.bot = bot
        self._user_message_counts = defaultdict(int)
        self._user_command_counts = defaultdict(int)
        self._lock = asyncio.Lock()
        self._reset_task = None

    def start(self):
        if not self._reset_task:
            self._reset_task = self.bot.loop.create_task(self._reset_counts_loop())

    def stop(self):
        if self._reset_task:
            self._reset_task.cancel()
            self._reset_task = None

    async def _reset_counts_loop(self):
        while True:
            await asyncio.sleep(10)
            async with self._lock:
                self._user_message_counts.clear()
                self._user_command_counts.clear()

    @property
    def user_message_counts(self):
        return self._user_message_counts

    @property
    def user_command_counts(self):
        return self._user_command_counts

    @property
    def lock(self):
        return self._lock

class DatabaseTasks:
    def __init__(self, bot):
        self.bot = bot
        self._vacuum_db_started = False

    def start_all(self):
        """Start all database tasks."""
        self.vacuum_db.start()
        self.check_mutes.start()

    def stop_all(self):
        """Stop all database tasks."""
        self.vacuum_db.cancel()
        self.check_mutes.cancel()

    @tasks.loop(hours=12)
    async def vacuum_db(self):
        """Periodically optimize the database."""
        if not self._vacuum_db_started:
            self._vacuum_db_started = True
            await asyncio.sleep(60*60)  # Start after 1 hour

        try:
            vacuum_result = await Database.vacuum_report()
            logger.info(vacuum_result)
        except Exception as e:
            logger.error(f"❌ Automatic VACUUM failed: {e}")

    @tasks.loop(minutes=1)
    async def check_mutes(self):
        """Periodically check for expired mutes and unmute users."""
        await self.bot.wait_until_ready()

        for guild in self.bot.guilds:
            guild_id = str(guild.id)
            query_fetch_mutes = '''
                SELECT id, user_id, timestamp, duration FROM moderation 
                WHERE action = 'mute' AND duration IS NOT NULL 
                AND active = 1 AND quashed = 0 AND guild_id = %s
            '''
            mutes = await Database.fetch(query_fetch_mutes, guild_id)
            current_time = datetime.now(timezone.utc)

            for mute in mutes:
                mute_id, user_id, timestamp, duration = mute["id"], mute[
                    "user_id"], mute["timestamp"], mute["duration"]
                mute_start = datetime.fromisoformat(timestamp)
                mute_end = mute_start + timedelta(seconds=duration)

                if current_time >= mute_end:
                    await MuteUtils.process_mute_expiration(guild, mute_id, user_id, guild_id)
