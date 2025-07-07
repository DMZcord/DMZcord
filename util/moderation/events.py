from datetime import datetime, timedelta, timezone
import logging
import discord
from util.core import Database
from util.moderation.utils import IDUtils

logger = logging.getLogger(__name__)

class MuteEventHelper:
    @staticmethod
    async def handle_mute_reapplication(bot, member):
        """Check and reapply mutes for rejoining members."""
        user_id = str(member.id)
        guild_id = str(member.guild.id)

        query = '''
            SELECT id, reason, duration FROM moderation 
            WHERE user_id = %s AND guild_id = %s AND action = 'mute' 
            AND duration IS NOT NULL AND active = 1 AND quashed = 0 
            ORDER BY timestamp DESC LIMIT 1
        '''
        mute = await Database.fetchrow(query, user_id, guild_id)

        if not mute:
            return

        mute_id, reason, duration = mute["id"], mute["reason"], mute["duration"]

        # Get mute start time
        mute_start_query = "SELECT timestamp FROM moderation WHERE id = %s"
        mute_start_row = await Database.fetchrow(mute_start_query, mute_id)
        mute_start = datetime.fromisoformat(mute_start_row["timestamp"])
        mute_end = mute_start + timedelta(seconds=duration)
        current_time = datetime.now(timezone.utc)

        if current_time < mute_end:
            mute_role = discord.utils.get(member.guild.roles, name="Muted")
            if mute_role and mute_role not in member.roles:
                try:
                    await member.add_roles(mute_role, reason="Re-applying mute after rejoin")
                    logger.info(
                        f"Re-applied 'Muted' role to {member} ({user_id}) after rejoin.")
                except discord.Forbidden:
                    logger.warning(
                        f"Missing permissions to re-apply mute to {member} ({user_id}) after rejoin.")

    @staticmethod
    async def process_mute_expiration(guild, mute_id, user_id, guild_id):
        """Process an expired mute."""
        member = guild.get_member(int(user_id))
        mute_role = discord.utils.get(guild.roles, name="Muted")

        # Create unmute record
        unmute_id = await IDUtils.generate_unique_id(user_id, "moderation")
        query_insert_unmute = '''
            INSERT INTO moderation (id, user_id, reason, timestamp, added_by, action, duration, guild_id, active, quashed) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 0)
        '''
        await Database.execute(query_insert_unmute, unmute_id, user_id, "Mute duration expired",
                               datetime.now(timezone.utc).isoformat(), "Bot", "unmute", None, guild_id)

        # Deactivate mute record
        query_update_mute = 'UPDATE moderation SET active = 0 WHERE id = %s AND guild_id = %s'
        await Database.execute(query_update_mute, mute_id, guild_id)

        logger.info(
            f"Auto-unmuted user {user_id} (mute expired) in guild {guild_id}.")

        # Remove mute role if member is still in guild
        if member and mute_role and mute_role in member.roles:
            try:
                await member.remove_roles(mute_role, reason="Mute duration expired")
                logger.info(
                    f"Removed 'Muted' role from user {user_id} in guild {guild_id}.")
            except discord.Forbidden:
                logger.warning(
                    f"Failed to remove 'Muted' role from user {user_id} in guild {guild_id} (missing permissions).")
