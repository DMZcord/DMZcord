import discord
import random
import logging
from util.core.database import Database

logger = logging.getLogger(__name__)

class WelcomeHandler:
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def get_random_highlight_video(highlights_channel):
        """Get a random highlight video from the highlights channel."""
        try:
            messages = [message async for message in highlights_channel.history(limit=100)]
            video_messages = [
                msg for msg in messages
                if any(att.content_type and att.content_type.startswith("video/") for att in msg.attachments)
            ]

            if video_messages:
                random_video_message = random.choice(video_messages)
                video_attachments = [
                    att for att in random_video_message.attachments
                    if att.content_type and att.content_type.startswith("video/")
                ]

                if video_attachments:
                    random_video_attachment = random.choice(video_attachments)
                    video_url = random_video_attachment.url
                    clip_author = random_video_message.author.display_name
                    logger.info(
                        f"Selected random highlight video for welcome: {video_url} by {clip_author}")
                    return video_url, clip_author

        except discord.Forbidden:
            logger.warning(
                "Forbidden: Could not fetch highlights channel history.")
        except discord.HTTPException as e:
            logger.error(f"HTTPException while fetching highlights: {e}")
        except Exception as e:
            logger.exception("Unexpected error fetching highlights.")

        return "a community highlight video", "a community member"
    
    async def send_welcome_message(self, member: discord.Member):
        """Send welcome message with random highlight video."""
        guild_id = str(member.guild.id)

        welcome_channel_id = await GuildSettings.get_setting('welcome_channel_id', guild_id=guild_id)
        if not welcome_channel_id:
            logger.info(
                "Welcome channel ID not set. Skipping welcome message.")
            return

        welcome_channel = self.bot.get_channel(int(welcome_channel_id))
        if not welcome_channel:
            logger.warning(
                f"Welcome channel with ID {welcome_channel_id} not found.")
            return

        # Get channel tags
        squad_channel_id = await GuildSettings.get_setting('squad_channel_id', guild_id=guild_id)
        squad_channel_tag = f"<#{squad_channel_id}>" if squad_channel_id and self.bot.get_channel(
            int(squad_channel_id)) else "the squad channel"

        highlights_channel_id = await GuildSettings.get_setting('highlights_channel_id', guild_id=guild_id)
        highlights_channel = self.bot.get_channel(
            int(highlights_channel_id)) if highlights_channel_id else None
        highlights_channel_tag = f"<#{highlights_channel_id}>" if highlights_channel else "the highlights channel"

        # Get random highlight video
        video_url = "a community highlight video"
        clip_author = "a community member"

        if highlights_channel:
            video_url, clip_author = await WelcomeHandler.get_random_highlight_video(highlights_channel)

        welcome_message = (
            f"Welcome to the DMZ {member.mention}! "
            f"Please use {squad_channel_tag} to find a squad, or {highlights_channel_tag} to check out the community highlights!\n"
            f"Check out this video from {clip_author}!\n{video_url}"
        )

        try:
            await DiscordHelper.respond(welcome_channel, welcome_message)
            logger.info(
                f"Sent welcome message for {member} ({member.id}) in channel {welcome_channel.id}")
        except discord.Forbidden:
            logger.warning(
                f"Forbidden: Could not send welcome message for {member} in channel {welcome_channel.id}")
        except discord.HTTPException as e:
            logger.error(f"HTTPException while sending welcome message: {e}")
        except Exception as e:
            logger.exception("Unexpected error sending welcome message.")
