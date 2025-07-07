import discord
from util.general.helpers import GeneralHelpers


def build_command_signature(command):
    """
    Build a usage signature string for a command, including its parameters.
    """
    params = []
    for name, param in command.clean_params.items():
        # If the parameter has a default value, it's optional
        if param.default is not param.empty:
            params.append(f"[{name}]")
        else:
            params.append(f"<{name}>")
    return f"{command.qualified_name} {' '.join(params)}"


class HelpEmbed:
    """Centralized embed builder for Discord bot"""

    Help_Thumbnail = "https://cdn.discordapp.com/attachments/1377733230857551956/1391580014281228430/raw.png?ex=686c6961&is=686b17e1&hm=062761aa47a991b8efd7badcefd57b7cf57d42a54d481974b8d665a165068d1d&"
    Help_Links = "💬 [Support Server](https://discord.gg/CHUynnZdae) 📖 [All Commands](https://github.com/DMZcord/DMZcord/blob/main/README.md) 🐞 [Report a Bug](https://github.com/DMZcord/DMZcord/issues)"

    @staticmethod
    def build_command_help_embed(command, user):
        """Build help embed for a specific command."""
        usage = build_command_signature(command)  # Use the centralized function
        embed = discord.Embed(
            title=f"**Help:** `/{command.qualified_name}`",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=HelpEmbed.Help_Thumbnail)  # Add thumbnail
        embed.add_field(
            name="**Description**",
            value=command.description or (command.help.splitlines()[0] if command.help else "No description provided."),
            inline=False
        )
        embed.add_field(name="**Usage**", value=f"`/{usage}`", inline=False)

        if command.aliases:
            embed.add_field(
                name="**Aliases**",
                value=", ".join(f"`{a}`" for a in command.aliases),
                inline=False
            )
        embed.add_field(
            name="\u200b",
            value=HelpEmbed.Help_Links,
            inline=False
        )
        embed.set_footer(
            text="< > inputs are required, [ ] inputs are optional",
            icon_url=user.display_avatar.url
        )
        return embed

    @staticmethod
    def build_main_help_embed(cogs_with_commands, user):
        """Build main help embed with all categories."""
        embed = discord.Embed(
            title="DMZcord Help",
            description="**Select a category to view its commands:**\n\u200b",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=HelpEmbed.Help_Thumbnail)

        for cog_name, commands_list in cogs_with_commands.items():
            display_name = cog_name[:-3] if cog_name.lower().endswith("cog") else cog_name
            embed.add_field(
                name=f"__**{display_name}**__",
                value=f"{len(commands_list)} commands",
                inline=True
            )
        # Add all links field
        embed.add_field(
            name="\u200b",
            value=HelpEmbed.Help_Links,
            inline=False
        )

        embed.set_footer(
            text=f"Requested by {user} | ID: {user.id}",
            icon_url=user.display_avatar.url
        )
        return embed

    @staticmethod
    async def organize_help_embed(bot, commands_list=None):
        """
        Organize commands by cog for the help overview.
        Only include commands that are not hidden and not owner-only.
        """
        if commands_list is None:
            commands_list = bot.commands
        cogs = {}
        for command in commands_list:
            if command.hidden or getattr(command, "owner_only", False):
                continue
            cog_name = command.cog_name or "No Category"
            cogs.setdefault(cog_name, []).append(command)
        return cogs

    @staticmethod
    def build_category_help_embed(cog_name, commands_desc, user):
        """Build help embed for a category of commands."""
        embed = discord.Embed(
            title=f"**{cog_name} Commands**",
            description=commands_desc,
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=HelpEmbed.Help_Thumbnail)  # Add thumbnail
        embed.add_field(
            name="\u200b",
            value=HelpEmbed.Help_Links,
            inline=False
        )
        embed.set_footer(
            text="Select a command below for detailed help, or go back to categories.",
            icon_url=user.display_avatar.url
        )
        return embed


class ClearEmbed:
    @staticmethod
    def build_old_message_confirm_embed(full_count, old_count, est_time, bot_user=None):
        est_str = f"Estimated time: {est_time} seconds ({est_time//60}m {est_time % 60}s)"
        embed = discord.Embed(
            title="⚠️ Some messages are older than 14 days ⚠️",
            description=(
                f"Are you sure you want to delete **{full_count}** messages? This action cannot be undone.\n"
                f"**{old_count}** messages are older than 14 days and must be deleted slowly\n\n"
                f"**{est_str}**"
            ),
            color=discord.Color.orange()
        )
        bot_icon = bot_user.display_avatar.url if bot_user else None
        embed.set_footer(
            text="⚠️ Discord API rate limits messages older than 14 days to 5 deletions per second",
            icon_url=bot_icon
        )
        return embed

    @staticmethod
    def build_confirm_embed(count, est_time, bot_user=None):
        est_str = ""
        if est_time is not None:
            est_str = f"Estimated time: {est_time} seconds ({est_time//60}m {est_time % 60}s)"
        embed = discord.Embed(
            title="⚠️ Confirm Message Deletion ⚠️",
            description=(
                f"Are you sure you want to delete **{count}** messages? This action cannot be undone.\n\n"
                f"**{est_str}**"
            ),
            color=discord.Color.blue()
        )
        bot_icon = bot_user.display_avatar.url if bot_user else None
        embed.set_footer(
            text="⚠️ Discord API rate limits messages within the past 14 days to 100 deletions per second",
            icon_url=bot_icon
        )
        return embed
