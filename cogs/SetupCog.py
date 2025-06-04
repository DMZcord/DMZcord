import discord
from discord.ext import commands
import sqlite3
import asyncio

class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def wait_for_response(self, ctx, prompt, timeout=60):
        await ctx.send(prompt)
        try:
            response = await self.bot.wait_for(
                'message',
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=timeout
            )
            return response.content.strip()
        except asyncio.TimeoutError:
            await ctx.send("⏰ Timed out waiting for response. Please run `!setup` again.")
            return None

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        """Sets up the DMZcord bot by asking for channel IDs and bot activity."""
        await ctx.send(
            "Starting setup process for DMZcord bot. I'll ask for channel IDs and bot activity. "
            "You have 60 seconds to respond to each prompt. Type 'skip' to leave a setting unchanged or empty."
        )

        settings = [
            ('welcome_channel_id', "Enter the channel ID for sending welcome messages (or 'skip'):"),
            ('squad_channel_id', "Enter the channel ID for the LFG channel to link in welcome messages (or 'skip'):"),
            ('highlights_channel_id', "Enter the channel ID for fetching community clips (or 'skip'):"),
            ('log_channel_id', "Enter the channel ID for sending moderator logs (from !clear) (or 'skip'):")
        ]

        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()

        for key, prompt in settings:
            response = await self.wait_for_response(ctx, prompt)
            if response is None:
                conn.close()
                return
            if response.lower() == 'skip':
                continue
            # Validate channel/user ID (must be numeric)
            if not response.isdigit():
                await ctx.send(f"❌ Invalid ID for {key}. Must be a numeric ID. Skipping this setting.")
                continue
            # Store the setting
            c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, response))
            await ctx.send(f"✅ Set {key} to {response}")

        # Ask for bot status
        status_prompt = (
            "Enter the bot's status (online, idle, dnd, invisible) (or 'skip' to leave unchanged):"
        )
        status_response = await self.wait_for_response(ctx, status_prompt)
        valid_statuses = ["online", "idle", "dnd", "invisible"]
        status = None
        if status_response and status_response.lower() in valid_statuses:
            status = status_response.lower()
        elif status_response and status_response.lower() != "skip":
            await ctx.send("❌ Invalid status. Skipping status setting.")

        # Ask for activity type
        activity_type_prompt = (
            "Enter the bot's activity type (playing, listening, watching, streaming) (or 'skip' to leave unchanged):"
        )
        valid_activity_types = ["playing", "listening", "watching", "streaming"]
        activity_type_response = await self.wait_for_response(ctx, activity_type_prompt)
        activity_type = None
        if activity_type_response and activity_type_response.lower() in valid_activity_types:
            activity_type = activity_type_response.lower()
        elif activity_type_response and activity_type_response.lower() != "skip":
            await ctx.send("❌ Invalid activity type. Skipping activity type setting.")

        # Ask for activity text
        activity_prompt = (
            "Enter the bot's activity text (or 'skip' to leave unchanged):"
        )
        activity_response = await self.wait_for_response(ctx, activity_prompt)
        activity = activity_response if activity_response and activity_response.lower() != "skip" else None

        # Save status/activity to settings
        if status:
            c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("bot_status", status))
            await ctx.send(f"✅ Set bot status to {status}")
        if activity_type:
            c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("bot_activity_type", activity_type))
            await ctx.send(f"✅ Set bot activity type to: {activity_type}")
        if activity:
            c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("bot_activity", activity))
            await ctx.send(f"✅ Set bot activity to: {activity}")

        # Always set support_user_id to the bot's user ID
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("support_user_id", str(self.bot.user.id)))
        await ctx.send(f"✅ Set support_user_id to the bot's user ID: {self.bot.user.id}")

        conn.commit()
        conn.close()
        await ctx.send("🎉 Setup complete! The bot is now configured. You can run `!setup` again to update any settings.")

        # Optionally, update the bot's presence immediately
        if status or activity_type or activity:
            status_map = {
                "online": discord.Status.online,
                "idle": discord.Status.idle,
                "dnd": discord.Status.dnd,
                "invisible": discord.Status.invisible
            }
            activity_type_map = {
                "playing": discord.ActivityType.playing,
                "watching": discord.ActivityType.watching,
                "listening": discord.ActivityType.listening,
                "streaming": discord.ActivityType.streaming
            }
            discord_status = status_map.get(status, discord.Status.online)
            discord_activity_type = activity_type_map.get(activity_type, discord.ActivityType.playing)
            activity_obj = None
            if activity:
                if activity_type == "streaming":
                    activity_obj = discord.Streaming(name=activity, url="https://twitch.tv/")
                else:
                    activity_obj = discord.Activity(type=discord_activity_type, name=activity)
            await self.bot.change_presence(status=discord_status, activity=activity_obj)

    @commands.command(name="audit")
    @commands.has_permissions(administrator=True)
    async def audit(self, ctx):
        """Lists all commands and their requirements."""
        lines = ["**Available Commands and Requirements:**"]
        for command in self.bot.commands:
            if command.hidden:
                continue
            perms = []
            # Check for permission decorators
            if hasattr(command, "checks") and command.checks:
                for check in command.checks:
                    qualname = getattr(check, "__qualname__", "")
                    if "has_permissions" in qualname or "has_guild_permissions" in qualname:
                        perms.append("Requires Permissions")
                    if "is_owner" in qualname:
                        perms.append("Bot Owner Only")
            # Try to get permission names from the command's checks
            doc = command.help or command.short_doc or "No description provided."
            perms_str = ", ".join(set(perms)) if perms else "None"
            lines.append(f"**!{command.name}**: {doc}\nRequirements: {perms_str}")
        await ctx.send("\n\n".join(lines))

async def setup(bot):
    await bot.add_cog(SetupCog(bot))