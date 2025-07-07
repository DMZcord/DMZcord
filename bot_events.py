import logging
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import uuid
from util.core import CommandLogger, MessageLogger, DiscordHelper, NotBotOwnerError
from util.owner import BlacklistUtils, BlacklistQueries
from util.moderation import MuteEventHelper
from util.community import SyncNewMember
from util.setup import WelcomeHandler
from util.core.logger import _discord_log_buffer, _discord_log_lock
from util.core.database import UniqueUser

logger = logging.getLogger(__name__)

# --- In-Memory Spam Detection & Blacklist State ---
_user_command_counts = defaultdict(int)
_currently_blacklisting = set()
_lock = asyncio.Lock()

# --- Command Log State ---
_command_log_cache = []
_command_log_lock = asyncio.Lock()

# --- Background Tasks ---
async def reset_counts_loop(bot):
    while True:
        await asyncio.sleep(60)
        async with _lock:
            _user_command_counts.clear()

async def blacklist_cleanup_loop(bot):
    while True:
        await asyncio.sleep(60)
        try:
            unblacklisted = await BlacklistUtils.cleanup_expired_blacklists(bot)
            for user_id, channel_id, guild_id in unblacklisted:
                target = (
                    f"user {user_id}" if user_id else
                    f"channel {channel_id}" if channel_id else
                    f"guild {guild_id}" if guild_id else "unknown"
                )
                logger.info(f"Auto-unblacklisted expired {target}")
        except Exception as e:
            logger.error(f"Failed to clean up expired blacklists: {e}", exc_info=True)

async def flush_command_logs_loop(bot):
    while True:
        await asyncio.sleep(60)
        try:
            count = len(_command_log_cache)
            if count == 0:
                continue
            await CommandLogger.flush_command_logs(bot, _command_log_cache, _command_log_lock, logger)
            logger.info(
                f"Flushed {count} command log entries - {datetime.now(timezone.utc).isoformat(sep=' ', timespec='seconds')} UTC")
        except Exception as e:
            logger.error(f"Exception in flush_command_logs_loop: {e}", exc_info=True)

async def flush_discord_log_buffer(bot):
    while True:
        await asyncio.sleep(60)
        async with _discord_log_lock:
            if not _discord_log_buffer:
                continue
            # Copy and clear the buffer
            lines = list(_discord_log_buffer)
            _discord_log_buffer.clear()
        # Chunk lines so no message exceeds 1900 chars and no line is split
        chunk = ""
        channel_id = getattr(bot, "log_channel_cache", None)
        if channel_id:
            channel = bot.get_channel(channel_id)
            if channel:
                for line in lines:
                    # +1 for newline
                    if len(chunk) + len(line) + 1 > 1900:
                        await channel.send(f"```{chunk}```")
                        chunk = ""
                    chunk += line + "\n"
                if chunk:
                    await channel.send(f"```{chunk}```")

# --- Command Event Handlers ---

