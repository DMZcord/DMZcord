import discord
from discord.ext import commands
import sqlite3
import random
from cogs.utils import get_setting

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        conn = sqlite3.connect('dmzcord.db')
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

        # Fetch channel IDs from settings
        welcome_channel_id = get_setting('welcome_channel_id')
        if not welcome_channel_id:
            return  # Welcome channel not set; silently exit

        welcome_channel = self.bot.get_channel(int(welcome_channel_id))
        if not welcome_channel:
            return

        squad_channel_id = get_setting('squad_channel_id')
        squad_channel = self.bot.get_channel(int(squad_channel_id)) if squad_channel_id else None
        squad_channel_tag = f"<#{squad_channel_id}>" if squad_channel else "the squad channel"

        highlights_channel_id = get_setting('highlights_channel_id')
        highlights_channel = self.bot.get_channel(int(highlights_channel_id)) if highlights_channel_id else None
        highlights_channel_tag = f"<#{highlights_channel_id}>" if highlights_channel else "the highlights channel"

        video_url = "a community highlight video"
        clip_author = "a community member"
        if highlights_channel:
            try:
                messages = [message async for message in highlights_channel.history(limit=100)]
                video_messages = [
                    msg for msg in messages
                    if any(att.content_type.startswith("video/") for att in msg.attachments)
                ]
                if video_messages:
                    random_video_message = random.choice(video_messages)
                    video_attachments = [
                        att for att in random_video_message.attachments
                        if att.content_type.startswith("video/")
                    ]
                    random_video_attachment = random.choice(video_attachments)
                    video_url = random_video_attachment.url
                    clip_author = random_video_message.author.display_name
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

        welcome_message = (
            f"Welcome to the DMZ {member.mention}! Please use {squad_channel_tag} to find a squad, or {highlights_channel_tag} to check out the community highlights!\n"
            f"Check out this video from {clip_author}!\n{video_url}"
        )
        try:
            await welcome_channel.send(welcome_message)
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def welcomeroles(self, ctx, *roles: discord.Role):
        """!welcomeroles <role1> <role2> ... """
        conn = sqlite3.connect('dmzcord.db')
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
