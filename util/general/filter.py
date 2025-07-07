from discord.ext import commands
from util.core.utils import MockContext


class HelpFilter:
    @staticmethod
    async def organize_by_cog(bot, user=None, guild=None):
        """Organize commands by cog, filtering by user permissions."""
        cogs_with_commands = {}

        for cog_name, cog in bot.cogs.items():
            commands_list = []

            for cmd in cog.get_commands():
                if cmd.hidden:
                    continue

                # Check if user has permissions for this command
                if user and guild:
                    try:
                        can_run = await cmd.can_run(MockContext(user, guild, bot))
                        if not can_run:
                            continue
                    except commands.CommandError:
                        continue

                commands_list.append(cmd)

            if commands_list:
                cogs_with_commands[cog_name] = commands_list

        # Handle uncategorized commands
        uncategorized = []
        for cmd in bot.commands:
            if not cmd.cog_name and not cmd.hidden:
                if user and guild:
                    try:
                        can_run = await cmd.can_run(MockContext(user, guild, bot))
                        if can_run:
                            uncategorized.append(cmd)
                    except commands.CommandError:
                        continue
                else:
                    uncategorized.append(cmd)

        if uncategorized:
            cogs_with_commands["Uncategorized"] = uncategorized

        return cogs_with_commands
