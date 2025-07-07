import discord
from discord.ui import Button, Select
from typing import Dict

class DeferButton(discord.ui.Button):
    """Generic defer button"""
    async def callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer()

class HelpCategorySelect(discord.ui.Select):
    """Select menu for choosing help categories/cogs"""
    def __init__(self, parent_view, options):
        super().__init__(placeholder="Choose a category...",
                         options=options, min_values=1, max_values=1)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_cog = self.values[0]
        await self.parent_view.show_cog_commands(selected_cog)

class HelpCommandSelect(discord.ui.Select):
    """Select menu for choosing commands within a category"""
    def __init__(self, parent_view, options):
        super().__init__(placeholder="Choose a command...",
                         options=options, min_values=1, max_values=1)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_command = self.values[0]
        command = self.parent_view.help_cog.bot.get_command(selected_command)
        if command:
            from util.general.embeds import HelpEmbed
            from util.general.views import HelpCommandView  # Updated import
            embed = HelpEmbed.build_command_help_embed(command, self.parent_view.user)
            back_view = HelpCommandView(  # Updated class name
                self.parent_view.help_cog,
                self.parent_view.ctx,
                self.parent_view.commands_list,
                self.parent_view.is_slash,
                self.parent_view.cog_name,
                self.parent_view.user,
                self.parent_view.message_id,
                self.parent_view.author_id
            )
            if self.parent_view.is_slash and hasattr(self.parent_view.ctx, "interaction") and self.parent_view.ctx.interaction:
                await self.parent_view.ctx.interaction.edit_original_response(embed=embed, view=back_view)
            else:
                channel = self.parent_view.ctx.channel
                message = await channel.fetch_message(self.parent_view.message_id)
                await message.edit(embed=embed, view=back_view)

class HelpMainMenuButton(discord.ui.Button):
    """Button to go back to main help menu"""
    def __init__(self):
        super().__init__(label="← Back to Main Help", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        from util.general.helpers import GeneralHelpers
        from util.general.embeds import HelpEmbed
        from util.general.views import HelpMainView  # Updated import
        
        user = interaction.user
        ctx = self.view.ctx
        viewable_commands = []
        for cmd in self.view.help_cog.bot.commands:
            if await GeneralHelpers.filter_help_commands(cmd, ctx, self.view.help_cog.bot):
                viewable_commands.append(cmd)
        cogs_with_commands = await HelpEmbed.organize_help_embed(
            self.view.help_cog.bot, commands_list=viewable_commands
        )
        embed = HelpEmbed.build_main_help_embed(cogs_with_commands, user)
        new_view = HelpMainView(self.view.help_cog, ctx, cogs_with_commands, self.view.is_slash, self.view.message_id, self.view.author_id)  # Updated class name
        await interaction.response.edit_message(embed=embed, view=new_view)

class HelpCategoryBackButton(discord.ui.Button):
    """Button to go back to a specific help category"""
    def __init__(self, category_name: str):
        super().__init__(label=f"← Back to {category_name}", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        from util.general.embeds import HelpEmbed
        from util.general.views import HelpCategoryView  # Updated import
        
        await interaction.response.defer()
        commands_desc = "\n".join(
            f"**/{cmd.qualified_name}**: {cmd.description or (cmd.help.splitlines()[0] if cmd.help else 'No description')}"
            for cmd in self.view.commands_list
        )
        embed = HelpEmbed.build_category_help_embed(self.view.cog_name, commands_desc, self.view.user)
        new_view = HelpCategoryView(  # Updated class name
            self.view.help_cog, self.view.ctx, self.view.commands_list, self.view.is_slash, 
            self.view.cog_name, self.view.user, self.view.message_id, self.view.author_id
        )
        if self.view.is_slash:
            await interaction.edit_original_response(embed=embed, view=new_view)
        else:
            channel = self.view.ctx.channel
            message = await channel.fetch_message(self.view.message_id)
            await message.edit(embed=embed, view=new_view)

class ConfirmButton(discord.ui.Button):
    """Generic confirm button"""
    def __init__(self, label: str = "Confirm", style: discord.ButtonStyle = discord.ButtonStyle.danger):
        super().__init__(label=label, style=style)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.author.id:
            await interaction.response.send_message("Only the command invoker can confirm.", ephemeral=True)
            return
        self.view.value = True
        for item in self.view.children:
            item.disabled = True
        await interaction.response.edit_message(content="Proceeding...", view=None)
        self.view.stop()

class CancelButton(discord.ui.Button):
    """Generic cancel button"""
    def __init__(self, label: str = "Cancel", style: discord.ButtonStyle = discord.ButtonStyle.secondary):
        super().__init__(label=label, style=style)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.author.id:
            await interaction.response.send_message("Only the command invoker can cancel.", ephemeral=True)
            return
        self.view.value = False
        for item in self.view.children:
            item.disabled = True
        await interaction.response.edit_message(content="Cancelled.", view=None)
        self.view.stop()

class UncacheSourceButton(discord.ui.Button):
    """Button for selecting uncache source"""
    def __init__(self, source: str, emoji: str, label: str):
        super().__init__(label=f"{emoji} {label}", style=discord.ButtonStyle.primary)
        self.source = source

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.ctx.author.id:
            await interaction.response.send_message("You can't use this button.", ephemeral=True)
            return

        if self.view.global_counts[self.source] == 0:
            await interaction.response.send_message(f"No {self.label.split()[-1]} loadouts found.", ephemeral=True)
            return

        self.view.selected_source = self.source
        await self.view.show_scope_selection(interaction)

class UncacheScopeButton(discord.ui.Button):
    """Button for selecting uncache scope"""
    def __init__(self, scope: str, emoji: str, label: str):
        super().__init__(label=f"{emoji} {label}", style=discord.ButtonStyle.danger)
        self.scope = scope

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.ctx.author.id:
            await interaction.response.send_message("You can't use this button.", ephemeral=True)
            return

        count = self.view.guild_count if self.scope == "guild" else self.view.global_count
        if count == 0:
            scope_name = "in this server" if self.scope == "guild" else "globally"
            await interaction.response.send_message(f"No loadouts to remove {scope_name}.", ephemeral=True)
            return

        await self.view.perform_uncache(interaction, scope=self.scope)

class UncacheBackButton(discord.ui.Button):
    """Back button for uncache views"""
    def __init__(self):
        super().__init__(label="← Back", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.ctx.author.id:
            await interaction.response.send_message("You can't use this button.", ephemeral=True)
            return
        
        from util.community.cache import LoadoutCacheHelper
        from util.general.views import UncacheViews
        
        embed = LoadoutCacheHelper.create_loadout_summary_embed(
            self.view.username, self.view.ctx.guild.name,
            {"wzhub": 0, "user": 0}, {"wzhub": 0, "user": 0}
        )
        source_view = UncacheViews.SourceSelectionView(
            self.view.ctx, self.view.username, {}, {})
        await interaction.response.edit_message(embed=embed, view=source_view)
        self.view.stop()

class UncacheCancelButton(discord.ui.Button):
    """Cancel button for uncache operations"""
    def __init__(self):
        super().__init__(label="❌ Cancel", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.ctx.author.id:
            await interaction.response.send_message("You can't use this button.", ephemeral=True)
            return
        await interaction.response.edit_message(content="❌ Uncache cancelled.", embed=None, view=None)
        self.view.stop()