@commands.Cog.listener()
async def on_command(ctx):
    ctx._log_id = uuid.uuid4().hex
    ctx._start_time = datetime.now(timezone.utc)

    # Call the unique user/TOS logic
    await UniqueUser.check_unique_user(ctx)

    # --- Existing logging logic below ---
    channel_name = ctx.channel.name if hasattr(ctx.channel, "name") and ctx.channel.name else "DM"
    async with _command_log_lock:
        _command_log_cache.append((
            ctx._log_id,
            str(ctx.author.id),
            str(ctx.author.name),
            str(ctx.channel.id) if hasattr(ctx.channel, "id") else None,
            channel_name,
            str(ctx.guild.id) if ctx.guild else None,
            ctx.command.qualified_name if ctx.command else "unknown",
            False,
            None,
            None
        ))

    if await ctx.bot.is_owner(ctx.author):
        await CommandLogger(ctx.bot).log_command_start(ctx)
        return

    if isinstance(ctx.channel, discord.DMChannel):
        user_id = str(ctx.author.id)
        is_blacklisted = await BlacklistQueries.check_blacklist(
            user_id=user_id,
            channel_id=None,
            guild_id=None
        )
        if is_blacklisted:
            return

    async with _lock:
        _user_command_counts[ctx.author.id] += 1
        if _user_command_counts[ctx.author.id] >= 6:
            user_id = str(ctx.author.id)
            if user_id in _currently_blacklisting:
                return
            _currently_blacklisting.add(user_id)
            try:
                is_blacklisted = await BlacklistQueries.check_blacklist(
                    user_id=user_id,
                    channel_id=None,
                    guild_id=None
                )
            except Exception as e:
                logger.error(f"Error checking blacklist for user {user_id}: {e}", exc_info=True)
                is_blacklisted = False
            if not is_blacklisted:
                try:
                    async with ctx.bot.db.acquire() as conn:
                        async with conn.cursor() as cursor:
                            await cursor.execute(
                                '''
                                INSERT INTO blacklist (user_id, channel_id, guild_id, added_by, added_at, duration_seconds, expires_at)
                                VALUES (%s, %s, %s, %s, NOW(), %s, DATE_ADD(NOW(), INTERVAL %s SECOND))
                                ON DUPLICATE KEY UPDATE
                                    added_at = NOW(),
                                    duration_seconds = VALUES(duration_seconds),
                                    expires_at = VALUES(expires_at)
                                ''',
                                (
                                    user_id,
                                    None,
                                    None,
                                    str(ctx.bot.user.id),
                                    600,
                                    600
                                )
                            )
                        await conn.commit()
                    logger.info(f"User {ctx.author.id} blacklisted for command spam.")
                    owner = (await ctx.bot.application_info()).owner
                    channel_id = str(ctx.channel.id)
                    recent_commands = []
                    for entry in reversed(_command_log_cache):
                        if entry[1] == user_id and entry[3] == channel_id:
                            checkmark = "✅" if entry[7] else "❌"
                            recent_commands.append(
                                f"{checkmark} `{entry[6]}` at {entry[4]}"
                            )
                        if len(recent_commands) >= 10:
                            break
                    recent_commands.reverse()
                    summary = "\n".join(recent_commands) if recent_commands else "No recent commands found."
                    alert_message = (
                        f"🚨 **User {ctx.author} (`{ctx.author.id}`) was auto-blacklisted for command spam**\n"
                        f"**Recent commands in this channel:**\n{summary}"
                    )
                    if owner:
                        try:
                            await owner.send(alert_message)
                        except Exception as e:
                            logger.error(f"Failed to DM bot owner about auto-blacklist: {e}", exc_info=True)
                    await asyncio.sleep(10)
                    now = datetime.now(timezone.utc)
                    cutoff = now - timedelta(seconds=40)
                    try:
                        messages = [m async for m in ctx.channel.history(limit=100)]
                        bot_messages = [
                            m for m in messages
                            if m.author.id == ctx.bot.user.id and m.created_at >= cutoff
                        ]
                        if bot_messages:
                            await ctx.channel.delete_messages(bot_messages)
                            logger.info(f"Deleted {len(bot_messages)} bot messages in {ctx.channel.name} due to spam.")
                    except discord.Forbidden:
                        pass
                    except Exception as e:
                        logger.error(f"Failed to delete bot messages: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Failed to add user to blacklist: {e}", exc_info=True)
            return

    await CommandLogger(ctx.bot).log_command_start(ctx)

