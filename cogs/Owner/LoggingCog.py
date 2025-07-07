import logging
from discord.ext import commands
from discord import app_commands
from util.core import LoggingThreshold
from util.core.startup import DiscordLogHandler

# logging.CRITICAL (50) - only critical errors
# logging.ERROR    (40) - errors and above
# logging.WARNING  (30) - warnings and above
# logging.INFO     (20) - info messages and above
# logging.DEBUG    (10) - debug messages and above
# logging.NOTSET   (0)  - all log messages (default: handle everything)

class LoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="setloglevel", description="Set the bot's logging level")
    @commands.is_owner()
    @app_commands.describe(level="Logging level (NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    async def setloglevel(self, ctx, level: str):
        level = level.upper()
        valid_levels = ["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level not in valid_levels:
            await ctx.send(f"Invalid level. Choose from: {', '.join(valid_levels)}")
            return

        async with self.bot.db.acquire() as conn:
            await LoggingThreshold.set_logging_level(conn, level)

        # Update the in-memory cache if present
        if hasattr(self.bot, "log_level_cache"):
            self.bot.log_level_cache = level

        # Actually update the logger
        logging.getLogger().setLevel(getattr(logging, level))
        await ctx.send(f"Logging level set to {level}.")

    @commands.hybrid_command(name="setlogchannel", description="Set the bot's log channel")
    @commands.is_owner()
    @app_commands.describe(channel="Channel to send logs to")
    async def setlogchannel(self, ctx, channel: commands.TextChannelConverter):
        channel_id = channel.id
        async with self.bot.db.acquire() as conn:
            await LoggingThreshold.set_log_channel(conn, channel_id)
        # Update the in-memory cache if present
        if hasattr(self.bot, "log_channel_cache"):
            self.bot.log_channel_cache = channel_id

        # Remove old DiscordLogHandler(s) and add a new one with the new channel
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            if isinstance(handler, DiscordLogHandler):
                root_logger.removeHandler(handler)
        discord_handler = DiscordLogHandler(self.bot, channel_id)
        discord_handler.setFormatter(logging.Formatter("[%(asctime)s]: %(message)s"))
        root_logger.addHandler(discord_handler)

        await ctx.send(f"Log channel set to {channel.mention} ({channel.id}).")

async def setup(bot):
    await bot.add_cog(LoggingCog(bot))