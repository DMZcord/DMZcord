from datetime import datetime, timezone
from playwright.async_api import async_playwright
from util.community.constants import MW2GunsLower
import json
import discord
from typing import Dict, List, Tuple, Set, Optional, Any
import logging

logger = logging.getLogger(__name__)

class CommunityLoadoutCacher:
    def __init__(self, logger):
        self.logger = logger

    async def cache_community_loadouts(self, username, guild_ids, save_loadouts, msg=None):
        url = f"https://wzhub.gg/loadouts/community/{username}"
        now = datetime.now(timezone.utc)
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url)
                loadout_list_selector = (
                    '#__layout > div > div.wzh-community-user.wz-content > div.container > div > div.wzh-community-user__content > div > div.community-user-loadouts__list'
                )
                await page.wait_for_selector(loadout_list_selector, timeout=30000)
                loadout_list = await page.query_selector(loadout_list_selector)
                if not loadout_list:
                    if msg:
                        await msg.edit(content=f"No loadouts found for `{username}`.")
                    await browser.close()
                    return False

                loadout_cards = await loadout_list.query_selector_all('> .loadout-card')
                if not loadout_cards:
                    if msg:
                        await msg.edit(content=f"No loadouts found for `{username}`.")
                    await browser.close()
                    return False

                loadouts = []
                for card in loadout_cards:
                    gun_name_element = await card.query_selector('.gun-badge__text')
                    gun_name = (await gun_name_element.inner_text()).strip() if gun_name_element else "Unknown"
                    gun_type_element = await card.query_selector('.loadout-card__type')
                    gun_type = ""
                    if gun_type_element:
                        gun_type_text = await gun_type_element.inner_text()
                        gun_type = gun_type_text.split('\n')[0].strip()
                    gun_image_url = None
                    gun_image_element = await card.query_selector('.loadout-content__gun-image img')
                    if gun_image_element:
                        src = await gun_image_element.get_attribute('src')
                        if src:
                            gun_image_url = src if src.startswith("http") else f"https://wzhub.gg{src}"
                    attachments = []
                    attachment_cards = await card.query_selector_all('.attachment-card-content')
                    for att_card in attachment_cards:
                        name_div = await att_card.query_selector('.attachment-card-content__name > div')
                        att_name = (await name_div.inner_text()).strip() if name_div else "Unknown"
                        type_span = await att_card.query_selector('.attachment-card-content__name > span')
                        att_type = (await type_span.inner_text()).strip() if type_span else "Unknown"
                        tuning1 = tuning2 = "0.00"
                        counts = await att_card.query_selector_all('.attachment-card-content__counts > div')
                        if len(counts) >= 1:
                            t1_span = await counts[0].query_selector('span')
                            t1_val = (await t1_span.inner_text()).strip() if t1_span else "-"
                            tuning1 = t1_val if t1_val not in ["-", ""] else "0.00"
                        if len(counts) >= 2:
                            t2_span = await counts[1].query_selector('span')
                            t2_val = (await t2_span.inner_text()).strip() if t2_span else "-"
                            tuning2 = t2_val if t2_val not in ["-", ""] else "0.00"
                        attachments.append({
                            "name": att_name,
                            "type": att_type,
                            "tuning1": tuning1,
                            "tuning2": tuning2
                        })
                    loadouts.append({
                        "gun_name": gun_name,
                        "gun_type": gun_type,
                        "gun_image_url": gun_image_url,
                        "attachments": attachments,
                        "source": "wzhub"
                    })

                # Filter for MW2 guns only
                loadouts = [l for l in loadouts if l["gun_name"].lower() in MW2GunsLower]
                if not loadouts:
                    if msg:
                        await msg.edit(content=f"No MW2 loadouts found for `{username}`.")
                    await browser.close()
                    return False

                # Sort alphabetically by gun_name
                loadouts = sorted(loadouts, key=lambda l: l["gun_name"].lower())

                # Save to cache for each guild
                last_updated = now.isoformat()
                for guild_id in guild_ids:
                    await save_loadouts(username.lower(), guild_id, loadouts, last_updated)
                    self.logger.info(f"[COMMUNITY] Cached {username} for guild {guild_id} at {last_updated}")

                await browser.close()
                return True
        except Exception as e:
            if msg:
                await msg.edit(content=f"Failed to load loadouts for `{username}`. Error: {e}")
            self.logger.error(f"Failed to cache community loadouts for {username}: {e}")
            return False
        
        
