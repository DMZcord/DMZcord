from util.core.database import Database

class BlacklistQueries:
    @staticmethod
    async def add_to_blacklist(user_id=None, channel_id=None, guild_id=None, added_by=None, duration_seconds=None, active=True):
        """Add user or channel to blacklist."""
        if duration_seconds:
            query = '''
                INSERT INTO blacklist (user_id, channel_id, guild_id, added_by, added_at, duration_seconds, expires_at, active)
                VALUES (%s, %s, %s, %s, NOW(), %s, DATE_ADD(NOW(), INTERVAL %s SECOND), %s)
                ON DUPLICATE KEY UPDATE
                    added_at = NOW(),
                    duration_seconds = %s,
                    expires_at = DATE_ADD(NOW(), INTERVAL %s SECOND),
                    active = %s
            '''
            params = (
                user_id, channel_id, guild_id, added_by, duration_seconds, duration_seconds, active,
                duration_seconds, duration_seconds, active
            )
        else:
            query = '''
                INSERT INTO blacklist (user_id, channel_id, guild_id, added_by, added_at, duration_seconds, expires_at, active)
                VALUES (%s, %s, %s, %s, NOW(), NULL, NULL, %s)
                ON DUPLICATE KEY UPDATE
                    added_at = NOW(),
                    duration_seconds = NULL,
                    expires_at = NULL,
                    active = %s
            '''
            params = (user_id, channel_id, guild_id, added_by, active, active)
        await Database.execute(query, *params)

    @staticmethod
    async def check_blacklist(user_id=None, channel_id=None, guild_id=None):
        """Check if user or channel is blacklisted."""
        query = """
            SELECT 1 FROM blacklist
            WHERE active = TRUE
              AND (
                    (user_id = %s AND user_id IS NOT NULL)
                 OR (channel_id = %s AND channel_id IS NOT NULL)
                 OR (guild_id = %s AND guild_id IS NOT NULL)
              )
              LIMIT 1
        """
        params = (user_id, channel_id, guild_id)
        result = await Database.fetchrow(query, *params)
        return bool(result)

    @staticmethod
    async def all_blacklisted(guild_id=None, include_fields=False):
        """Get all blacklisted users/channels for a guild."""
        if include_fields:
            query = (
                "SELECT user_id, channel_id, guild_id, added_at, duration_seconds, expires_at, active FROM blacklist"
                + (" WHERE guild_id = %s" if guild_id else "")
            )
        else:
            query = (
                "SELECT user_id, channel_id FROM blacklist"
                + (" WHERE guild_id = %s" if guild_id else "")
            )
        params = (guild_id,) if guild_id else ()
        return await Database.fetch(query, *params)

    @staticmethod
    async def remove_from_blacklist(user_id=None, channel_id=None, guild_id=None, active=False):
        """Remove user or channel from blacklist."""
        query = '''
            UPDATE blacklist
            SET active = %s
            WHERE
                (user_id = %s AND user_id IS NOT NULL)
                OR (channel_id = %s AND channel_id IS NOT NULL)
                OR (guild_id = %s AND guild_id IS NOT NULL)
        '''
        params = (active, user_id, channel_id, guild_id)
        await Database.execute(query, *params)
