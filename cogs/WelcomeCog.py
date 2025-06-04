import discord
from discord.ext import commands
import sqlite3
import random

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_channel_id = 1377733111844180000  # Channel to send welcome messages
        self.squad_channel_id = 1377841563257798727    # Channel to tag for (y)
        self.highlights_channel_id = 1377840380787036260  # Channel to fetch video messages from (z)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Step 1: Assign welcome roles (existing functionality)
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        c.execute("SELECT role_id FROM welcome_roles")
        role_ids = c.fetchall()
        conn.close()
        if role_ids:
            roles = [member.guild.get_role(int(role_id[0])) for role_id in role_ids if member.guild.get_role(int(role_id[0]))]
            if roles:
                try:
                    await member.add_roles(*roles, reason="Auto-assigned welcome roles")
                except discord.Forbidden:
                    channel = member.guild.system_channel or (await member.guild.text_channels())[0]
                    if channel:
                        await channel.send("Failed to assign welcome roles: Bot lacks permissions.")

        # Step 2: Send welcome message with embedded video URL
        # Get the welcome channel
        welcome_channel = self.bot.get_channel(self.welcome_channel_id)
        if not welcome_channel:
            return  # Channel not found; silently exit

        # Get the squad channel for tagging
        squad_channel = self.bot.get_channel(self.squad_channel_id)
        squad_channel_tag = f"<#{self.squad_channel_id}>" if squad_channel else "the squad channel"

        # Get the highlights channel for tagging
        highlights_channel = self.bot.get_channel(self.highlights_channel_id)
        highlights_channel_tag = f"<#{self.highlights_channel_id}>" if highlights_channel else "the highlights channel"

        # Fetch a random message with a video attachment from the highlights channel
        video_url = "a community highlight video"
        clip_author = "a community member"
        if highlights_channel:
            try:
                # Fetch up to 100 messages from the highlights channel
                messages = [message async for message in highlights_channel.history(limit=100)]
                # Filter for messages with video attachments
                video_messages = [
                    msg for msg in messages
                    if any(att.content_type.startswith("video/") for att in msg.attachments)
                ]
                if video_messages:
                    # Pick a random message
                    random_video_message = random.choice(video_messages)
                    # Get all video attachments from that message
                    video_attachments = [
                        att for att in random_video_message.attachments
                        if att.content_type.startswith("video/")
                    ]
                    # Pick a random video attachment
                    random_video_attachment = random.choice(video_attachments)
                    video_url = random_video_attachment.url  # Direct URL to the video
                    # Get the author of the clip
                    clip_author = random_video_message.author.display_name
            except discord.Forbidden:
                pass  # Bot lacks permissions to read the channel
            except discord.HTTPException:
                pass  # Other errors (e.g., rate limits)

        # Construct the welcome message
        welcome_message = (
            f"Welcome to the DMZ {member.mention}!\n"
            f"Please use {squad_channel_tag} to find a squad, or {highlights_channel_tag} to check out the community highlights!\n"
            f"Check out this clip from {clip_author}!\n{video_url}"
        )
        try:
            await welcome_channel.send(welcome_message)
        except discord.Forbidden:
            pass  # Bot lacks permissions to send messages in the welcome channel
        except discord.HTTPException:
            pass  # Other errors (e.g., rate limits)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def welcomeroles(self, ctx, *roles: discord.Role):
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        c.execute("DELETE FROM welcome_roles")
        if roles:
            for role in roles:
                c.execute("INSERT OR REPLACE INTO welcome_roles (role_id) VALUES (?)", (str(role.id),))
            role_names = ", ".join(role.name for role in roles)
            await ctx.send(f"Set welcome roles to: {role_names}")
        else:
            await ctx.send("Cleared welcome roles. New members will receive no roles.")
        conn.commit()
        conn.close()

async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))