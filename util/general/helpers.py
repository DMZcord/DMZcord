import asyncio
import inspect
import re
import discord
from datetime import datetime
import logging
from typing import List, Tuple, Optional, Union

logger = logging.getLogger(__name__)

class GeneralHelpers:
    @staticmethod
    async def safely_delete_message(ctx, is_slash, timeout=120):
        """
        Safely deletes the help message after a timeout.
        Works for both context and slash command interactions.
        """
        try:
            if is_slash and hasattr(ctx, "interaction"):
                message = await ctx.interaction.original_response()
                await message.delete(delay=timeout)
            else:
                # For regular commands, delete the last sent message after timeout
                async for msg in ctx.channel.history(limit=1, after=ctx.message):
                    await msg.delete(delay=timeout)
        except Exception:
            pass  # Ignore errors (e.g., message already deleted)

    @staticmethod
    async def delete_after_timeout(ctx, message, timeout=120):
        """
        Deletes a message after a timeout.
        Works for both context and slash command messages.
        """
        try:
            await asyncio.sleep(timeout)
            await message.delete()
        except Exception:
            pass  # Ignore if message already deleted or missing permissions

    @staticmethod
    def get_command_arguments(command):
        params = list(command.clean_params.values())
        arg_lines = []
        for param in params:
            if param.name in ("self", "ctx"):
                continue
            required = param.default is inspect.Parameter.empty
            annotation = (
                param.annotation.__name__ if hasattr(param.annotation, "__name__")
                else str(param.annotation)
            ) if param.annotation != inspect.Parameter.empty else "str"
            if required:
                arg_lines.append(f"<{param.name}: {annotation}>")
            else:
                arg_lines.append(f"[{param.name}: {annotation} = {param.default}]")
        return " ".join(arg_lines) if arg_lines else "No arguments."

    @staticmethod
    async def filter_help_commands(cmd, ctx, bot):
        """Return True if the command should be visible to the user in help."""
        try:
            # Owner-only check
            is_owner = await bot.is_owner(ctx.author if hasattr(ctx, "author") else ctx.user)
            is_owner_only = any(getattr(check, "__qualname__", "").startswith("is_owner") for check in getattr(cmd, "checks", []))
            if is_owner_only and not is_owner:
                return False
            # Permission and all other checks
            return await cmd.can_run(ctx)
        except Exception:
            return False


class MessageHelper:
    """Helper functions for message manipulation and formatting"""

    @staticmethod
    async def log_deleted_message(msg: discord.Message) -> str:
        """Create a log entry for a deleted message"""
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] {msg.author} ({msg.author.id}): {msg.content}"

    @staticmethod
    async def create_message_log_file(log_entries: List[str], actor: Union[discord.User, discord.Member], channel: discord.TextChannel) -> discord.File:
        """Create a file object containing deleted message logs"""
        import io
        from util.core import TimeUtils

        output = io.StringIO()
        output.write(
            f"Command run by {actor} ({actor.id}) at {TimeUtils.convert_timestamp(datetime.now().isoformat(), 'PST')}\n")
        output.write(f"In channel: #{channel} (ID: {channel.id})\n\n")
        output.write("\n".join(reversed(log_entries)))
        output.seek(0)

        return discord.File(fp=output, filename="deleted_messages_log.txt")

    @staticmethod
    async def get_or_create_log_channel(guild: discord.Guild) -> discord.TextChannel:
        """Get or create the message logs channel in Modmail category"""
        modmail_category = discord.utils.get(guild.categories, name="Modmail")
        if not modmail_category:
            modmail_category = await guild.create_category("Modmail")

        log_channel = discord.utils.get(
            modmail_category.text_channels, name="message-logs")
        if not log_channel:
            log_channel = await guild.create_text_channel("message-logs", category=modmail_category)

        return log_channel

    @staticmethod
    def format_custom_emojis(text: str, is_animated: bool = False) -> str:
        """Format emoji IDs in text to Discord emoji format"""
        emoji_ids = re.findall(r'\b\d{17,19}\b(?![^<]*>)', text)
        formatted_message = text

        for emoji_id in emoji_ids:
            emoji_name = "customemoji"
            emoji_format = f"<a:{emoji_name}:{emoji_id}>" if is_animated else f"<:{emoji_name}:{emoji_id}>"
            formatted_message = re.sub(
                r'\b' + emoji_id + r'\b(?![^<]*>)', emoji_format, formatted_message)

        return formatted_message

    @staticmethod
    def parse_echo_command(text: str) -> Tuple[str, bool]:
        """Parse echo command text and animated flag"""
        parts = text.split()
        is_animated = False
        message_text = text

        if parts and parts[-1].lower() in ["yes", "no"]:
            animated_flag = parts[-1].lower()
            is_animated = animated_flag == "yes"
            message_text = " ".join(parts[:-1])

        return message_text, is_animated


class ClearHelper:
    """Helper functions for message clearing operations"""
    
    @staticmethod
    async def batch_purge(channel, total_count):
        deleted = []
        to_delete = total_count
        while to_delete > 0:
            batch_size = min(100, to_delete)
            batch = await channel.purge(limit=batch_size)
            if not batch:
                break
            deleted.extend(batch)
            to_delete -= len(batch)
            if to_delete > 0:
                await asyncio.sleep(2)  # Wait 2 seconds between batches to avoid rate limits
        return deleted


class EchoHelper:
    """Helper functions for echo command"""

    @staticmethod
    async def validate_echo_permissions(channel: discord.TextChannel, bot_member: discord.Member, guild: discord.Guild) -> Tuple[bool, Optional[str]]:
        """Validate permissions for echo command"""
        if channel.guild.id != guild.id:
            return False, "Error: Channel not found in this server. Please select a channel from this server."

        if not channel.permissions_for(bot_member).send_messages:
            return False, "Error: I don't have permission to send messages in that channel."

        return True, None

    @staticmethod
    async def send_echo_message(channel: discord.TextChannel, text: str, animated: bool = False) -> None:
        """Send formatted echo message to channel"""
        formatted_message = MessageHelper.format_custom_emojis(text, animated)
        await channel.send(formatted_message)