@commands.Cog.listener()
async def on_command_completion(ctx):
    end_time = datetime.now(timezone.utc)
    start_time = getattr(ctx, "_start_time", end_time)
    if isinstance(start_time, float):
        start_time = datetime.fromtimestamp(start_time, tz=timezone.utc)
    if isinstance(end_time, float):
        end_time = datetime.fromtimestamp(end_time, tz=timezone.utc)
    response_time = (end_time - start_time).total_seconds()
    log_id = getattr(ctx, "_log_id", None)
    if log_id is None:
        return
    async with _command_log_lock:
        found = False
        for entry in reversed(_command_log_cache):
            if entry[0] == log_id:
                updated_entry = list(entry)
                updated_entry[7] = True
                updated_entry[9] = response_time
                _command_log_cache[_command_log_cache.index(entry)] = tuple(updated_entry)
                found = True
                break
    if not found:
        async with ctx.bot.db.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    '''
                    UPDATE command_logs
                    SET success=%s, error=%s, response_time=%s
                    WHERE log_id=%s
                    ''',
                    (True, None, response_time, log_id)
                )
            await conn.commit()
    await CommandLogger(ctx.bot).log_command_completion(ctx)

@commands.Cog.listener()
async def on_command_error(ctx, error):
    error_messages = {
        commands.MissingPermissions: "❌ You don't have permission to use this command.",
        commands.MissingRequiredArgument: lambda e: f"❌ Missing required argument: `{e.param.name}`. Please check the command usage.",
        commands.CommandNotFound: None,  # Silently ignore unknown commands
        commands.BadArgument: "❌ Invalid argument provided. Please check your input.",
        commands.MemberNotFound: "❌ Member not found. Please provide a valid user ID or mention.",
        NotBotOwnerError: "❌ You do not have permission to use this command. (Bot owner only)",
        commands.CommandOnCooldown: "⏳ This command is on cooldown. Please try again later.",
    }

    for exc_type, message in error_messages.items():
        if isinstance(error, exc_type):
            if message is None:
                return  # Silently ignore
            if callable(message):
                await ctx.send(message(error), delete_after=5)
            else:
                await ctx.send(message, delete_after=5)
            return

    if isinstance(error, commands.CheckFailure):
        user_id = str(ctx.author.id)
        channel_id = str(ctx.channel.id) if hasattr(ctx.channel, "id") else None
        guild_id = str(ctx.guild.id) if ctx.guild else None
        is_blacklisted = await BlacklistQueries.check_blacklist(
            user_id=user_id,
            channel_id=channel_id,
            guild_id=guild_id
        )
        if is_blacklisted:
            # Determine what is blacklisted
            reason = []
            if await BlacklistQueries.check_blacklist(user_id=user_id, channel_id=None, guild_id=None):
                reason.append(f"user {ctx.author} ({user_id})")
            if channel_id and await BlacklistQueries.check_blacklist(user_id=None, channel_id=channel_id, guild_id=None):
                reason.append(f"channel {ctx.channel} ({channel_id})")
            if guild_id and await BlacklistQueries.check_blacklist(user_id=None, channel_id=None, guild_id=guild_id):
                reason.append(f"guild {ctx.guild} ({guild_id})")
            logger.info(f"Blacklisted {' and '.join(reason)} attempted to use a command: {ctx.command}")
            return  # Do not send any message to the user
        else:
            await ctx.send("❌ You do not meet the requirements to use this command.", delete_after=5)
        return

    logger.error(f"Unhandled error in command by {ctx.author}: {error}", exc_info=True)
    await ctx.send(f"An unexpected error occurred: {error}", delete_after=10)

# --- App Command (Slash Command) Event Handlers ---

@commands.Cog.listener()
async def on_app_command_error(interaction: discord.Interaction, error):
    error_messages = {
        app_commands.MissingPermissions: "You don't have permission to use this slash command.",
        app_commands.MissingRole: "You are missing a required role to use this slash command.",
        app_commands.CommandNotFound: "This slash command does not exist.",
        app_commands.CheckFailure: "You do not meet the requirements to use this slash command.",
        app_commands.CommandOnCooldown: "This command is on cooldown. Please try again later.",
        app_commands.BotMissingPermissions: "I don't have the required permissions to execute this command."
    }

    # Handle CheckFailure: check if user is blacklisted, if so, stay silent
    if isinstance(error, app_commands.CheckFailure):
        user_id = str(interaction.user.id)
        channel_id = str(interaction.channel.id) if interaction.channel else None
        guild_id = str(interaction.guild.id) if interaction.guild else None
        is_blacklisted = await BlacklistQueries.check_blacklist(
            user_id=user_id,
            channel_id=channel_id,
            guild_id=guild_id
        )
        if is_blacklisted:
            logger.info(f"Blacklisted user {interaction.user} ({interaction.user.id}) attempted to use a slash command: {getattr(interaction.command, 'qualified_name', 'unknown')}")
            return  # Do not send any message to the user

    message = error_messages.get(type(error), f"An error occurred: {error}")
    await DiscordHelper.respond(interaction, message, ephemeral=True)
    if type(error) not in error_messages:
        logger.error(f"Unhandled error in slash command by {interaction.user}: {error}", exc_info=True)
    else:
        logger.warning(f"{type(error).__name__}: {interaction.user} tried to use a slash command")

