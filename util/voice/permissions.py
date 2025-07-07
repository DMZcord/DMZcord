import discord

class Permissions:
    @staticmethod
    def is_owner(ctx):
        return ctx.author.id == ctx.guild.owner_id

    @staticmethod
    def is_mod(ctx):
        perms = ctx.author.guild_permissions
        return perms.manage_guild or perms.manage_messages

    @staticmethod
    def has_premium(ctx):
        premium_role = discord.utils.get(ctx.guild.roles, name="Premium Members")
        return premium_role in ctx.author.roles if premium_role else False
