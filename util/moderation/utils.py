import io
import logging
import re
import discord
from util.core import Database
from util.moderation.embeds import SetupEmbed
from typing import Union, List, Tuple

logger = logging.getLogger(__name__)


class IDUtils:
    @staticmethod
    async def generate_unique_id(user_id: str, table: str, action: str = None):
        """
        Generate a unique ID for database records.
        Prefix is based on table name.
        """
        prefix = {"warnings": "W", "mutes": "M",
                  "bans": "B", "moderation": "MOD"}[table]
        last4 = user_id[-4:]
        attempt = 1
        while True:
            try:
                query_count = f"SELECT COUNT(*) AS count FROM {table}"
                row_count = await Database.fetchrow(query_count)
                count = row_count["count"] + attempt
                new_id = f"{prefix}-{last4}-{count:04d}"
                query_check = f"SELECT 1 FROM {table} WHERE id = %s"
                row_check = await Database.fetchrow(query_check, new_id)
                if not row_check:
                    return new_id
            except Exception as e:
                logger.error(f"Error generating unique ID: {e}", exc_info=True)
                return None
            attempt += 1


class DurationUtils:
    @staticmethod
    def parse_duration(duration_str: str) -> int:
        """
        Parse duration string to seconds.
        Accepts '15m', '1h', etc. Max 7 days.
        """
        max_duration = 604800
        match = re.match(r'^(\d+)([mh])$', duration_str.lower())
        if not match:
            logger.warning(f"Invalid duration string: {duration_str}")
            raise ValueError(
                "Duration must be in the format '15m', '45m', '1h', or '24h' (e.g., 15 minutes, 1 hour).")
        value, unit = int(match.group(1)), match.group(2)
        if unit == 'm':
            seconds = value * 60
        elif unit == 'h':
            seconds = value * 3600
        else:
            seconds = 0
        if seconds > max_duration:
            seconds = max_duration
        return seconds


