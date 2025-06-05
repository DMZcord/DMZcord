import discord
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta
from cogs.utils import format_timestamp, format_table

class CheaterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def logcheater(self, ctx: commands.Context, activision_id: str, *, reason: str = "No reason provided"):
        """!logcheater <Activision ID> [Reason] """
        if "#" not in activision_id:
            await ctx.send("Please provide a valid Activision ID in the format 'Username#1234567' (e.g., 'ヅCAPONE89ヅ#9322496').")
            return
        conn = sqlite3.connect('dmzcord.db')  # Updated database name
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO cheaters (activision_id, reason, timestamp, added_by) VALUES (?, ?, ?, ?)",
                  (activision_id, reason, datetime.now().isoformat(), str(ctx.author)))
        conn.commit()
        conn.close()
        await ctx.send(f"Logged cheater with Activision ID `{activision_id}` for: {reason}")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def listcheaters(self, ctx: commands.Context):
        """ List all cheaters in the database. """
        conn = sqlite3.connect('dmzcord.db')  # Updated database name
        c = conn.cursor()
        c.execute("SELECT activision_id, reason, timestamp, added_by FROM cheaters")
        cheaters = c.fetchall()
        conn.close()
        if not cheaters:
            await ctx.send("No cheaters found in the database.")
            return
        rows = [["Activision ID", "Reason", "Timestamp", "Added By"]]
        for activision_id, reason, timestamp, added_by in cheaters:
            reason = (reason[:25] + "...") if len(reason) > 25 else reason
            added_by = (added_by[:15] + "...") if len(added_by) > 15 else added_by
            activision_id = (activision_id[:25] + "...") if len(activision_id) > 25 else activision_id
            rows.append([activision_id, reason, format_timestamp(timestamp), added_by])
        table = format_table(rows)
        await ctx.send(f"**List of Cheaters**\n{table}")

    @commands.command()
    async def checkcheater(self, ctx: commands.Context, *, search_term: str = None):
        """!checkcheater <Activision ID>. Partial searches allowed."""
        if not search_term:
            await ctx.send("Please specify a username to check (e.g., `!checkcheater wyatt0069`).")
            return
        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()
        c.execute("SELECT activision_id, reason, timestamp, added_by FROM cheaters")
        cheaters = c.fetchall()
        conn.close()
        matches = []
        for activision_id, reason, timestamp, added_by in cheaters:
            if search_term.lower() in activision_id.lower():
                matches.append((activision_id, reason, timestamp, added_by))
        if not matches:
            await ctx.send(f"No cheater found matching '{search_term}'.")
        elif len(matches) == 1:
            activision_id, reason, timestamp, added_by = matches[0]
            response = (
                f"**Cheater Found**\n"
                f"Activision ID: {activision_id}\n"
                f"Reason: {reason}\n"
                f"Timestamp: {format_timestamp(timestamp)}\n"
                f"Added By: {added_by}"
            )
            await ctx.send(response)
        else:
            rows = [["Activision ID", "Reason", "Timestamp", "Added By"]]
            for activision_id, reason, timestamp, added_by in matches:
                reason = (reason[:25] + "...") if len(reason) > 25 else reason
                added_by = (added_by[:15] + "...") if len(added_by) > 15 else added_by
                activision_id = (activision_id[:25] + "...") if len(activision_id) > 25 else activision_id
                rows.append([activision_id, reason, format_timestamp(timestamp), added_by])
            table = format_table(rows)
            await ctx.send(f"**Multiple cheaters found matching '{search_term}':**\n{table}")

async def setup(bot: commands.Bot):
    await bot.add_cog(CheaterCog(bot))
