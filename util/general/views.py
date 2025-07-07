import discord
from discord.ui import View
from util.general.embeds import HelpEmbed
from util.general.helpers import GeneralHelpers
from util.general.buttons import (
    HelpCategorySelect, HelpCommandSelect, HelpMainMenuButton, HelpCategoryBackButton,
    ConfirmButton, CancelButton, UncacheSourceButton, UncacheScopeButton,
    UncacheBackButton, UncacheCancelButton
)
from typing import Dict
import logging
from util.community.cache import LoadoutCacheHelper

logger = logging.getLogger(__name__)

async def on_timeout(self):
    try:
        channel = self.ctx.channel
        message = await channel.fetch_message(self.message_id)
        await message.delete()
    except discord.NotFound:
        pass

class BaseRestrictedView(View):
    """Base view class with common interaction checking logic"""
    def __init__(self, author_id: int, message_id: int = None, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.message_id = message_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Check if user is authorized
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the user who invoked this command can use these buttons.",
                ephemeral=True
            )
            return False
        
        # Check if message is still valid (if message_id is provided)
        if self.message_id and interaction.message.id != self.message_id:
            await interaction.response.send_message(
                "This view is no longer valid.",
                ephemeral=True
            )
            return False
        
        return True

class BaseAuthorView(View):
    """Base view class that only checks author (no message validation)"""
    def __init__(self, author_id: int, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the command invoker can use this.",
                ephemeral=True
            )
            return False
        return True

class HelpMainView(BaseRestrictedView):
    """Main help view with category selection"""
    def __init__(self, help_cog, ctx, cogs_with_commands, is_slash, message_id, author_id, timeout=600):
        super().__init__(author_id, message_id, timeout)
        self.help_cog = help_cog
        self.ctx = ctx
        self.cogs_with_commands = cogs_with_commands
        self.is_slash = is_slash
        self.user = ctx.author if not is_slash else ctx.interaction.user

        self.add_cog_selector()

    def add_cog_selector(self):
        options = []
        # Sort cog names alphabetically for the selection menu
        for cog_name in sorted(self.cogs_with_commands.keys(), key=str.lower):
            display_name = cog_name[:-3] if cog_name.lower().endswith("cog") else cog_name
            options.append(discord.SelectOption(
                label=display_name,
                description=f"{len(self.cogs_with_commands[cog_name])} commands",
                value=cog_name
            ))
        if options:
            select = HelpCategorySelect(self, options)
            self.add_item(select)

    async def show_cog_commands(self, cog_name):
        """Show commands for a specific cog"""
        commands_list = self.cogs_with_commands[cog_name]
        display_name = cog_name[:-3] if cog_name.lower().endswith("cog") else cog_name
        
        # Sort commands alphabetically in the description
        sorted_commands = sorted(commands_list, key=lambda cmd: cmd.qualified_name.lower())
        commands_desc = "\n".join(
            f"**/{cmd.qualified_name}**: {cmd.description or (cmd.help.splitlines()[0] if cmd.help else 'No description')}"
            for cmd in sorted_commands
        )
        embed = HelpEmbed.build_category_help_embed(display_name, commands_desc, self.user)
        new_view = HelpCategoryView(
            self.help_cog, self.ctx, sorted_commands, self.is_slash, display_name, self.user, self.message_id, self.author_id
        )
        if self.is_slash and hasattr(self.ctx, "interaction") and self.ctx.interaction:
            await self.ctx.interaction.edit_original_response(embed=embed, view=new_view)
        else:
            channel = self.ctx.channel
            message = await channel.fetch_message(self.message_id)
            await message.edit(embed=embed, view=new_view)

class HelpCategoryView(BaseRestrictedView):
    """View for showing commands within a category"""
    def __init__(self, help_cog, ctx, commands_list, is_slash, cog_name, user, message_id, author_id):
        super().__init__(author_id, message_id, 120)
        self.help_cog = help_cog
        self.ctx = ctx
        self.commands_list = commands_list
        self.is_slash = is_slash
        self.cog_name = cog_name[:-3] if cog_name.lower().endswith("cog") else cog_name
        self.user = user
        self.add_command_selector()
        self.add_item(HelpMainMenuButton())

    def add_command_selector(self):
        options = []
        # Sort commands alphabetically for the selection menu
        sorted_commands = sorted(self.commands_list[:25], key=lambda cmd: cmd.qualified_name.lower())
        for cmd in sorted_commands:
            description = cmd.description[:100] if cmd.description else (cmd.help.splitlines()[0][:100] if cmd.help else "No description available")
            options.append(discord.SelectOption(
                label=cmd.qualified_name,
                description=description,
                value=cmd.qualified_name
            ))
        if options:
            select = HelpCommandSelect(self, options)
            self.add_item(select)