class TicketHelper:
    @staticmethod
    async def create_ticket_category_and_channel(interaction, bot, admin_user, view):
        if interaction.user != admin_user:
            await interaction.response.send_message("Only the admin who started setup can use this.", ephemeral=True)
            return
        await interaction.response.send_message("Enter the category name for the ticket panel:", ephemeral=True)
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        try:
            cat_msg = await bot.wait_for("message", check=check, timeout=60)
            category_name = cat_msg.content.strip()
        except Exception:
            await interaction.followup.send("Timed out waiting for category name.", ephemeral=True)
            return
        await interaction.followup.send("Enter the channel name for the ticket panel channel:", ephemeral=True)
        try:
            chan_msg = await bot.wait_for("message", check=check, timeout=60)
            channel_name = chan_msg.content.strip()
        except Exception:
            await interaction.followup.send("Timed out waiting for channel name.", ephemeral=True)
            return
        guild = interaction.guild
        panel_overwrites = TicketHelper.build_ticket_panel_overwrites(guild)
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name, overwrites=panel_overwrites)
        panel_channel = discord.utils.get(category.channels, name=channel_name)
        if not panel_channel:
            panel_channel = await guild.create_text_channel(channel_name, category=category, overwrites=panel_overwrites)
        view.result_channel = panel_channel
        view.stop()
        await interaction.followup.send(f"Ticket panel channel set to {panel_channel.mention}", ephemeral=True)

    @staticmethod
    async def link_existing_ticket_channel(interaction, bot, admin_user, view):
        if interaction.user != admin_user:
            await interaction.response.send_message("Only the admin who started setup can use this.", ephemeral=True)
            return
        await interaction.response.send_message("Please mention the channel or provide its ID for the ticket panel:", ephemeral=True)
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await bot.wait_for("message", check=check, timeout=60)
            channel = None
            if msg.channel_mentions:
                channel = msg.channel_mentions[0]
            elif msg.content.isdigit():
                channel = interaction.guild.get_channel(int(msg.content))
            if not channel:
                await interaction.followup.send("Invalid channel. Please try setup again.", ephemeral=True)
                return
        except Exception:
            await interaction.followup.send("Timed out waiting for channel mention or ID.", ephemeral=True)
            return
        view.result_channel = channel
        view.stop()
        await interaction.followup.send(f"Ticket panel channel set to {channel.mention}", ephemeral=True)

    @staticmethod
    async def create_log_category_and_channel(interaction, bot, admin_user, view):
        if interaction.user != admin_user:
            await interaction.response.send_message("Only the admin who started setup can use this.", ephemeral=True)
            return
        await interaction.response.send_message("Enter the category name for modmail logs:", ephemeral=True)
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        try:
            cat_msg = await bot.wait_for("message", check=check, timeout=60)
            category_name = cat_msg.content.strip()
        except Exception:
            await interaction.followup.send("Timed out waiting for category name.", ephemeral=True)
            return
        await interaction.followup.send("Enter the channel name for the modmail log channel:", ephemeral=True)
        try:
            chan_msg = await bot.wait_for("message", check=check, timeout=60)
            channel_name = chan_msg.content.strip()
        except Exception:
            await interaction.followup.send("Timed out waiting for channel name.", ephemeral=True)
            return
        guild = interaction.guild
        modmail_overwrites = TicketHelper.build_modmail_overwrites(guild)
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name, overwrites=modmail_overwrites)
        log_channel = discord.utils.get(category.channels, name=channel_name)
        if not log_channel:
            log_channel = await guild.create_text_channel(channel_name, category=category, overwrites=modmail_overwrites)
        view.result_channel = log_channel
        view.stop()
        await interaction.followup.send(f"Log channel set to {log_channel.mention}", ephemeral=True)

    @staticmethod
    async def link_existing_log_channel(interaction, bot, admin_user, view):
        if interaction.user != admin_user:
            await interaction.response.send_message("Only the admin who started setup can use this.", ephemeral=True)
            return
        await interaction.response.send_message("Please mention the channel or provide its ID for the modmail log channel:", ephemeral=True)
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await bot.wait_for("message", check=check, timeout=60)
            channel = None
            if msg.channel_mentions:
                channel = msg.channel_mentions[0]
            elif msg.content.isdigit():
                channel = interaction.guild.get_channel(int(msg.content))
            if not channel:
                await interaction.followup.send("Invalid channel. Please try setup again.", ephemeral=True)
                return
        except Exception:
            await interaction.followup.send("Timed out waiting for channel mention or ID.", ephemeral=True)
            return
        view.result_channel = channel
        view.stop()
        await interaction.followup.send(f"Log channel set to {channel.mention}", ephemeral=True)

    @staticmethod
    async def create_ticket(interaction: discord.Interaction):
        """Handle ticket creation logic"""
        guild = interaction.guild
        category = interaction.channel.category
        ticket_name = f"ticket-{interaction.user.name}".replace(
            " ", "-").lower()
        existing = discord.utils.get(category.text_channels, name=ticket_name)
        if existing:
            await interaction.response.send_message(f"You already have an open ticket: {existing.mention}", ephemeral=True)
            return
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role in guild.roles:
            perms = role.permissions
            if perms.kick_members or perms.ban_members or perms.manage_guild:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True)
        ticket_channel = await guild.create_text_channel(ticket_name, category=category, overwrites=overwrites)
        embed = SetupEmbed.create_ticket_embed(
            interaction.user, interaction.values[0] if hasattr(interaction, 'values') else 'general')
        await ticket_channel.send(embed=embed)
        await interaction.response.send_message(f"Ticket created: {ticket_channel.mention}", ephemeral=True)

    @staticmethod
    async def close_ticket(channel, log_channel=None):
        """Close a ticket and log the conversation"""
        messages = []
        async for message in channel.history(limit=1000, oldest_first=True):
            messages.append(
                f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {message.author}: {message.content}")
        log_text = f"Closed Ticket: {channel.name}\n" + "\n".join(messages)
        if log_channel:
            file = discord.File(io.BytesIO(log_text.encode(
                "utf-8")), filename=f"{channel.name}_log.txt")
            await log_channel.send(content=f"Log for {channel.name}:", file=file)

    @staticmethod
    def build_ticket_panel_overwrites(guild):
        return {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                add_reactions=False
            )
        }

    @staticmethod
    def build_modmail_overwrites(guild):
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False)
        }
        for role in guild.roles:
            perms = role.permissions
            if perms.kick_members or perms.ban_members or perms.manage_guild:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True
                )
        return overwrites