class LoadoutCacheHelper:
    """Helper functions for loadout cache management"""

    @staticmethod
    async def get_user_loadouts(bot, username: str, guild_id: Optional[str] = None) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
        """Get loadouts for a user from database"""
        async with bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                if guild_id:
                    # Guild-specific loadouts
                    await cur.execute(
                        "SELECT data FROM community_loadouts WHERE username = %s AND guild_id = %s",
                        (username, guild_id)
                    )
                    guild_row = await cur.fetchone()

                    # Global loadouts (all guilds)
                    await cur.execute(
                        "SELECT data, guild_id FROM community_loadouts WHERE username = %s",
                        (username,)
                    )
                    global_rows = await cur.fetchall()

                    return guild_row, global_rows
                else:
                    # Only global loadouts
                    await cur.execute(
                        "SELECT data, guild_id FROM community_loadouts WHERE username = %s",
                        (username,)
                    )
                    rows = await cur.fetchall()
                    return None, rows

    @staticmethod
    def count_loadouts_by_source(guild_row: Optional[Tuple], global_rows: List[Tuple]) -> Tuple[Dict[str, int], Dict[str, int]]:
        """Count loadouts by source (wzhub vs user) for guild and global"""
        guild_counts = {"wzhub": 0, "user": 0}
        global_counts = {"wzhub": 0, "user": 0}

        # Count guild-specific loadouts
        if guild_row:
            try:
                guild_loadouts = json.loads(guild_row[0])
                for loadout in guild_loadouts:
                    source = loadout.get("source", "wzhub")
                    if source in guild_counts:
                        guild_counts[source] += 1
            except Exception:
                pass

        # Count global loadouts (avoid duplicates)
        seen_loadouts: Set[Tuple] = set()
        for data, guild_id in global_rows:
            try:
                loadouts = json.loads(data)
                for loadout in loadouts:
                    # Create unique identifier to avoid counting duplicates
                    loadout_key = (
                        loadout.get("gun_name", ""),
                        loadout.get("gun_type", ""),
                        tuple(sorted([(att.get("name", ""), att.get("type", ""))
                              for att in loadout.get("attachments", [])]))
                    )

                    if loadout_key not in seen_loadouts:
                        seen_loadouts.add(loadout_key)
                        source = loadout.get("source", "wzhub")
                        if source in global_counts:
                            global_counts[source] += 1
            except Exception:
                continue

        return guild_counts, global_counts

    @staticmethod
    async def remove_loadouts_by_source(bot, username: str, source: str, scope: str, guild_id: Optional[str] = None, global_rows: Optional[List[Tuple]] = None) -> bool:
        """Remove loadouts by source and scope"""
        try:
            async with bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    if scope == "guild" and guild_id:
                        # Remove from this guild only
                        await cur.execute(
                            "SELECT data FROM community_loadouts WHERE username = %s AND guild_id = %s",
                            (username, guild_id)
                        )
                        guild_row = await cur.fetchone()

                        if guild_row:
                            loadouts = json.loads(guild_row[0])
                            remaining_loadouts = [
                                l for l in loadouts if l.get("source") != source]

                            if remaining_loadouts:
                                await cur.execute(
                                    "UPDATE community_loadouts SET data = %s WHERE username = %s AND guild_id = %s",
                                    (json.dumps(remaining_loadouts),
                                     username, guild_id)
                                )
                            else:
                                await cur.execute(
                                    "DELETE FROM community_loadouts WHERE username = %s AND guild_id = %s",
                                    (username, guild_id)
                                )

                    elif scope == "global" and global_rows:
                        # Remove from all guilds
                        for data, gid in global_rows:
                            try:
                                loadouts = json.loads(data)
                                remaining_loadouts = [
                                    l for l in loadouts if l.get("source") != source]

                                if remaining_loadouts:
                                    await cur.execute(
                                        "UPDATE community_loadouts SET data = %s WHERE username = %s AND guild_id = %s",
                                        (json.dumps(remaining_loadouts), username, gid)
                                    )
                                else:
                                    await cur.execute(
                                        "DELETE FROM community_loadouts WHERE username = %s AND guild_id = %s",
                                        (username, gid)
                                    )
                            except Exception:
                                continue

                    await conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Error removing loadouts: {e}")
            return False

    @staticmethod
    def create_loadout_summary_embed(username: str, guild_name: str, guild_counts: Dict[str, int], global_counts: Dict[str, int]) -> discord.Embed:
        """Create embed showing loadout breakdown"""
        embed = discord.Embed(
            title=f"Cached Loadouts for `{username}`",
            color=discord.Color.blue(),
            description="Choose which type of loadouts to remove:"
        )

        embed.add_field(
            name=f"This Server ({guild_name})",
            value=f"🌐 Wzhub.gg: {guild_counts['wzhub']} loadouts\n🛠️ DMZcord: {guild_counts['user']} loadouts",
            inline=True
        )

        embed.add_field(
            name="All Servers (Global)",
            value=f"🌐 Wzhub.gg: {global_counts['wzhub']} loadouts\n🛠️ DMZcord: {global_counts['user']} loadouts",
            inline=True
        )

        return embed