class HelpCommandView(BaseRestrictedView):
    """View for individual command help with back button"""
    def __init__(self, help_cog, ctx, commands_list, is_slash, cog_name, user, message_id, author_id):
        super().__init__(author_id, message_id, 120)
        self.help_cog = help_cog
        self.ctx = ctx
        self.commands_list = commands_list
        self.is_slash = is_slash
        self.cog_name = cog_name[:-3] if cog_name.lower().endswith("cog") else cog_name
        self.user = user

        # Add the back button
        self.add_item(HelpCategoryBackButton(self.cog_name))

class UncacheViews:
    """UI Views for uncache command"""

    class SourceSelectionView(BaseAuthorView):
        def __init__(self, ctx, target_username: str, guild_counts: Dict[str, int], global_counts: Dict[str, int]):
            super().__init__(ctx.author.id, 60)
            self.ctx = ctx
            self.target_username = target_username
            self.guild_counts = guild_counts
            self.global_counts = global_counts
            self.selected_source = None

            # Add source buttons
            wzhub_btn = UncacheSourceButton("wzhub", "🌐", "Wzhub.gg")
            dmzcord_btn = UncacheSourceButton("user", "🛠️", "DMZcord")
            cancel_btn = UncacheCancelButton()

            # Disable buttons based on loadout counts
            if global_counts["wzhub"] == 0:
                wzhub_btn.disabled = True
            if global_counts["user"] == 0:
                dmzcord_btn.disabled = True

            self.add_item(wzhub_btn)
            self.add_item(dmzcord_btn)
            self.add_item(cancel_btn)

        async def show_scope_selection(self, interaction):
            source_name = "Wzhub.gg" if self.selected_source == "wzhub" else "DMZcord"
            guild_count = self.guild_counts[self.selected_source]
            global_count = self.global_counts[self.selected_source]

            scope_embed = discord.Embed(
                title=f"Remove {source_name} Loadouts",
                color=discord.Color.red(),
                description=f"Choose scope for removing {source_name} loadouts:"
            )

            scope_embed.add_field(
                name=f"This Server ({self.ctx.guild.name})",
                value=f"{guild_count} loadouts",
                inline=True
            )

            scope_embed.add_field(
                name="All Servers (Global)",
                value=f"{global_count} loadouts",
                inline=True
            )

            scope_view = UncacheViews.ScopeSelectionView(
                self.ctx, self.target_username, self.selected_source,
                guild_count, global_count
            )
            await interaction.response.edit_message(embed=scope_embed, view=scope_view)
            self.stop()

    class ScopeSelectionView(BaseAuthorView):
        def __init__(self, ctx, username: str, source: str, guild_count: int, global_count: int):
            super().__init__(ctx.author.id, 60)
            self.ctx = ctx
            self.username = username
            self.source = source
            self.guild_count = guild_count
            self.global_count = global_count

            # Add scope buttons
            guild_btn = UncacheScopeButton("guild", "🏠", "This Server")
            global_btn = UncacheScopeButton("global", "🌍", "All Servers")
            back_btn = UncacheBackButton()

            # Disable buttons based on loadout counts
            if guild_count == 0:
                guild_btn.disabled = True
            if global_count == 0:
                global_btn.disabled = True

            self.add_item(guild_btn)
            self.add_item(global_btn)
            self.add_item(back_btn)

        async def perform_uncache(self, interaction, scope):
            source_name = "Wzhub.gg" if self.source == "wzhub" else "DMZcord"
            scope_name = "this server" if scope == "guild" else "all servers"

            await interaction.response.edit_message(
                content=f"🔄 Removing {source_name} loadouts from {scope_name}...",
                embed=None, view=None
            )

            success = await LoadoutCacheHelper.remove_loadouts_by_source(
                self.ctx.bot, self.username, self.source, scope,
                str(self.ctx.guild.id) if scope == "guild" else None
            )

            if success:
                if scope == "guild":
                    message = f"✅ Removed {source_name} loadouts for `{self.username}` from {self.ctx.guild.name}."
                else:
                    message = f"✅ Removed {source_name} loadouts for `{self.username}` from all servers."
            else:
                message = f"❌ Error removing {source_name} loadouts."

            await interaction.edit_original_response(content=message)
            self.stop()

class OldMessageConfirmView(BaseAuthorView):
    """Confirmation view for old message operations"""
    def __init__(self, estimated_seconds, author, timeout=60):
        super().__init__(author.id, timeout)
        self.value = None
        self.estimated_seconds = estimated_seconds
        self.author = author

        self.add_item(ConfirmButton("Proceed", discord.ButtonStyle.danger))
        self.add_item(CancelButton())

class ConfirmDeleteView(BaseAuthorView):
    """Generic confirmation view for delete operations"""
    def __init__(self, author, timeout=60):
        super().__init__(author.id, timeout)
        self.value = None
        self.author = author

        self.add_item(ConfirmButton())
        self.add_item(CancelButton())

# Set timeout handlers
HelpMainView.on_timeout = on_timeout
HelpCategoryView.on_timeout = on_timeout
HelpCommandView.on_timeout = on_timeout