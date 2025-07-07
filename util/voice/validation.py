import re
import discord

class MusicValidation:
    YOUTUBE_URL_RE = re.compile(
        r"^(https?\:\/\/)?(www\.|m\.)?(youtube\.com|youtu\.be)\/.+$"
    )

    @classmethod
    def is_youtube_url(cls, url: str) -> bool:
        """Check if URL is a valid YouTube URL."""
        return bool(cls.YOUTUBE_URL_RE.match(url))

    @staticmethod
    def check_duration_permissions(ctx, duration):
        """
        Check if user has permission to play a song of given duration.
        Returns (allowed: bool, message: str)
        """
        if duration is None:
            return False, "Could not determine the length of this song/video."
        
        perms = ctx.author.guild_permissions
        is_mod = perms.manage_guild or perms.manage_messages
        is_server_owner = ctx.author.id == ctx.guild.owner_id
        premium_role = discord.utils.get(ctx.guild.roles, name="Premium Members")
        has_premium = premium_role in ctx.author.roles if premium_role else False

        if is_server_owner:
            return True, ""
        elif is_mod or has_premium:
            if duration > 60 * 60:  # 1 hour
                return False, "Song length is capped at 1 hour"
        else:
            if duration > 5 * 60:  # 5 minutes
                return False, "Song length is capped at 5 minutes. Premium members can play songs up to 1 hour long."
        
        return True,