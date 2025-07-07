from discord.ext import commands
import logging
from util.owner.queries import BlacklistQueries
import time

logger = logging.getLogger(__name__)

class BlacklistUtils:
    @staticmethod
    async def cleanup_expired_blacklists(bot):
        logger = logging.getLogger("dmzcord.blacklist")
        unblacklisted = []
        async with bot.db.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT id, user_id, channel_id, guild_id FROM blacklist WHERE expires_at IS NOT NULL AND expires_at < NOW() AND active = 1"
                )
                rows = await cursor.fetchall()
                if rows:
                    logger.info(f"Found {len(rows)} expired blacklists to clean up.")
                for row in rows:
                    blacklist_id, user_id, channel_id, guild_id = row
                    await cursor.execute(
                        "UPDATE blacklist SET active = 0 WHERE id = %s AND active = 1",
                        (blacklist_id,)
                    )
                    if cursor.rowcount > 0:
                        unblacklisted.append((user_id, channel_id, guild_id))
        return unblacklisted

    @staticmethod
    def check_blacklist():
        async def predicate(ctx):
            return not await BlacklistQueries.check_blacklist(
                user_id=ctx.author.id,
                channel_id=getattr(ctx.channel, "id", None),
                guild_id=getattr(ctx.guild, "id", None)
            )
        return commands.check(predicate)
            
    @staticmethod        
    async def resolve_blacklist_target(bot, ctx, id_or_mention: str):
        """
        Resolves a string to a user_id, channel_id, or guild_id.
        Returns a tuple: (user_id, channel_id, guild_id)
        """
        user_id = None
        channel_id = None
        guild_id = None
    
        if id_or_mention.isdigit():
            id_int = int(id_or_mention)
            # Check all guilds for a matching guild ID
            guild = bot.get_guild(id_int)
            if guild:
                guild_id = id_int
            else:
                # Check all guilds for a matching channel ID
                found_channel = None
                for g in bot.guilds:
                    ch = g.get_channel(id_int)
                    if ch:
                        found_channel = ch
                        break
                if found_channel:
                    channel_id = id_int
                else:
                    # Check current guild for a member
                    if ctx.guild:
                        member = ctx.guild.get_member(id_int)
                        if member:
                            user_id = id_int
                        else:
                            user_id = id_int  # fallback
                    else:
                        user_id = id_int  # fallback if not in a guild context
        elif id_or_mention.startswith("<@") and id_or_mention.endswith(">"):
            user_id = int(id_or_mention.strip("<@!>"))
        elif id_or_mention.startswith("<#") and id_or_mention.endswith(">"):
            channel_id = int(id_or_mention.strip("<#>"))
        elif id_or_mention.lower() == "guild" and ctx.guild:
            guild_id = ctx.guild.id
    
        # Ensure only one is set
        if user_id:
            channel_id = None
            guild_id = None
        elif channel_id:
            user_id = None
            guild_id = None
        elif guild_id:
            user_id = None
            channel_id = None
    
        return user_id, channel_id, guild_id