class WelcomeHelper:
    """Helper functions for welcome settings management"""

    @staticmethod
    async def handle_setting_update(view, interaction: discord.Interaction, setting_key: str, setting_name: str):
        """Handle updating a welcome setting through the interactive interface"""
        if interaction.user.id != view.ctx.author.id:
            await view.send_response(interaction, "You can't use this button.")
            return

        # Get current value for this setting
        current_value = next(
            (row[1] for row in view.rows if row[0] == setting_key), None)

        # Create the channel edit view with clear button
        from .views import ChannelEditView
        edit_view = ChannelEditView(
            view, interaction, setting_key, setting_name, current_value)

        # Edit the original message with the prompt and clear button
        prompt_embed = discord.Embed(
            title=f"{setting_name}",
            description="Please mention the channel or provide the channel ID.",
            color=discord.Color.orange()
        )

        if current_value:
            prompt_embed.add_field(
                name="Current Setting",
                value=f"<#{current_value}>",
                inline=False
            )

        await interaction.response.edit_message(
            content="",
            embed=prompt_embed,
            view=edit_view
        )

        def check(message):
            return (
                message.author.id == interaction.user.id and
                message.channel.id == interaction.channel.id
            )

        try:
            response = await view.bot.wait_for('message', timeout=60.0, check=check)

            # Parse channel mention or ID
            channel_id = None
            channel = None

            # Check if it's a channel mention
            if response.content.startswith('<#') and response.content.endswith('>'):
                channel_id = response.content[2:-1]
                channel = interaction.guild.get_channel(int(channel_id))

            # Check if it's a raw channel ID
            elif response.content.isdigit():
                channel_id = response.content
                channel = interaction.guild.get_channel(int(channel_id))

            # Check if it's a channel name
            else:
                channel = discord.utils.get(
                    interaction.guild.channels, name=response.content)
                if channel:
                    channel_id = str(channel.id)

            # Delete the user's message immediately
            try:
                await response.delete()
            except (discord.NotFound, discord.Forbidden):
                pass

            if not channel or not channel_id:
                # Return to original view with error message
                embed = WelcomeHelper.create_settings_embed(
                    interaction.guild, view.rows)
                from .views import WelcomeSettingsView
                new_view = WelcomeSettingsView(
                    view.ctx, view.bot, view.guild_id, view.rows)
                await interaction.edit_original_response(content="❌ Invalid channel. Please provide a valid channel mention, ID, or name from this server.", embed=embed, view=new_view)
                return

            if channel.guild.id != interaction.guild.id:
                # Return to original view with error message
                embed = WelcomeHelper.create_settings_embed(
                    interaction.guild, view.rows)
                from .views import WelcomeSettingsView
                new_view = WelcomeSettingsView(
                    view.ctx, view.bot, view.guild_id, view.rows)
                await interaction.edit_original_response(content="❌ That channel is not in this server.", embed=embed, view=new_view)
                return

            # Update the database
            async with view.bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "INSERT INTO guild_settings (guild_id, `key`, value) VALUES (%s, %s, %s) AS new ON DUPLICATE KEY UPDATE value = new.value",
                        (view.guild_id, setting_key, channel_id)
                    )
                    await conn.commit()

            # Update the rows data and refresh the view
            view.rows = [row for row in view.rows if row[0] != setting_key]
            view.rows.append((setting_key, channel_id))

            # Refresh the embed and view without any confirmation message
            embed = WelcomeHelper.create_settings_embed(
                interaction.guild, view.rows)
            from .views import WelcomeSettingsView
            new_view = WelcomeSettingsView(
                view.ctx, view.bot, view.guild_id, view.rows)
            await interaction.edit_original_response(content="", embed=embed, view=new_view)

        except TimeoutError:
            # Return to original view on timeout
            embed = WelcomeHelper.create_settings_embed(
                interaction.guild, view.rows)
            from .views import WelcomeSettingsView
            new_view = WelcomeSettingsView(
                view.ctx, view.bot, view.guild_id, view.rows)
            await interaction.edit_original_response(content="⏰ Timed out waiting for response.", embed=embed, view=new_view)

    @staticmethod
    def create_settings_embed(guild: discord.Guild, rows: List[Tuple[str, str]]) -> discord.Embed:
        """Create the welcome settings embed"""
        embed = discord.Embed(
            title="Welcome Settings",
            description=f"Current welcome configuration for **{guild.name}**",
            color=discord.Color.blue()
        )

        setting_names = {
            'welcome_channel_id': '🎉 Welcome',
            'squad_channel_id': '👥 LFG',
            'highlights_channel_id': '🎬 Highlights',
            'log_channel_id': '📋 Logs'
        }

        settings_order = [
            'welcome_channel_id',
            'squad_channel_id',
            'highlights_channel_id',
            'log_channel_id'
        ]

        for i, key in enumerate(settings_order):
            display_name = setting_names[key]
            value = next((row[1] for row in rows if row[0] == key), None)

            embed.add_field(
                name=display_name,
                value=f"<#{value}>" if value else "*(not set)*",
                inline=True
            )

            # After every 2 fields, insert a blank to force line break
            if (i + 1) % 2 == 0:
                embed.add_field(name="\u200b", value="\u200b", inline=True)

        return embed

    @staticmethod
    async def process_channel_arguments(settings: List[Tuple[str, Union[str, None]]], guild_id: str, bot, send_func) -> Tuple[List[str], bool]:
        """Process command-line channel arguments and update database"""
        updated_settings = []

        async with bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                for key, value in settings:
                    if value:
                        # Accept channel mention or ID
                        channel_id = None
                        if value.isdigit():
                            channel_id = value
                        else:
                            match = re.match(r"<#(\d+)>", value)
                            if match:
                                channel_id = match.group(1)

                        if channel_id:
                            await cur.execute(
                                "INSERT INTO guild_settings (guild_id, `key`, value) VALUES (%s, %s, %s) AS new ON DUPLICATE KEY UPDATE value = new.value",
                                (guild_id, key, channel_id)
                            )
                            updated_settings.append(
                                f"• `{key}`: <#{channel_id}>")
                            logger.info(
                                f"Set {key} to {channel_id} in guild {guild_id}.")
                        else:
                            await send_func(f"❌ Invalid channel mention or ID for `{key}`. Skipping this setting.")
                            logger.warning(
                                f"Invalid channel '{value}' for {key} in guild {guild_id}.")
                            continue

                await conn.commit()

        return updated_settings, len(updated_settings) > 0


