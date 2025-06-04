import discord
from discord.ext import commands
import sqlite3

class ReactionRolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def addcategory(self, ctx, category_name: str, *roles: discord.Role):
        """!addcategory <Category Name> <@Role1> <@Role2> ..."""
        if not roles:
            await ctx.send("Please mention at least one role for the category.")
            return
        role_ids = ",".join(str(role.id) for role in roles)
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO categories (category_name, role_ids) VALUES (?, ?)", 
                  (category_name.lower(), role_ids))
        conn.commit()
        conn.close()
        await ctx.send(f"Category '{category_name}' created with roles: {', '.join(role.name for role in roles)}")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def addreactionrole(self, ctx, message_id: int, emoji: str, role: discord.Role):
        """!addreactionrole <Message ID> <Emoji> <@Role>"""
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        c.execute("SELECT category_name, role_ids FROM categories")
        categories = c.fetchall()
        category = None
        for cat_name, role_ids in categories:
            if str(role.id) in role_ids.split(","):
                category = cat_name
                break
        c.execute("INSERT INTO reaction_roles (message_id, emoji, role_id, category) VALUES (?, ?, ?, ?)", 
                  (str(message_id), emoji, str(role.id), category))
        conn.commit()
        conn.close()
        message = await ctx.channel.fetch_message(message_id)
        await message.add_reaction(emoji)
        category_text = f" in category '{category}'" if category else " (no category)"
        await ctx.send(f"Added reaction role: {emoji} for {role.name}{category_text}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        emoji = str(payload.emoji) if payload.emoji.is_unicode_emoji() else f"<:{payload.emoji.name}:{payload.emoji.id}>"
        c.execute("SELECT role_id, category FROM reaction_roles WHERE message_id = ? AND emoji = ?", 
                  (str(payload.message_id), emoji))
        result = c.fetchone()
        if result:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                conn.close()
                return
            member = guild.get_member(payload.user_id)
            if not member:
                conn.close()
                return
            role = guild.get_role(int(result[0]))
            category = result[1]
            if role and role not in member.roles:
                if category:
                    c.execute("SELECT role_ids FROM categories WHERE category_name = ?", (category,))
                    category_roles = c.fetchone()
                    if category_roles:
                        role_ids = category_roles[0].split(",")
                        for role_id in role_ids:
                            other_role = guild.get_role(int(role_id))
                            if other_role and other_role in member.roles and other_role != role:
                                try:
                                    await member.remove_roles(other_role)
                                    try:
                                        await member.send(f"The '{other_role.name}' role was removed in {guild.name} due to selecting a new role in category '{category}'.")
                                    except discord.Forbidden:
                                        channel = guild.get_channel(payload.channel_id)
                                        if channel:
                                            await channel.send(f"Could not DM {member.mention} about role removal (DMs disabled).")
                                except discord.Forbidden:
                                    channel = guild.get_channel(payload.channel_id)
                                    if channel:
                                        await channel.send(f"Failed to remove role '{other_role.name}' from {member.mention} (bot lacks permissions).")
                try:
                    await member.add_roles(role)
                    try:
                        await member.send(f"You received the '{role.name}' role in {guild.name} via reaction{(' in category ' + category) if category else ''}.")
                    except discord.Forbidden:
                        channel = guild.get_channel(payload.channel_id)
                        if channel:
                            await channel.send(f"Could not DM {member.mention} about their new role (DMs disabled or bot blocked).")
                except discord.Forbidden:
                    channel = guild.get_channel(payload.channel_id)
                    if channel:
                        await channel.send(f"Failed to assign role '{role.name}' to {member.mention} (bot lacks permissions).")
        conn.close()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        emoji = str(payload.emoji) if payload.emoji.is_unicode_emoji() else f"<:{payload.emoji.name}:{payload.emoji.id}>"
        c.execute("SELECT role_id FROM reaction_roles WHERE message_id = ? AND emoji = ?", 
                  (str(payload.message_id), emoji))
        result = c.fetchone()
        if result:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                conn.close()
                return
            member = guild.get_member(payload.user_id)
            if not member:
                conn.close()
                return
            role = guild.get_role(int(result[0]))
            if role and role in member.roles:
                try:
                    await member.remove_roles(role)
                    try:
                        await member.send(f"The '{role.name}' role was removed in {guild.name} due to removing your reaction.")
                    except discord.Forbidden:
                        channel = guild.get_channel(payload.channel_id)
                        if channel:
                            await channel.send(f"Could not DM {member.mention} about role removal (DMs disabled).")
                except discord.Forbidden:
                    channel = guild.get_channel(payload.channel_id)
                    if channel:
                        await channel.send(f"Failed to remove role '{role.name}' from {member.mention} (bot lacks permissions).")
        conn.close()

async def setup(bot):
    await bot.add_cog(ReactionRolesCog(bot))
