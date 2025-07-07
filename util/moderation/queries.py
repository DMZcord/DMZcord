from util.core.database import Database


class ModerationQueries:
    @staticmethod
    async def add_moderation_entry(id, user_id, discord_username, reason, timestamp, added_by, guild_id, action, duration=None, active=True, quashed=False):
        """Add a moderation entry."""
        query = '''
            INSERT INTO moderation (id, user_id, discord_username, reason, timestamp, added_by, guild_id, action, duration, active, quashed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE discord_username=VALUES(discord_username), reason=VALUES(reason), timestamp=VALUES(timestamp), added_by=VALUES(added_by), action=VALUES(action), duration=VALUES(duration), active=VALUES(active), quashed=VALUES(quashed)
        '''
        await Database.execute(query, id, user_id, discord_username, reason, timestamp, added_by, guild_id, action, duration, active, quashed)

    @staticmethod
    async def get_moderation_entry(user_id, guild_id):
        """Get moderation entries for a user in a guild."""
        query = "SELECT * FROM moderation WHERE user_id = %s AND guild_id = %s"
        return await Database.fetch(query, user_id, guild_id)

    @staticmethod
    async def get_active_mute(user_id, guild_id):
        """Get active mute for a user."""
        query = '''
            SELECT id, reason, duration FROM moderation 
            WHERE user_id = %s AND action = 'mute' 
            AND duration IS NOT NULL AND active = 1 AND quashed = 0 AND guild_id = %s
            ORDER BY timestamp DESC LIMIT 1
        '''
        return await Database.fetchrow(query, user_id, guild_id)

    @staticmethod
    async def get_ticket_settings(conn, guild_id):
        query = "SELECT ticket_channel, log_channel FROM ticket_settings WHERE guild_id = %s"
        async with conn.cursor() as cursor:
            await cursor.execute(query, (guild_id,))
            return await cursor.fetchone()

    @staticmethod
    async def save_ticket_settings(conn, guild_id, ticket_channel_id, message_id, log_channel_id):
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO ticket_settings (guild_id, ticket_channel, message_id, log_channel)
                VALUES (%s, %s, %s, %s) AS new
                ON DUPLICATE KEY UPDATE
                    ticket_channel=new.ticket_channel,
                    message_id=new.message_id,
                    log_channel=new.log_channel
                """,
                (guild_id, ticket_channel_id, message_id, log_channel_id)
            )
            await conn.commit()
