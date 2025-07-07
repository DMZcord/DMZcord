import logging
import json
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class DebugLoadouts:
    @staticmethod
    async def get_loadout_summary(bot, username: str, guild_id: str) -> Dict[str, Any]:
        """Get loadout summary for a user in a guild"""
        if not bot or not hasattr(bot, 'db'):
            logger.warning("Bot instance or database pool not found")
            return {"found": False, "loadouts": []}
        try:
            async with bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT data FROM community_loadouts WHERE username = %s AND guild_id = %s",
                        (username.lower(), guild_id)
                    )
                    row = await cur.fetchone()
            if not row:
                return {"found": False, "loadouts": []}
            try:
                loadouts = json.loads(row[0])
            except Exception:
                return {"found": False, "loadouts": []}
            wzhub_count = sum(
                1 for l in loadouts if l.get("source") == "wzhub")
            user_count = sum(1 for l in loadouts if l.get("source") == "user")
            return {
                "found": True,
                "loadouts": loadouts,
                "total": len(loadouts),
                "wzhub_count": wzhub_count,
                "user_count": user_count,
                "summary": f"{username} - {len(loadouts)}x guns - {wzhub_count}x from wzhub, {user_count}x from user"
            }
        except Exception as e:
            logger.error(f"Error getting loadout summary: {e}")
            return {"found": False, "loadouts": []}

    @staticmethod
    async def get_all_loadouts(bot, guild_id: str) -> List[Dict[str, Any]]:
        """Get all cached loadouts for a guild"""
        if not bot or not hasattr(bot, 'db'):
            logger.warning("Bot instance or database pool not found")
            return []
        try:
            async with bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT username, data FROM community_loadouts WHERE guild_id = %s",
                        (guild_id,)
                    )
                    rows = await cur.fetchall()
            results = []
            for username, data in rows:
                try:
                    loadouts = json.loads(data)
                    wzhub_count = sum(
                        1 for l in loadouts if l.get("source") == "wzhub")
                    user_count = sum(
                        1 for l in loadouts if l.get("source") == "user")
                    results.append({
                        "username": username,
                        "loadouts": loadouts,
                        "total": len(loadouts),
                        "wzhub_count": wzhub_count,
                        "user_count": user_count,
                        "summary": f"{username} - {len(loadouts)}x guns - {wzhub_count}x from wzhub, {user_count}x from user"
                    })
                except Exception:
                    continue
            return results
        except Exception as e:
            logger.error(f"Error getting all loadouts: {e}")
            return []

    @staticmethod
    def format_loadout_table(loadouts: List[Dict[str, Any]], include_username: bool = False) -> str:
        """Format loadouts into a table"""
        if include_username:
            headers = ["Username", "Gun", "Type", "Source", "Build Name"]
            rows = [headers]
            for loadout_data in loadouts:
                username = loadout_data["username"]
                for loadout in loadout_data["loadouts"]:
                    rows.append([
                        username,
                        loadout.get("gun_name", "?"),
                        loadout.get("gun_type", "?"),
                        loadout.get("source", "?"),
                        loadout.get("build_name", "-")
                    ])
        else:
            headers = ["Gun", "Type", "Source", "Build Name"]
            rows = [headers]
            for loadout in loadouts:
                rows.append([
                    loadout.get("gun_name", "?"),
                    loadout.get("gun_type", "?"),
                    loadout.get("source", "?"),
                    loadout.get("build_name", "-")
                ])

        return TabError.format_table(rows)
    
    
    @staticmethod
    async def test_random_loadouts() -> Tuple[bool, List[str]]:
        """Test random loadout generation for all guns and return failures"""
        try:
            # Import from your existing constants
            from util.community.constants import MW2Guns, Gun_Image_Urls
            from util.community.data import Gun_Attachments
        except ImportError as e:
            return False, [f"Could not import constants: {e}"]

        import random

        def test_random_loadout_generation(gun: str) -> Optional[str]:
            """Test if we can generate a random loadout for this gun. Returns error message if failed."""
            try:
                if not Gun_Attachments:
                    return f"No attachment data available"

                compatible_attachments = []
                gun_upper = gun.upper()

                # Find compatible attachments for this gun
                for att_type, att_dict in Gun_Attachments.items():
                    if not isinstance(att_dict, dict):
                        continue

                    for att_name, guns in att_dict.items():
                        if not isinstance(guns, list):
                            continue

                        if any(gun_upper == g.upper() for g in guns):
                            compatible_attachments.append((att_type, att_name))

                if not compatible_attachments:
                    return f"No compatible attachments found"

                # Try to build attachment categories
                att_by_type = {}
                for att_type, att_name in compatible_attachments:
                    att_by_type.setdefault(att_type, []).append(att_name)

                if not att_by_type:
                    return f"No attachment types available"

                # Try to select random attachments (up to 5)
                chosen_types = random.sample(
                    list(att_by_type.keys()), min(5, len(att_by_type)))
                chosen_attachments = []

                for att_type in chosen_types:
                    att_name = random.choice(att_by_type[att_type])
                    chosen_attachments.append({
                        "name": att_name,
                        "type": att_type,
                        "tuning1": "0.00",
                        "tuning2": "0.00"
                    })

                # Test if we can create an embed (without actually creating it)
                gun_image_url = Gun_Image_Urls.get(gun.upper(), "")

                # Just test that we have the data needed for embed creation
                if len(chosen_attachments) == 0:
                    return f"No attachments selected"

                # Test passed - return None (no error)
                return None

            except Exception as e:
                return f"Exception during generation: {str(e)}"

        # Test all guns
        if not MW2Guns:
            return False, ["No gun data available"]

        failed = []
        tested_count = 0

        for gun in MW2Guns:  # MW2Guns is a list
            tested_count += 1
            error_msg = test_random_loadout_generation(gun)
            if error_msg:
                failed.append(f"{gun}: {error_msg}")

        success = len(failed) == 0

        # Add summary info
        if failed:
            failed.insert(
                0, f"Tested {tested_count} guns, {len(failed)} failed:")

        return success, failed