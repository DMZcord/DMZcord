import asyncio
import time
import logging
from datetime import datetime, timezone
from .database import Database

logger = logging.getLogger(__name__)

class CommandLogger:
    def __init__(self, bot, flush_interval=5):
        self.bot = bot
        self.command_log_buffer = []
        self.flush_interval = flush_interval
        self.flush_task = None

    def start(self):
        """Start the periodic flush task."""
        if not self.flush_task:
            self.flush_task = self.bot.loop.create_task(
                self.flush_command_logs_periodically())

    def stop(self):
        """Stop the periodic flush task and flush remaining logs."""
        if self.flush_task:
            self.flush_task.cancel()

        # Flush any remaining logs
        if self.command_log_buffer:
            query = '''
                INSERT INTO command_logs (user_id, guild_id, command_name, start_time, end_time, response_time) 
                VALUES (%s, %s, %s, %s, %s, %s)
            '''
            for log_entry in self.command_log_buffer:
                asyncio.run(Database.execute(query, *log_entry))
            self.command_log_buffer.clear()

    async def log_command_start(self, ctx):
        """Log when a command starts."""
        user_id = str(ctx.author.id)
        now = time.time()

        # Check if user is blocked due to abuse
        query = "SELECT block_until FROM abuse WHERE user_id = %s"
        row = await Database.fetchrow(query, user_id)
        if row and now < row["block_until"]:
            return False  # Block the command

        ctx._start_time = time.time()
        return True  # Allow the command

    async def log_command_completion(self, ctx):
        """Log when a command completes."""
        end_time = datetime.now(timezone.utc)
        start_time = getattr(ctx, "_start_time", end_time)
        # Convert float to datetime if needed
        if isinstance(start_time, float):
            start_time = datetime.fromtimestamp(start_time, tz=timezone.utc)
        if isinstance(end_time, float):
            end_time = datetime.fromtimestamp(end_time, tz=timezone.utc)
        response_time = (end_time - start_time).total_seconds()
        command_name = ctx.command.qualified_name if ctx.command else "unknown"
        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id) if ctx.guild else None

        self.command_log_buffer.append(
            (user_id, guild_id, command_name, start_time, end_time, response_time))

    async def flush_command_logs_periodically(self):
        """Flush command logs to the database periodically."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            await asyncio.sleep(self.flush_interval)
            if self.command_log_buffer:
                buffer_copy = self.command_log_buffer[:]
                self.command_log_buffer.clear()
                query = '''
                    INSERT INTO command_logs (user_id, guild_id, command_name, start_time, end_time, response_time) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                '''
                for log_entry in buffer_copy:
                    await Database.execute(query, *log_entry)

    async def flush_command_logs(bot, command_log_cache, command_log_lock, logger):
        start = time.perf_counter()
        async with command_log_lock:
            if not command_log_cache:
                return
            entries = command_log_cache[:]
            command_log_cache.clear()
        try:
            async with bot.db.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.executemany('''
                        INSERT INTO command_logs (
                        log_id, user_id, username, channel_id, channel_name, guild_id,
                        command_name, success, error, response_time, timestamp
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ''', entries)
            await conn.commit()
        except Exception as e:
            logger.error(f"Failed to flush command logs: {e}", exc_info=True)
        finally:
            elapsed = time.perf_counter() - start
        logger.info(f"Command log flush took {elapsed:.2f} seconds")

_discord_log_buffer = []
_discord_log_lock = asyncio.Lock()