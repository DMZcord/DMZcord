import logging
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta
import asyncio
from util.community import LoadoutCacheHelper
from util.core import DiscordHelper
from util.general import MessageHelper, EchoHelper, UncacheViews, ClearEmbed, OldMessageConfirmView, ConfirmDeleteView

logger = logging.getLogger(__name__)

class UtilCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="clear", description="Clear messages by count or after a message ID")
    @app_commands.describe(arg="Number of messages or message ID")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, arg: str):
        send = lambda msg, **kwargs: DiscordHelper.respond(ctx, msg, **kwargs)
        is_slash = isinstance(ctx, discord.Interaction)
        log_entries = []

        try:
            # Determine messages to delete (preserve your logic)
            if arg.isdigit() and 1 <= int(arg) <= 1000:
                count = int(arg)
                messages = [m async for m in ctx.channel.history(limit=count+1)]
            elif 17 <= len(arg) <= 19 and arg.isdigit():
                message_id = int(arg)
                target_message = await ctx.channel.fetch_message(message_id)
                messages = [m async for m in ctx.channel.history(after=target_message, limit=1000)]
            else:
                try:
                    message_id = int(arg)
                    target_message = await ctx.channel.fetch_message(message_id)
                    messages = [m async for m in ctx.channel.history(after=target_message, limit=1000)]
                except Exception:
                    raise ValueError("Please enter a valid number of messages (1-1000) or a message ID.")

            if not messages:
                await send("No messages found to delete.")
                return

            now = datetime.now(timezone.utc)
            old_msgs = [m for m in messages if (now - m.created_at) >= timedelta(days=14)]
            new_msgs = [m for m in messages if (now - m.created_at) < timedelta(days=14)]

            # Always prompt for confirmation
            if old_msgs:
                num_old = len(old_msgs)
                batches_old = (num_old + 4) // 5 if num_old else 0
                est_time_old = int(num_old * 0.3 + (batches_old - 1) * 2 if batches_old > 1 else 0)
                batches_new = (len(new_msgs) + 99) // 100 if new_msgs else 0
                est_time_new = (batches_new - 1) * 2 if batches_new > 1 else 0
                est_time = est_time_old + est_time_new
                embed = ClearEmbed.build_old_message_confirm_embed(len(old_msgs + new_msgs), len(old_msgs), est_time)
                view = OldMessageConfirmView(est_time, ctx.author)
            else:
                batches = (len(new_msgs) + 99) // 100 if new_msgs else 0
                est_time = (batches - 1) * 2 if batches > 1 else 0
                embed = ClearEmbed.build_confirm_embed(len(messages), est_time)
                view = ConfirmDeleteView(ctx.author)

            if is_slash:
                await ctx.interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                view.message = await ctx.interaction.original_response()
            else:
                sent = await ctx.send(embed=embed, view=view)
                view.message = sent

            await view.wait()
            if not view.value:
                if is_slash:
                    await ctx.interaction.edit_original_response(content="Cancelled message deletion.", embed=None, view=None)
                else:
                    if hasattr(view, "message") and view.message:
                        await view.message.edit(content="Cancelled message deletion.", embed=None, view=None)
                    else:
                        await send("Cancelled message deletion.")
                return

            # Log all messages to log_entries BEFORE deletion
            for msg in messages:
                try:
                    log_entry = await MessageHelper.log_deleted_message(msg)
                    if log_entry:
                        log_entries.append(log_entry)
                except Exception as e:
                    logger.warning(f"Failed to log message {getattr(msg, 'id', None)}: {e}")

            # Delete new messages in batches of 100
            deleted = []
            if new_msgs:
                for i in range(0, len(new_msgs), 100):
                    batch = new_msgs[i:i+100]
                    purged = await ctx.channel.delete_messages(batch)
                    if purged:
                        deleted.extend(purged)
                    if i + 100 < len(new_msgs):
                        await asyncio.sleep(2)

            # Delete old messages in batches of 5
            if old_msgs:
                for i in range(0, len(old_msgs), 5):
                    batch = old_msgs[i:i+5]
                    for msg in batch:
                        try:
                            await msg.delete()
                            deleted.append(msg)
                            await asyncio.sleep(0.3)
                        except discord.HTTPException as e:
                            if e.status == 429 and hasattr(e, "retry_after"):
                                await asyncio.sleep(e.retry_after)
                            else:
                                pass
                    if i + 5 < len(old_msgs):
                        await asyncio.sleep(2)

            # Send log to message-logs channel if any entries exist
            if log_entries:
                log_channel = await MessageHelper.get_or_create_log_channel(ctx.guild)
                actor = getattr(ctx, "author", None) or getattr(ctx, "user", None)
                log_file = await MessageHelper.create_message_log_file(log_entries, actor, ctx.channel)
                await log_channel.send(file=log_file)

            # Success message
            success_message = f"✅ Deleted {len(log_entries)} messages."
            if is_slash:
                await ctx.interaction.edit_original_response(content=success_message, embed=None, view=None)
            else:
                if hasattr(view, "message") and view.message:
                    await view.message.edit(content=success_message, embed=None, view=None)
                else:
                    await send(success_message, delete_after=5)
        except ValueError as e:
            error_msg = "❌ Please enter a valid number of messages (1-1000) or a message ID."
            if is_slash:
                await send(error_msg)
            else:
                await send(error_msg, delete_after=5)
        except discord.NotFound:
            error_msg = "❌ Message ID not found in this channel."
            if is_slash:
                await send(error_msg)
            else:
                await send(error_msg, delete_after=5)
        except discord.Forbidden:
            error_msg = "❌ I do not have permission to delete messages."
            if is_slash:
                await send(error_msg)
            else:
                await send(error_msg, delete_after=5)
        except discord.HTTPException as e:
            error_msg = f"❌ Failed to delete messages: {e}"
            if is_slash:
                await send(error_msg)
            else:
                await send(error_msg, delete_after=5)

    @commands.hybrid_command(name="echo", description="Repeat your message in a specified channel")
    @app_commands.describe(
        channel="Channel to send the message in",
        text="Text with emoji IDs and optional [animated:yes/no]"
    )
    @commands.has_permissions(manage_messages=True)
    async def echo(self, ctx: commands.Context, channel: discord.TextChannel, *, text: str):
        """Repeat your message in a channel with custom emojis (hybrid command)."""
        send = lambda msg: DiscordHelper.respond(ctx, msg)
        actor = getattr(ctx, "author", None) or getattr(ctx, "user", None)

        try:
            # Validate permissions
            valid, error_msg = await EchoHelper.validate_echo_permissions(
                channel, ctx.guild.me, ctx.guild
            )
            if not valid:
                await send(error_msg)
                return

            # Parse command and send message
            message_text, is_animated = MessageHelper.parse_echo_command(text)
            await EchoHelper.send_echo_message(channel, message_text, is_animated)
            
            await send(f"Message sent to {channel.mention}!")
            logger.info(f"Echoed message to channel {channel.id} in guild {ctx.guild.id} by {actor}")

        except Exception as e:
            await send(f"An error occurred: {str(e)}")
            logger.error(f"Error in echo command: {e}")

    @commands.hybrid_command(name="uncache", description="Remove cached Wzhub.gg loadouts for yourself.")
    @app_commands.describe(username="Username to uncache (bot owner only)")
    async def uncache(self, ctx: commands.Context, username: str = None):
        """Remove cached wzhub.gg loadouts for yourself or a username (hybrid command)."""
        # Determine target username
        if username is None:
            async with self.bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT wzhub_username FROM user_sync WHERE discord_id = %s", 
                        (str(ctx.author.id),)
                    )
                    row = await cur.fetchone()
            target_username = row[0] if row else ctx.author.name.lower()
        else:
            if not await self.bot.is_owner(ctx.author):
                await DiscordHelper.respond(
                    ctx, 
                    "Only the bot owner can uncache by username. Use `/uncache` or `!uncache` to remove your own cached loadouts."
                )
                return
            target_username = username.lower()

        # Get loadout data
        guild_row, global_rows = await LoadoutCacheHelper.get_user_loadouts(
            self.bot, target_username, str(ctx.guild.id)
        )
        
        # Count loadouts by source
        guild_counts, global_counts = LoadoutCacheHelper.count_loadouts_by_source(
            guild_row, global_rows
        )

        # Create summary embed and view
        embed = LoadoutCacheHelper.create_loadout_summary_embed(
            target_username, ctx.guild.name, guild_counts, global_counts
        )
        
        view = UncacheViews.SourceSelectionView(ctx, target_username, guild_counts, global_counts)
        await DiscordHelper.respond(ctx, "", embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(UtilCog(bot))
