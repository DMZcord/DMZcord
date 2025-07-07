import discord
from discord.ext import commands
from util.core import DiscordHelper
from util.owner import DebugHelpers, DebugPaginator, DebugEmbeds, CogActionView, AttachmentUtils, DebugLoadouts, DebugStats

class DebugSelect(discord.ui.Select):
    def __init__(self, bot, author):
        options = [
            discord.SelectOption(label="Attachments", description="List all available attachment types per gun"),
            discord.SelectOption(label="Loadouts", description="Test random loadout generation"),
            discord.SelectOption(label="Command Stats", description="Show command usage stats"),
            discord.SelectOption(label="Command Abuse", description="Show most active and most blacklisted users"),
            discord.SelectOption(label="Cogs", description="List and manage cogs/extensions")
        ]
        super().__init__(placeholder="Choose a debug option...", min_values=1, max_values=1, options=options)
        self.bot = bot
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Only the command invoker can use this menu.", ephemeral=True)
            return

        selection = self.values[0]
        if selection == "Attachments":
            tables = AttachmentUtils.get_gun_attachment_count_tables_by_class()
            pages = []
            for table in tables:
                # table is already a string with code block, don't wrap again
                if len(table) > 1900:
                    subpages = DebugHelpers.paginate_lines(table.splitlines())
                    # Join subpages into code blocks for Discord
                    subpages = [f"```markdown\n{chr(10).join(sub)}\n```" for sub in subpages]
                    pages.extend(subpages)
                else:
                    pages.append(table)
            if len(pages) > 1:
                paginator = DebugPaginator(pages, self.author.id)
                await interaction.response.edit_message(content=pages[0], embed=None, view=paginator)
            else:
                await interaction.response.edit_message(content=pages[0], embed=None, view=self.view)
        elif selection == "Loadouts":
            success, failed = await DebugLoadouts.test_random_loadouts()
            if success:
                await interaction.response.edit_message(content="✅ All guns successfully generated a random loadout.", embed=None, view=self.view)
            else:
                lines = ["**Random loadout failures:**"] + failed
                pages = DebugHelpers.paginate_lines(lines)
                if len(pages) > 1:
                    paginator = DebugPaginator(pages, self.author.id)
                    await interaction.response.edit_message(content="\n".join(pages[0]), embed=None, view=paginator)
                else:
                    await interaction.response.edit_message(content="\n".join(pages[0]), embed=None, view=self.view)
        elif selection == "Command Stats":
            stats = await DebugStats.get_command_stats_with_times(self.bot)
            if not stats:
                await interaction.response.edit_message(content="No commands have been run yet.", embed=None, view=self.view)
                return
            stats = sorted(stats, key=lambda s: s['command_name'].lower())
            embed = DebugEmbeds.build_commandstats_embed(stats)
            await interaction.response.edit_message(content=None, embed=embed, view=self.view)
        elif selection == "Command Abuse":
            stats = await DebugStats.get_command_abuse_stats(self.bot, limit=10)
            if not stats:
                await interaction.response.edit_message(content="No command logs found.", embed=None, view=self.view)
                return
            blacklist_stats = await DebugStats.get_most_blacklisted_users(self.bot, limit=5)
            embed = await DebugEmbeds.build_commandabuse_embed(stats, blacklist_stats, self.bot)
            await interaction.response.edit_message(content=None, embed=embed, view=self.view)
        elif selection == "Cogs":
            all_extensions = DebugHelpers.find_cog_extensions()
            embed = DebugEmbeds.build_status_embed(self.bot, all_extensions)
            await interaction.response.edit_message(content=None, embed=embed, view=CogActionView(self.bot, all_extensions))

class DebugMenuView(discord.ui.View):
    def __init__(self, bot, author):
        super().__init__(timeout=120)
        self.add_item(DebugSelect(bot, author))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        select = self.children[0]
        if interaction.user.id != select.author.id:
            await interaction.response.send_message("Only the command invoker can use this menu.", ephemeral=True)
            return False
        return True

class DebugCog(commands.Cog):
    """Cog for debugging bot functionality."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="debug", description="Open the debug menu")
    @commands.is_owner()
    async def debug(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Debug Menu",
            description=(
                "Choose an option from the menu below:\n"
                "• **Attachments**: List all available attachment types per gun\n"
                "• **Loadouts**: Test random loadout generation\n"
                "• **Command Stats**: Show command usage stats\n"
                "• **Command Abuse**: Show most active and most blacklisted users\n"
                "• **Cogs**: List and manage cogs/extensions"
            ),
            color=discord.Color.blurple()
        )
        view = DebugMenuView(self.bot, ctx.author)
        await DiscordHelper.respond(ctx, "", embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(DebugCog(bot))
