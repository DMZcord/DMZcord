import os
import logging
import asyncio
import discord

from util.owner import BlacklistQueries
from util.core.logger import _discord_log_buffer, _discord_log_lock

class Startup:
    @staticmethod
    def find_cogs(base_dir="cogs"):
        cogs = []
        for root, dirs, files in os.walk(base_dir):
            if "WIP" in root.split(os.sep):
                continue
            for file in files:
                if file.endswith("Cog.py"):
                    rel_path = os.path.relpath(os.path.join(root, file), base_dir)
                    module = rel_path.replace(os.sep, ".")[:-3]
                    cogs.append(f"{base_dir}.{module}")
        return cogs

    @staticmethod
    async def global_blacklist_check(ctx):
        user_id = str(ctx.author.id)
        channel_id = str(ctx.channel.id) if hasattr(ctx.channel, "id") else None
        guild_id = str(ctx.guild.id) if ctx.guild else None
        if await BlacklistQueries.check_blacklist(user_id=user_id, channel_id=channel_id, guild_id=guild_id):
            return False
        return True
    
    @staticmethod
    async def load_logging_settings(bot):
        async with bot.db.acquire() as conn:
            level = await LoggingThreshold.get_logging_level(conn)
            if not level:
                level = "INFO"
            bot.log_level_cache = level
            logging.getLogger().setLevel(getattr(logging, level))

            log_channel = await LoggingThreshold.get_log_channel(conn)
            bot.log_channel_cache = int(log_channel) if log_channel else None

class DiscordLogHandler(logging.Handler):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def emit(self, record):
        log_entry = self.format(record)
        # Buffer the log instead of sending immediately
        asyncio.create_task(self.buffer_log(log_entry))

    async def buffer_log(self, log_entry):
        async with _discord_log_lock:
            _discord_log_buffer.append(log_entry)

class DMZcordLogger:
    def __init__(self, level=logging.INFO, format_str="[%(asctime)s]: %(message)s"):
        self.level = level
        self.format_str = format_str
        self.formatter = logging.Formatter(self.format_str)

    def filter(self, record):
        msg = record.getMessage()
        return bool(msg and msg.strip())

    def setup(self):
        # Ensure root logger has a StreamHandler for the console
        root_logger = logging.getLogger()
        root_logger.setLevel(self.level)
        if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
            handler = logging.StreamHandler()
            handler.setFormatter(self.formatter)
            handler.addFilter(self.filter)
            root_logger.addHandler(handler)
        else:
            for handler in root_logger.handlers:
                handler.setFormatter(self.formatter)
                handler.addFilter(self.filter)

        # Ensure propagate=True for all loggers
        for logger_name in logging.root.manager.loggerDict:
            logger_obj = logging.getLogger(logger_name)
            logger_obj.propagate = True

        # Also apply formatter and filter to discord loggers if they have handlers
        for logger_name in ("discord", "discord.client", "discord.gateway"):
            logger_obj = logging.getLogger(logger_name)
            for handler in logger_obj.handlers:
                handler.setFormatter(self.formatter)
                handler.addFilter(self.filter)
            logger_obj.propagate = True
                
class LoggingThreshold:
    @staticmethod
    async def get_logging_level(conn):
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT value FROM logging WHERE `key` = 'logging_level'")
            row = await cursor.fetchone()
            return row[0] if row else "INFO"

    @staticmethod
    async def set_logging_level(conn, level):
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO logging (`key`, value) VALUES ('logging_level', %s) "
                "ON DUPLICATE KEY UPDATE value = VALUES(value)",
                (level,)
            )
        await conn.commit()

    @staticmethod
    async def get_log_channel(conn):
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT log_channel FROM logging WHERE `key` = 'logging_level'")
            row = await cursor.fetchone()
            return row[0] if row else "1386083199431475250"

    @staticmethod
    async def set_log_channel(conn, channel_id):
        async with conn.cursor() as cursor:
            await cursor.execute(
                "UPDATE logging SET log_channel = %s WHERE `key` = 'logging_level'",
                (str(channel_id),)
            )
        await conn.commit()

class MessageLogger:
    @staticmethod
    async def log_deleted_message(message):
        """Log deleted messages."""
        if message.author.bot or not message.guild:
            return

        category = discord.utils.get(message.guild.categories, name="Modmail")
        if not category:
            return

        log_channel = discord.utils.get(category.channels, name="message-logs")
        if not log_channel:
            return

        content = message.content or "[No content]"
        channel = f"#{message.channel}" if hasattr(
            message.channel, "name") else str(message.channel.id)

        embed = discord.Embed(
            title="Message Deleted",
            description=f"**Channel:** {channel}\n**Content:**\n{content}",
            color=discord.Color.red()
        )
        embed.set_author(name=f"{message.author} | ID: {message.author.id}",
                         icon_url=message.author.display_avatar.url)
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.timestamp = message.created_at

        await log_channel.send(embed=embed)

    @staticmethod
    async def log_edited_message(before, after):
        """Log edited messages."""
        if before.author.bot or not before.guild or before.content == after.content:
            return

        category = discord.utils.get(before.guild.categories, name="Modmail")
        if not category:
            return

        log_channel = discord.utils.get(category.channels, name="message-logs")
        if not log_channel:
            return

        channel = f"#{before.channel}" if hasattr(
            before.channel, "name") else str(before.channel.id)
        message_link = f"https://discord.com/channels/{before.guild.id}/{before.channel.id}/{before.id}"

        embed = discord.Embed(
            title="Message Edited",
            description=f"**Channel:** {channel}\n[Jump to message]({message_link})",
            color=discord.Color.orange()
        )
        embed.set_author(name=f"{before.author} | ID: {before.author.id}",
                         icon_url=before.author.display_avatar.url)
        embed.set_thumbnail(url=before.author.display_avatar.url)

        max_field_length = 1024
        before_content = (before.content or "[No content]")[:max_field_length]
        after_content = (after.content or "[No content]")[:max_field_length]

        embed.add_field(name="Before", value=before_content, inline=False)
        embed.add_field(name="After", value=after_content, inline=False)
        embed.timestamp = before.edited_at or before.created_at

        await log_channel.send(embed=embed)
