import discord
from discord.ext import commands
from discord import app_commands
from typing import Union
import logging
from util.moderation import WelcomeSettingsView, WelcomeHelper, StatusHelper

logger = logging.getLogger(__name__)


class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="welcome", description="Configure welcome settings for this server")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        welcome_channel_id="Channel ID for welcome messages",
        squad_channel_id="Channel ID for LFG",
        highlights_channel_id="Channel ID for community clips",
        log_channel_id="Channel ID for moderator logs"
    )
    async def welcome(
        self,
        ctx: Union[commands.Context, discord.Interaction],
        welcome_channel_id: str = None,
        squad_channel_id: str = None,
        highlights_channel_id: str = None,
        log_channel_id: str = None
    ):
        """Configure welcome settings for this server."""
        async def send(msg, **kwargs):
            if isinstance(ctx, discord.Interaction):
                if ctx.response.is_done():
                    return await ctx.followup.send(msg, ephemeral=True, **kwargs)
                else:
                    return await ctx.response.send_message(msg, ephemeral=True, **kwargs)
            else:
                return await ctx.send(msg, **kwargs)

        author = getattr(ctx, "author", None) or getattr(ctx, "user", None)
        guild = ctx.guild
        guild_id = str(guild.id)

        # Settings to configure
        settings = [
            ('welcome_channel_id', welcome_channel_id),
            ('squad_channel_id', squad_channel_id),
            ('highlights_channel_id', highlights_channel_id),
            ('log_channel_id', log_channel_id)
        ]

        # If no arguments are provided, show interactive settings view
        if not any([welcome_channel_id, squad_channel_id, highlights_channel_id, log_channel_id]):
            # Fetch current settings from database
            async with self.bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT `key`, value FROM guild_settings WHERE guild_id = %s AND `key` IN ('welcome_channel_id', 'squad_channel_id', 'highlights_channel_id', 'log_channel_id')",
                        (guild_id,)
                    )
                    rows = await cur.fetchall()

            # Create interactive view
            view = WelcomeSettingsView(ctx, self.bot, guild_id, rows)
            embed = WelcomeHelper.create_settings_embed(guild, rows)
            await send("", embed=embed, view=view)
            return

        # Process provided arguments to update settings
        updated_settings, has_updates = await WelcomeHelper.process_channel_arguments(
            settings, guild_id, self.bot, send
        )

        if has_updates:
            embed = discord.Embed(
                title="Welcome Settings Updated",
                description="The following settings have been updated:",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Updated Settings",
                value="\n".join(updated_settings),
                inline=False
            )
            await send("", embed=embed)
            logger.info(f"Welcome settings updated by {author} in guild {guild_id}.")
        else:
            await send("❌ No valid settings were provided to update.")

    @commands.hybrid_command(name="setstatus", description="Set the bot's status and activity")
    @app_commands.describe(
        status="online/idle/dnd/invisible",
        activity_type="playing/watching/listening/streaming",
        activity="Activity text"
    )
    @commands.is_owner()
    async def setstatus(
        self,
        ctx: Union[commands.Context, discord.Interaction],
        status: str,
        activity_type: str = "playing",
        activity: str = None
    ):
        """Set the bot's status and activity."""
        async def send(msg):
            if isinstance(ctx, discord.Interaction):
                if ctx.response.is_done():
                    return await ctx.followup.send(msg, ephemeral=True)
                else:
                    return await ctx.response.send_message(msg, ephemeral=True)
            else:
                return await ctx.send(msg)

        success, message = await StatusHelper.set_bot_status(self.bot, status, activity_type, activity)
        await send(message)


async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))