class StatusHelper:
    """Helper functions for bot status management"""

    @staticmethod
    async def set_bot_status(bot, status: str, activity_type: str = "playing", activity: str = None) -> Tuple[bool, str]:
        """Set the bot's status and activity"""
        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }
        activity_type_map = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "streaming": discord.ActivityType.streaming
        }

        # Validate status
        status_lower = status.lower()
        if status_lower not in status_map:
            return False, "Invalid status. Choose from: online, idle, dnd, invisible."

        # Validate activity type
        activity_type_lower = activity_type.lower()
        if activity_type_lower not in activity_type_map:
            return False, "Invalid activity type. Choose from: playing, watching, listening, streaming."

        # Set Discord presence
        discord_status = status_map[status_lower]
        activity_obj = None
        if activity:
            if activity_type_lower == "streaming":
                # Support "title|url" or just a URL as activity
                if "|" in activity:
                    stream_title, stream_url = activity.split("|", 1)
                elif activity.startswith("http"):
                    stream_title, stream_url = "Streaming!", activity
                else:
                    stream_title, stream_url = activity or "Streaming!", "https://twitch.tv/"
                activity_obj = discord.Streaming(
                    name=stream_title, url=stream_url)
            else:
                activity_obj = discord.Activity(
                    type=activity_type_map[activity_type_lower], name=activity)

        await bot.change_presence(status=discord_status, activity=activity_obj)

        success_msg = f"Bot status set to **{status_lower}** with activity type **{activity_type_lower}**"
        if activity:
            success_msg += f" and activity: {activity}"
        success_msg += "."

        logger.info(
            f"Bot status set to {status_lower} with activity type {activity_type_lower} and activity: {activity}")
        return True, success_msg
