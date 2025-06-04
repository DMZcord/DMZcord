import discord
from discord.ext import commands

class ErrorHandlerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing required argument. Please check the command syntax.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("Member not found. Please provide a valid user ID or mention.")
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send(f"Command '{ctx.invoked_with}' is not found.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Invalid argument provided. Please use a valid user ID or number.")
        else:
            await ctx.send(f"An error occurred: {error}")

async def setup(bot):
    await bot.add_cog(ErrorHandlerCog(bot))
