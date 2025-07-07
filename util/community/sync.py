import logging
from util.core import Database

logger = logging.getLogger(__name__)

class SyncNewMember:
    @staticmethod
    async def sync_community_loadouts(member):
        """Sync community loadouts for the new member."""
        query_loadouts = '''
            SELECT username, data, last_updated FROM community_loadouts
            WHERE username IN (SELECT wzhub_username FROM user_sync WHERE discord_id = %s)
        '''
        rows = await Database.fetch(query_loadouts, str(member.id))

        if rows:
            for row in rows:
                username = row["username"]
                data = row["data"]
                last_updated = row["last_updated"]
                query_check = 'SELECT 1 FROM community_loadouts WHERE username = %s AND guild_id = %s'
                exists = await Database.fetchrow(query_check, username, str(member.guild.id))

                if not exists:
                    query_insert = '''
                        INSERT INTO community_loadouts (username, data, last_updated, guild_id)
                        VALUES (%s, %s, %s, %s)
                    '''
                    await Database.execute(query_insert, username, data, last_updated, str(member.guild.id))
        else:
            logger.info(
                "[on_member_join] No cached loadouts or sync'd username for user %s (%s)", member, member.id)


