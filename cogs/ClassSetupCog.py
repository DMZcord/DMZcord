import discord
from discord.ext import commands

class ClassSetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def classsetup(self, ctx, class_name: str):
        """WORK IN PROGRESS"""
        classes = {
            "tank": "Tank: High HP, melee focus. Role: Defender.",
            "healer": "Healer: Restores team HP. Role: Support.",
            "dps": "DPS: High damage, agile. Role: Attacker."
        }
        if class_name.lower() in classes:
            await ctx.send(classes[class_name.lower()])
        else:
            await ctx.send("Class not found. Try: tank, healer, dps.")

async def setup(bot):
    await bot.add_cog(ClassSetupCog(bot))
