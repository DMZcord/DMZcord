from datetime import datetime, timezone
from discord.ext import commands
import discord
import logging
from util.core import Database, StringUtils, DiscordHelper, TablePaginator, TimeUtils

logger = logging.getLogger(__name__)

class CheaterCog(commands.Cog):
    """Cog for managing cheater logs in the database."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="logcheater", description="Log a cheater by Activision ID and reason.")
    @commands.is_owner()
    async def logcheater(self, ctx: commands.Context, activision_id: str, *, reason: str = "No reason provided"):
        if hasattr(ctx, "interaction") and ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.interaction.response.defer()
        if "#" not in activision_id:
            msg = "Please provide a valid Activision ID in the format 'Username#1234567' (e.g., 'ヅCAPONE89ヅ#9322496')."
            await DiscordHelper.respond(ctx, msg, ephemeral=True)
            logger.warning("User tried to log invalid Activision ID: %s", activision_id)
            return
        reason = StringUtils.truncate(reason, 100)
        guild_id = str(ctx.guild.id)
        discord_user_id = str(ctx.author.id)
        author = str(ctx.author)

        # Check if activision_id already exists
        check_query = "SELECT 1 FROM cheaters WHERE activision_id = %s"
        existing = await Database.fetch(check_query, activision_id)
        if existing:
            msg = f"Activision ID `{activision_id}` is already logged as a cheater."
            await DiscordHelper.respond(ctx, msg, ephemeral=True)
            logger.info("Attempted to log duplicate Activision ID: %s", activision_id)
            return

        # Always use ISO 8601 with timezone (UTC)
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.info(f"Saving cheater with timestamp: {timestamp}")
        query = '''
            INSERT INTO cheaters (activision_id, reason, timestamp, added_by, added_by_id, guild_id)
            VALUES (%s, %s, %s, %s, %s, %s) AS new
            ON DUPLICATE KEY UPDATE
                reason = new.reason,
                timestamp = new.timestamp,
                added_by = new.added_by,
                added_by_id = new.added_by_id
        '''
        await Database.execute(query, activision_id, reason, timestamp, author, discord_user_id, guild_id)

        logger.info(
            "Cheater logged: %s by %s (%s) for reason: %s in guild %s", activision_id, author, discord_user_id, reason, guild_id)
        msg = f"Logged cheater with Activision ID `{activision_id}` for: {reason}"
        await DiscordHelper.respond(ctx, msg)

    @commands.hybrid_command(name="cheaters", description="List all cheaters in the database.")
    async def cheaters(self, ctx: commands.Context):
        if hasattr(ctx, "interaction") and ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.interaction.response.defer()

        query = "SELECT activision_id, reason, timestamp, added_by FROM cheaters"
        cheaters = await Database.fetch(query)

        if not cheaters:
            msg = "No cheaters found in the database."
            await DiscordHelper.respond(ctx, msg, ephemeral=True)
            logger.info("No cheaters found in the database when listing.")
            return

        cheaters.sort(key=lambda x: x["timestamp"], reverse=True)
        rows = [["Activision ID", "Reason", "Timestamp", "Added By"]]
        for cheater in cheaters:
            activision_id = StringUtils.truncate(cheater["activision_id"], 25)
            reason = StringUtils.truncate(cheater["reason"], 25)
            timestamp = TimeUtils.convert_timestamp(cheater["timestamp"], "PST")
            added_by = StringUtils.truncate(cheater["added_by"], 15)
            rows.append([activision_id, reason, timestamp, added_by])

        view = TablePaginator(rows, "**List of Cheaters (global):**", per_page=10)
        await DiscordHelper.respond(ctx, f"**List of Cheaters (global):**\n{view.get_page_table()}", view=view)
        logger.info(
            "%d cheaters listed by %s (global).",
            len(cheaters),
            getattr(ctx, 'author', getattr(ctx, 'user', 'unknown'))
        )

    @commands.hybrid_command(name="checkcheater", description="Check if someone is a known cheater (partial search allowed).")
    async def checkcheater(self, ctx: commands.Context, *, search_term: str = None):
        if hasattr(ctx, "interaction") and ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.interaction.response.defer()

        if not search_term:
            msg = "Please specify a username to check (e.g., `!checkcheater wyatt0069`)."
            await DiscordHelper.respond(ctx, msg, ephemeral=True)
            logger.warning("User tried to checkcheater without a search term.")
            return

        query = "SELECT activision_id, reason, timestamp, added_by FROM cheaters WHERE activision_id LIKE %s"
        cheaters = await Database.fetch(query, f"%{search_term}%")

        if not cheaters:
            msg = f"No cheater found matching '{search_term}'."
            await DiscordHelper.respond(ctx, msg, ephemeral=True)
            logger.info("No cheater found matching '%s'.", search_term)
        elif len(cheaters) == 1:
            cheater = cheaters[0]
            embed = discord.Embed(
                title="Cheater Found",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1377733230857551956/1391197762342617148/raw.png?ex=686b0561&is=6869b3e1&hm=b271740521d16020b81f4e0fe8d00706e0aed38218b1587d154abafe4499d892&")
            embed.add_field(name="Activision ID", value=cheater['activision_id'], inline=False)
            embed.add_field(name="Reason", value=cheater['reason'], inline=False)
            embed.add_field(
                name="Timestamp",
                value=TimeUtils.convert_timestamp(cheater["timestamp"], "PST"),
                inline=False
            )
            embed.add_field(name="Added By", value=cheater['added_by'], inline=False)
            await DiscordHelper.respond(ctx, "", embed=embed)
            logger.info("Cheater found for '%s': %s", search_term, cheater["activision_id"])
        else:
            rows = [["Activision ID", "Reason", "Timestamp", "Added By"]]
            for cheater in cheaters:
                activision_id = StringUtils.truncate(cheater["activision_id"], 25)
                reason = StringUtils.truncate(cheater["reason"], 25)
                timestamp = TimeUtils.convert_timestamp(cheater["timestamp"], "PST")
                added_by = StringUtils.truncate(cheater["added_by"], 15)
                rows.append([activision_id, reason, timestamp, added_by])

            view = TablePaginator(rows, f"**Multiple cheaters found matching '{search_term}' (global):**", per_page=10)
            await DiscordHelper.respond(
                ctx,
                f"**Multiple cheaters found matching '{search_term}' (global):**\n{view.get_page_table()}",
                view=view
            )
            logger.info("%d cheaters matched '%s'.", len(cheaters), search_term)

async def setup(bot: commands.Bot):
    await bot.add_cog(CheaterCog(bot))
