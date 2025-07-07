import re
import logging
import json
import aiohttp
from discord.ext import commands
from discord import app_commands
from util.community import CommunityLoadoutCacher, MW2Guns, CommunityQueries
from util.core import Database, TableUtils, DiscordHelper

logger = logging.getLogger(__name__)


class SyncCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="sync", with_app_command=True, description="Sync your wzhub.gg username")
    @app_commands.describe(wzhub_username="Your wzhub.gg username")
    async def sync(self, ctx, wzhub_username: str):
        # Owner only records audit
        if wzhub_username == "records":
            if not await self.bot.is_owner(ctx.author):
                await DiscordHelper.respond(ctx, "Only the bot owner can view this.")
                return
            rows = await CommunityQueries.get_synced_users()
            if not rows:
                await DiscordHelper.respond(ctx, "No users are currently synced.")
                return
            table_rows = [["Discord ID", "Discord Username", "Wzhub.gg Username"]]
            for row in rows:
                if isinstance(row, dict):
                    table_rows.append([row.get("discord_id", ""), row.get("discord_username", ""), row.get("wzhub_username", "")])
                else:
                    table_rows.append([row[0], row[2], row[1]])
            table_str = TableUtils.format_table(table_rows)
            await DiscordHelper.respond(ctx, f"**Synced Users:**\n{table_str}")
            return
        # Prevent duplicate wzhub usernames
        existing = await CommunityQueries.get_user_sync(str(ctx.author.id))
        if existing and (existing[0] if isinstance(existing, (list, tuple)) else existing.get("wzhub_username")):
            already = existing[0] if isinstance(existing, (list, tuple)) else existing.get("wzhub_username")
            await DiscordHelper.respond(ctx, f"You already have a synced wzhub.gg username (`{already}`). Please use `/unsync` before syncing a new one.")
            return
        row = await CommunityQueries.get_user_sync(wzhub_username)
        if row and str(ctx.author.id) != (row[0] if isinstance(row, (list, tuple)) else row.get("discord_id")):
            await DiscordHelper.respond(ctx, f"❌ The wzhub.gg username `{wzhub_username}` is already synced to another Discord account. Please choose another username.")
            return
        # Validate wzhub.gg username
        url = f"https://wzhub.gg/loadouts/community/{wzhub_username}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 404:
                    await DiscordHelper.respond(ctx, f"❌ The wzhub.gg username `{wzhub_username}` does not exist. Please enter a valid username.")
                    return
        await CommunityQueries.insert_or_update_user_sync(
            str(ctx.author.id), wzhub_username, str(ctx.author)
        )
        # Migrate user created loadouts to the wzhub username
        old_username = str(ctx.author).lower()
        new_username = wzhub_username.lower()
        guild_id = str(ctx.guild.id)
        if old_username != new_username:
            row = await Database.fetch("SELECT data, last_updated FROM community_loadouts WHERE username = %s AND guild_id = %s", old_username, guild_id)
            if row:
                new_row = await Database.fetch("SELECT data FROM community_loadouts WHERE username = %s AND guild_id = %s", new_username, guild_id)
                # --- PATCH: Only json.loads if needed ---
                if isinstance(row[0], str):
                    old_loadouts = json.loads(row[0])
                else:
                    old_loadouts = row[0]
                if new_row:
                    if isinstance(new_row[0], str):
                        new_loadouts = json.loads(new_row[0])
                    else:
                        new_loadouts = new_row[0]
                    if isinstance(new_loadouts, dict): new_loadouts = [new_loadouts]
                    if isinstance(old_loadouts, dict): old_loadouts = [old_loadouts]
                    merged = new_loadouts + old_loadouts
                    await Database.execute("UPDATE community_loadouts SET data = %s, last_updated = %s WHERE username = %s AND guild_id = %s", json.dumps(merged), row[1], new_username, guild_id)
                    await Database.execute("DELETE FROM community_loadouts WHERE username = %s AND guild_id = %s", old_username, guild_id)
                else:
                    await Database.execute("UPDATE community_loadouts SET username = %s WHERE username = %s AND guild_id = %s", new_username, old_username, guild_id)
        logger.info("User %s synced with wzhub.gg username '%s'.", ctx.author, wzhub_username)
        await DiscordHelper.respond(ctx, f"✅ Synced your Discord account to wzhub.gg username `{wzhub_username}`.")
        # Silently cache loadouts for all mutual guilds
        mutual_guild_ids = [
            guild.id for guild in self.bot.guilds
            if guild.get_member(ctx.author.id)
        ]
        if mutual_guild_ids:
            cacher = CommunityLoadoutCacher(logger)
            await cacher.cache_community_loadouts(
                wzhub_username,
                mutual_guild_ids,
                CommunityQueries.save_loadouts,
                msg=None
            )

    @commands.hybrid_command(name="unsync", with_app_command=True, description="Unsync your wzhub.gg username")
    @app_commands.describe(user="User mention or Discord ID")
    async def unsync(self, ctx, user: str = None):
        if user is None:
            discord_id = str(ctx.author.id)
        else:
            if not await self.bot.is_owner(ctx.author):
                await DiscordHelper.respond(ctx, "Use `/unsync` to remove the sync between your wzhub username and discord.")
                return
            match = re.match(r"<@!?(\d+)>", user)
            if match:
                discord_id = match.group(1)
            elif user.isdigit():
                discord_id = user
            else:
                await DiscordHelper.respond(ctx, "Please provide a valid user mention or Discord ID.")
                return

        row = await Database.fetch("SELECT wzhub_username FROM user_sync WHERE discord_id = %s", discord_id)
        if not row:
            await DiscordHelper.respond(ctx, "No synced wzhub.gg username found for that user.")
            return
        if isinstance(row, dict):
            old_username = row.get("wzhub_username", "")
        elif isinstance(row, (list, tuple)):
            old_username = row[0]
        else:
            old_username = row
        old_username = str(old_username).lower()
        if user is not None:
            member = ctx.guild.get_member(int(discord_id))
            new_username = str(member).lower() if member else discord_id
        else:
            new_username = str(ctx.author).lower()
        guild_id = str(ctx.guild.id)
        if old_username != new_username:
            row2 = await Database.fetch("SELECT data, last_updated FROM community_loadouts WHERE username = %s AND guild_id = %s", old_username, guild_id)
            if row2:
                try:
                    if isinstance(row2[0], str):
                        loadouts = json.loads(row2[0])
                    else:
                        loadouts = row2[0]
                except Exception:
                    loadouts = []
                user_loadouts = [l for l in loadouts if l.get("source") == "user"]
                wzhub_loadouts = [l for l in loadouts if l.get("source") == "wzhub"]
                if wzhub_loadouts:
                    await Database.execute("UPDATE community_loadouts SET data = %s WHERE username = %s AND guild_id = %s", json.dumps(wzhub_loadouts), old_username, guild_id)
                else:
                    await Database.execute("DELETE FROM community_loadouts WHERE username = %s AND guild_id = %s", old_username, guild_id)
                if user_loadouts:
                    new_row = await Database.fetch("SELECT data FROM community_loadouts WHERE username = %s AND guild_id = %s", new_username, guild_id)
                    if new_row:
                        try:
                            if isinstance(new_row[0], str):
                                new_loadouts = json.loads(new_row[0])
                            else:
                                new_loadouts = new_row[0]
                        except Exception:
                            new_loadouts = []
                        merged = new_loadouts + user_loadouts
                        await Database.execute("UPDATE community_loadouts SET data = %s WHERE username = %s AND guild_id = %s", json.dumps(merged), new_username, guild_id)
                    else:
                        await Database.execute(
                            """INSERT INTO community_loadouts (username, data, last_updated, guild_id) VALUES (%s, %s, %s, %s) AS new ON DUPLICATE KEY UPDATE data = new.data, last_updated = new.last_updated""",
                            new_username, json.dumps(user_loadouts), row2[1], guild_id
                        )

        if user is None:
            await DiscordHelper.respond(ctx, "✅ You have been unsynced from wzhub.gg username `%s`." % old_username)
        else:
            mention = "<@%s>" % discord_id
            await DiscordHelper.respond(ctx, "✅ You have unsynced %s (ID: %s) from wzhub.gg username `%s`." % (mention, discord_id, old_username))
        await CommunityQueries.delete_user_sync(discord_id)

async def setup(bot):
    await bot.add_cog(SyncCog(bot))
