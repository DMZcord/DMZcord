import logging
import json
import time
from discord.ext import commands
from util.core import Database

RESTART_STATUS_FILE = "restart_status.json"

logger = logging.getLogger(__name__)

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="restart", description="Restart the bot)")
    @commands.is_owner()
    async def restart(self, ctx):
        msg = await ctx.send("Restarting...")
        with open(RESTART_STATUS_FILE, "w") as f:
            json.dump({"channel_id": msg.channel.id, "message_id": msg.id, "timestamp": time.time()}, f)
        self.bot._do_restart = True  # Set a flag
        await self.bot.close()

    @commands.hybrid_command(name="shutdown", description="Shutdown the bot")
    @commands.is_owner()
    async def shutdown(self, ctx):
        msg = await ctx.send("✅ Shutdown complete!")
        await self.bot.close()

    @commands.command(name="vacuum", description="Run the database vacuum")
    @commands.is_owner()
    async def vacuum(self, ctx):
        report = await Database.vacuum_report()
        await ctx.send(f"```\n{report}\n```")


async def setup(bot):
    await bot.add_cog(Owner(bot))
