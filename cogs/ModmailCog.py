import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()
GUILD_ID = os.getenv('GUILD_ID')
MODMAIL_LOG_CHANNEL_ID = os.getenv('MODMAIL_LOG_CHANNEL_ID')

class ModmailCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not GUILD_ID or not MODMAIL_LOG_CHANNEL_ID:
            raise ValueError("GUILD_ID or MODMAIL_LOG_CHANNEL_ID missing in .env")
        self.guild_id = int(GUILD_ID)
        self.modmail_log_channel_id = int(MODMAIL_LOG_CHANNEL_ID)

    def format_timestamp(self, iso_timestamp: str) -> str:
        try:
            dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
            return dt.strftime("%d-%m-%Y %H:%M:%S")
        except ValueError:
            return "Invalid timestamp"

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not isinstance(message.channel, discord.DMChannel):
            return
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return
        category = discord.utils.get(guild.categories, name="Modmail")
        if not category:
            category = await guild.create_category("Modmail")
        channel_name = f"ticket-{message.author.id}"
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await existing_channel.send(f"New message from {message.author}: {message.content}")
            try:
                ticket_link = f"https://discord.com/channels/{guild.id}/{existing_channel.id}"
                await message.author.send(f"Your message has been sent to {ticket_link}")
            except discord.Forbidden:
                await existing_channel.send(f"Could not DM {message.author} (DMs disabled or bot blocked).")
        else:
            existing_channel = await guild.create_text_channel(channel_name, category=category)
            await existing_channel.send(f"New modmail from {message.author}: {message.content}")
            try:
                ticket_link = f"https://discord.com/channels/{guild.id}/{existing_channel.id}"
                await message.author.send(f"Your modmail ticket has been created: {ticket_link}")
            except discord.Forbidden:
                await existing_channel.send(f"Could not DM {message.author} (DMs disabled or bot blocked).")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def closeticket(self, ctx: commands.Context):
        """Closes the current modmail ticket and logs the conversation."""
        if not ctx.channel.name.startswith("ticket-"):
            await ctx.send("This command can only be used in a modmail ticket channel.")
            return
        guild = self.bot.get_guild(self.guild_id)
        log_channel = guild.get_channel(self.modmail_log_channel_id)
        if not log_channel:
            await ctx.send(f"Could not find modmail log channel with ID {self.modmail_log_channel_id}.")
            return
        user_id = ctx.channel.name.split("-")[1]
        messages = []
        async for message in ctx.channel.history(limit=1000):
            formatted_time = self.format_timestamp(message.created_at.isoformat())
            messages.append(f"{formatted_time}: {message.author}: {message.content}")
        log_message = f"**Closed Ticket: {ctx.channel.name}**\n" + "\n".join(reversed(messages))
        if len(log_message) > 2000:
            parts = []
            current_part = ""
            for line in log_message.split("\n"):
                if len(current_part) + len(line) + 1 > 2000:
                    parts.append(current_part)
                    current_part = line + "\n"
                else:
                    current_part += line + "\n"
            if current_part:
                parts.append(current_part)
            for part in parts:
                await log_channel.send(part)
        else:
            await log_channel.send(log_message)
        await ctx.send("Ticket closed and logged.")
        try:
            user = await self.bot.fetch_user(int(user_id))
            await user.send(f"Your modmail ticket in {guild.name} has been closed.")
        except discord.Forbidden:
            await log_channel.send(f"Could not DM user {user_id} about ticket closure (DMs disabled or bot blocked).")
        except discord.NotFound:
            await log_channel.send(f"User {user_id} not found for ticket closure notification.")
        await ctx.channel.delete()

async def setup(bot: commands.Bot):
    await bot.add_cog(ModmailCog(bot))
