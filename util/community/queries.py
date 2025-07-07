from datetime import datetime, timezone
from typing import List, Dict, Set, Optional, Tuple
import json
import re
import logging
from util.community.models import Loadout, LoadoutSearchResult
from util.core.database import Database
from util.community.constants import MW2GunsLower

logger = logging.getLogger(__name__)


class CommunityQueries:
    @staticmethod
    async def get_cached_loadouts(username, guild_id=None):
        """Fetch cached loadouts for a user from the community_loadouts table."""
        if guild_id is not None:
            query = "SELECT data, last_updated FROM community_loadouts WHERE username = %s AND guild_id = %s"
            row = await Database.Database.fetchrow(query, username.lower(), str(guild_id))
        else:
            query = "SELECT data, last_updated FROM community_loadouts WHERE username = %s"
            row = await Database.Database.fetchrow(query, username.lower())

        if row:
            try:
                return json.loads(row["data"]), row["last_updated"]
            except Exception:
                return None, None
        return None, None

    @staticmethod
    async def save_loadouts(username, guild_id, loadouts, last_updated=None):
        """Save loadouts for a user into the community_loadouts table."""
        if last_updated is None:
            last_updated = datetime.now(timezone.utc).isoformat()
        query = '''
            REPLACE INTO community_loadouts (username, data, last_updated, guild_id)
            VALUES (%s, %s, %s, %s)
        '''
        await Database.execute(query, username.lower(), json.dumps(loadouts), last_updated, str(guild_id))

    @staticmethod
    async def resolve_username(arg, guild_id=None):
        """Resolve Discord mention to WZHub username, or return arg if not a mention."""
        mention_match = re.match(r'^<@!?(\d+)>$', str(arg))
        if mention_match:
            discord_id = mention_match.group(1)
            try:
                query = "SELECT wzhub_username FROM user_sync WHERE discord_id = %s"
                row = await Database.fetchrow(query, discord_id)
                if row:
                    logger.debug(
                        f"Resolved username for Discord ID {discord_id}: {row['wzhub_username']}")
                    return row["wzhub_username"]
                else:
                    logger.info(
                        f"No wzhub_username found for Discord ID {discord_id}")
                    return None
            except Exception as e:
                logger.error(
                    f"Error resolving username for Discord ID {discord_id}: {e}", exc_info=True)
                return None
        return arg

    @staticmethod
    def get_all_loadouts() -> List[LoadoutSearchResult]:
        """Get all cached loadouts from database."""
        rows = Database.fetch(
            "SELECT username, data, last_updated FROM community_loadouts")

        results = []
        for username, data, last_updated in rows:
            try:
                loadouts_data = json.loads(data)
                for loadout_data in loadouts_data:
                    loadout = Loadout.from_dict(loadout_data)
                    results.append(LoadoutSearchResult(
                        username, loadout, last_updated))
            except Exception:
                continue

        return results

    @staticmethod
    def search_loadouts_by_gun(gun_name: str) -> List[LoadoutSearchResult]:
        """Search for loadouts by gun name."""
        rows = Database.fetch(
            "SELECT username, data, last_updated FROM community_loadouts")

        found = []
        for username, data, last_updated in rows:
            try:
                loadouts_data = json.loads(data)
                for loadout_data in loadouts_data:
                    if gun_name.lower() in loadout_data["gun_name"].lower():
                        loadout = Loadout.from_dict(loadout_data)
                        found.append(LoadoutSearchResult(
                            username, loadout, last_updated))
                        break
            except Exception:
                continue

        return sorted(found, key=lambda x: x.username.lower())

    @staticmethod
    def get_guns_by_type() -> Dict[str, Set[str]]:
        """Get all cached guns organized by type."""
        rows = Database.fetch("SELECT data FROM community_loadouts")

        guns = {}
        for (data,) in rows:
            try:
                loadouts = json.loads(data)
                for loadout in loadouts:
                    gun_type = loadout["gun_type"]
                    gun_name = loadout["gun_name"]
                    if gun_type not in guns:
                        guns[gun_type] = set()
                    guns[gun_type].add(gun_name)
            except Exception:
                continue

        return guns

    @staticmethod
    def cache_user_loadouts(username: str, loadouts: List[Dict], timestamp: str) -> None:
        """Cache user loadouts to database."""
        mw2_loadouts = [
            l for l in loadouts
            if l["gun_name"].lower() in MW2GunsLower
        ]

        if not mw2_loadouts:
            return

        mw2_loadouts = sorted(
            mw2_loadouts, key=lambda l: l["gun_name"].lower())

        Database.execute(
            "REPLACE INTO community_loadouts (username, data, last_updated) VALUES (?, ?, ?)",
            (username.lower(), json.dumps(mw2_loadouts), timestamp)
        )

    @staticmethod
    def get_user_loadouts(username: str) -> Optional[Tuple]:
        """Get cached loadouts for a specific user."""
        return Database.fetchrow(
            "SELECT data, last_updated FROM community_loadouts WHERE username = ?",
            (username.lower(),)
        )

    @staticmethod
    def delete_user_loadouts(username: str) -> bool:
        """Delete cached loadouts for a specific user."""
        result = Database.execute(
            "DELETE FROM community_loadouts WHERE username = ?",
            (username.lower(),)
        )
        return result > 0

    @staticmethod
    async def all_synced_users():
        return await Database.fetch("SELECT discord_id, wzhub_username, discord_username FROM user_sync")

    @staticmethod
    async def update_user_sync(discord_id, wzhub_username, discord_username):
        return await Database.execute(
            """
            INSERT INTO user_sync (discord_id, wzhub_username, discord_username)
            VALUES (%s, %s, %s) AS new
            ON DUPLICATE KEY UPDATE
                wzhub_username = new.wzhub_username,
                discord_username = new.discord_username
            """,
            discord_id, wzhub_username, discord_username
        )

    @staticmethod
    async def delete_user_sync(discord_id):
        return await Database.execute("DELETE FROM user_sync WHERE discord_id = %s", discord_id)

    @staticmethod
    async def get_user_sync(identifier):
        """
        Fetch a user_sync row by Discord ID (int/str of digits) or wzhub username (str).
        """
        # Determine if identifier is a Discord ID (all digits)
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            query = "SELECT wzhub_username, discord_id, discord_username FROM user_sync WHERE discord_id = %s"
        else:
            query = "SELECT wzhub_username, discord_id, discord_username FROM user_sync WHERE wzhub_username = %s"
        return await Database.fetchrow(query, identifier)

    @staticmethod
    async def insert_or_update_user_sync(discord_id, wzhub_username, discord_username):
        """
        Insert or update a user_sync row using MySQL.
        """
        return await Database.execute(
            """
            INSERT INTO user_sync (discord_id, wzhub_username, discord_username)
            VALUES (%s, %s, %s) AS new
            ON DUPLICATE KEY UPDATE
                wzhub_username = new.wzhub_username,
                discord_username = new.discord_username
            """,
            discord_id, wzhub_username, discord_username
        )

    @staticmethod
    async def get_synced_users():
        """
        Fetch all synced users from the user_sync table.
        Returns a list of dicts with keys: discord_id, wzhub_username, discord_username.
        """
        rows = await Database.fetch("SELECT discord_id, wzhub_username, discord_username FROM user_sync")
        # If your Database.fetch returns a list of tuples, convert to dicts:
        result = []
        for row in rows:
            if isinstance(row, dict):
                result.append(row)
            else:
                # Assume tuple order: (discord_id, wzhub_username, discord_username)
                result.append({
                    "discord_id": row[0],
                    "wzhub_username": row[1],
                    "discord_username": row[2]
                })
        return result
