import discord
from discord.ext import commands
import sqlite3
import asyncio
from discord.ext import tasks
import os

class ReactionRolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.category_role_map = {}  # Cache for category: [role_ids]
        self.monitor_reaction_roles.start()

    def cog_unload(self):
        self.monitor_reaction_roles.cancel()

    @tasks.loop(minutes=5)
    async def monitor_reaction_roles(self):
        await self.bot.wait_until_ready()
        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()
        c.execute("SELECT category_name, role_ids FROM categories")
        categories = c.fetchall()
        guild = self.bot.get_guild(int(os.getenv('GUILD_ID')))
        if not guild:
            conn.close()
            return

        for category_name, role_ids_str in categories:
            role_ids = [int(rid) for rid in role_ids_str.split(",") if rid]
            for member in guild.members:
                # Find which roles in this category the member has
                member_roles_in_cat = [guild.get_role(rid) for rid in role_ids if guild.get_role(rid) in member.roles]
                if len(member_roles_in_cat) > 1:
                    # Keep the first, remove the rest
                    to_remove = member_roles_in_cat[1:]
                    try:
                        await member.remove_roles(*to_remove, reason=f"Multiple roles in category '{category_name}' (auto-corrected)")
                        # Optionally, you can log this action to a channel or print
                    except discord.Forbidden:
                        pass  # Bot lacks permissions
        conn.close()

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def addcategory(self, ctx, category_name: str, *roles: discord.Role):
        """!addcategory <Category Name> <@Role1> <@Role2> ..."""
        if not roles:
            await ctx.send("Please mention at least one role for the category.")
            return
        role_ids = ",".join(str(role.id) for role in roles)
        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO categories (category_name, role_ids) VALUES (?, ?)", 
                  (category_name.lower(), role_ids))
        conn.commit()
        conn.close()
        await ctx.send(f"Category '{category_name}' created with roles: {', '.join(role.name for role in roles)}")

    @commands.command(name="clearreactionrole")
    @commands.has_permissions(manage_roles=True)
    async def clearreactionrole(self, ctx, message_id: int):
        """!clearreactionrole <Message ID>"""
        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()
        # Remove all reactions from the specified message
        message = None
        for channel in ctx.guild.text_channels:
            try:
                message = await channel.fetch_message(int(message_id))
                break
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                continue
        if message:
            try:
                await message.clear_reactions()
            except discord.Forbidden:
                await ctx.send(f"Could not clear reactions for message ID {message_id} (missing permissions).")
            except discord.HTTPException:
                await ctx.send(f"Failed to clear reactions for message ID {message_id}.")
        # Now clear the reaction_roles entries for this message
        c.execute("DELETE FROM reaction_roles WHERE message_id = ?", (str(message_id),))
        conn.commit()
        conn.close()
        await ctx.send(f"All reaction roles and reactions have been cleared for message ID {message_id}.")

    @commands.command(name="addreactionrole")
    @commands.has_permissions(manage_roles=True)
    async def addreactionrole(self, ctx, *args):
        """!addreactionrole <Message ID> <Emoji> <@Role> [<Emoji> <@Role> ...]"""
        if len(args) < 3 or len(args[1:]) % 2 != 0:
            await ctx.send("Usage: !addreactionrole <Message ID> <Emoji> <@Role> [<Emoji> <@Role> ...]")
            return

        message_id = int(args[0])
        pairs = []
        for i in range(1, len(args), 2):
            emoji = args[i]
            role_arg = args[i + 1]
            # Extract role ID from mention format <@&ROLE_ID>
            if role_arg.startswith("<@&") and role_arg.endswith(">"):
                role_id = int(role_arg[3:-1])
                role = ctx.guild.get_role(role_id)
                if not role:
                    await ctx.send(f"Role not found for mention: {role_arg}")
                    return
                pairs.append((emoji, role))
            else:
                await ctx.send(f"Invalid role mention: {role_arg}")
                return

        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()
        c.execute("SELECT category_name, role_ids FROM categories")
        categories = c.fetchall()

        # Try to find the message in all text channels
        message = None
        for channel in ctx.guild.text_channels:
            try:
                message = await channel.fetch_message(message_id)
                break
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                continue

        if not message:
            await ctx.send("Could not find the message with that ID in any text channel.")
            conn.close()
            return

        added_roles = []
        for emoji, role in pairs:
            category = None
            for cat_name, role_ids in categories:
                if str(role.id) in role_ids.split(","):
                    category = cat_name
                    break
            c.execute("INSERT INTO reaction_roles (message_id, emoji, role_id, category) VALUES (?, ?, ?, ?)", 
                      (str(message_id), emoji, str(role.id), category))
            await message.add_reaction(emoji)
            added_roles.append(f"{emoji} for {role.name}" + (f" in category '{category}'" if category else ""))
        conn.commit()
        conn.close()

        await ctx.send("Added reaction roles: " + ", ".join(added_roles))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        conn = sqlite3.connect('dmzcord.db')
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
                        # Remove other roles in the category
                        for role_id in role_ids:
                            other_role = guild.get_role(int(role_id))
                            if other_role and other_role in member.roles and other_role != role:
                                try:
                                    await member.remove_roles(other_role)
                                    # DM removed
                                except discord.Forbidden:
                                    channel = guild.get_channel(payload.channel_id)
                                    if channel:
                                        await channel.send(f"Failed to remove role '{other_role.name}' from {member.mention} (bot lacks permissions).")
                        # Remove other reactions in the category
                        channel = guild.get_channel(payload.channel_id)
                        if channel:
                            try:
                                message = await channel.fetch_message(payload.message_id)
                                c.execute("SELECT emoji FROM reaction_roles WHERE message_id = ? AND category = ?", (str(payload.message_id), category))
                                category_emojis = [row[0] for row in c.fetchall() if row[0] != emoji]
                                for other_emoji in category_emojis:
                                    for reaction in message.reactions:
                                        if (reaction.emoji == other_emoji) or (str(reaction.emoji) == other_emoji):
                                            users = [u async for u in reaction.users()]
                                            if any(u.id == payload.user_id for u in users):
                                                await message.remove_reaction(reaction.emoji, member)
                            except Exception:
                                pass
                try:
                    await member.add_roles(role)
                    # DM removed
                except discord.Forbidden:
                    channel = guild.get_channel(payload.channel_id)
                    if channel:
                        await channel.send(f"Failed to assign role '{role.name}' to {member.mention} (bot lacks permissions).")
        conn.close()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        conn = sqlite3.connect('dmzcord.db')
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
                    # DM removed
                except discord.Forbidden:
                    channel = guild.get_channel(payload.channel_id)
                    if channel:
                        await channel.send(f"Failed to remove role '{role.name}' from {member.mention} (bot lacks permissions).")
        conn.close()

async def setup(bot):
    await bot.add_cog(ReactionRolesCog(bot))