@commands.Cog.listener()
async def on_app_command_completion(interaction, command):
    user = interaction.user
    channel = interaction.channel
    guild = interaction.guild
    log_id = uuid.uuid4().hex
    channel_name = getattr(channel, "name", "DM")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    async with _command_log_lock:
        _command_log_cache.append((
            log_id,
            str(user.id),
            str(user.name),
            str(channel.id) if hasattr(channel, "id") else None,
            channel_name,
            timestamp,
            str(guild.id) if guild else None,
            command.qualified_name if hasattr(command, "qualified_name") else str(command),
            True,
            None,
            0
        ))

# --- Member Event Handlers ---

@commands.Cog.listener()
async def on_member_remove(member: discord.Member):
    logger.info(f"Member {member.id} left the server.")

@commands.Cog.listener()
async def on_member_join(member: discord.Member):
    try:
        await MuteEventHelper.handle_mute_reapplication(member.guild._state._get_bot(), member)
        await WelcomeHandler.send_welcome_message(member.guild._state._get_bot(), member)
        await SyncNewMember.sync_community_loadouts(member)
    except Exception as e:
        logger.error(f"Error in on_member_join for user {member.id}: {e}", exc_info=True)

# --- Message Event Handlers ---

@commands.Cog.listener()
async def on_message(message: discord.Message):
    if message.author.bot:
        return

@commands.Cog.listener()
async def on_message_delete(message):
    await MessageLogger.log_deleted_message(message)

@commands.Cog.listener()
async def on_message_edit(before, after):
    await MessageLogger.log_edited_message(before, after)

# --- Registration helper ---

def setup_event_handlers(bot):
    """Register event listeners and log registration"""
    listeners = [
        ("on_command", on_command),
        ("on_command_completion", on_command_completion),
        ("on_command_error", on_command_error),
        ("on_app_command_error", on_app_command_error),
        ("on_app_command_completion", on_app_command_completion),
        ("on_member_remove", on_member_remove),
        ("on_member_join", on_member_join),
        ("on_message", on_message),
        ("on_message_delete", on_message_delete),
        ("on_message_edit", on_message_edit)
    ]
    
    registered_events = []
    for name, handler in listeners:
        bot.add_listener(handler)
        registered_events.append(f"  [OK]   {name}")
    
    # Add to bot's startup log
    bot.startup_log_lines.append(
        "Registered Event Handlers:\n" + 
        "\n".join(registered_events) + "\n" + "="*40
    )

def start_background_tasks(bot):
    """Start background tasks and log startup"""
    tasks = [
        ("reset_counts_loop", reset_counts_loop),
        ("blacklist_cleanup_loop", blacklist_cleanup_loop),
        ("flush_command_logs_loop", flush_command_logs_loop),
        ("flush_discord_log_buffer", flush_discord_log_buffer)
    ]
    
    started_tasks = []
    for name, task_func in tasks:
        bot.loop.create_task(task_func(bot))
        started_tasks.append(f"  [OK]   {name}")
    
    # Add to bot's startup log
    bot.startup_log_lines.append(
        "Started Background Tasks:\n" + 
        "\n".join(started_tasks) + "\n" + "="*40
    )
