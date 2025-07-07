import logging
from datetime import datetime
from util.core.constants import TimezoneMap
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from pytz import timezone as ZoneInfo  # fallback for older Python

logger = logging.getLogger(__name__)

class TimeUtils:
    @staticmethod
    def convert_timestamp(iso_timestamp: str, timezone_name: str = "UTC") -> str:
        """Converts ISO 8601 timestamp to formatted string in the given timezone."""
        converted_timezone = TimezoneMap.get(timezone_name.upper(), timezone_name)
        try:
            dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
            dt_tz = dt.astimezone(ZoneInfo(converted_timezone))
            return dt_tz.strftime("%Y-%m-%d %I:%M:%S %p %Z")
        except Exception as e:
            logger.error(
                f"Error converting '{iso_timestamp}' to timezone '{timezone_name}': {e}", exc_info=True)
            return "Invalid timestamp"

    @staticmethod
    def format_mmss(seconds):
        """Format seconds to MM:SS format."""
        if seconds is None:
            return "Unknown"
        minutes, seconds = divmod(int(seconds), 60)
        return f"{minutes}:{seconds:02d}"

    @staticmethod
    def format_timestamp(iso_timestamp: str) -> str:
        """Format ISO 8601 timestamp to a readable string."""
        try:
            # Handles both with and without timezone info
            if iso_timestamp.endswith("Z"):
                iso_timestamp = iso_timestamp[:-1] + "+00:00"
            dt = datetime.fromisoformat(iso_timestamp)
            return dt.strftime("%d-%m-%Y %H:%M:%S")
        except Exception:
            logger.error(f"Invalid timestamp format: {iso_timestamp}", exc_info=True)
            return "Invalid timestamp"

class TableUtils:
    @staticmethod
    def format_table(rows: list) -> str:
        """ Formats a list of rows as a monospaced table with aligned columns."""
        if not rows:
            logger.debug("No rows provided to format_table.")
            return ""
        col_widths = [max(len(str(item)) for item in col) for col in zip(*rows)]
        lines = []
        for row in rows:
            line = "  ".join(str(item).ljust(width)
                             for item, width in zip(row, col_widths))
            lines.append(line)
        return "```\n" + "\n".join(lines) + "\n```"

class StringUtils:
    @staticmethod
    def truncate(text, max_len):
        """Truncate text to max_len, adding ellipsis if needed."""
        if len(text) > max_len:
            logger.debug(f"Truncated text '{text}' to max_len {max_len}")
            return (text[:max_len] + "...")
        return text

class MockContext:
    """Mock context for permission checking."""
    def __init__(self, user, guild, bot):
        self.author = user
        self.guild = guild
        self.bot = bot
        self.channel = None
        self.me = bot.user if hasattr(bot, 'user') else None
        self.interaction = None
        self.command = None
        self.invoked_with = None
        self.prefix = "!"
        self.valid = True

class DiscordHelper:
    @staticmethod
    async def respond(target, message, ephemeral=False, **kwargs):
        """
        Respond to an interaction or send a message in a context/channel.
        """
        if hasattr(target, "response") and hasattr(target.response, "is_done"):
            # It's likely a discord.Interaction
            try:
                if not target.response.is_done():
                    await target.response.send_message(message, ephemeral=ephemeral, **kwargs)
                else:
                    await target.followup.send(message, ephemeral=ephemeral, **kwargs)
            except Exception:
                # fallback to channel send if interaction fails
                if hasattr(target, "channel"):
                    await target.channel.send(message, **kwargs)
        elif hasattr(target, "send"):
            # It's a context or channel
            await target.send(message, **kwargs)
        else:
            raise ValueError("Target does not support sending messages.")

class SizeUtils:
    @staticmethod
    def format_size(num):
        """Convert bytes to human readable format."""
        num = float(num)
        for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
            if num < 1024.0:
                return f"{num:.2f} {unit}"
            num /= 1024.0
        return f"{num:.2f} PB"