import discord
from typing import List
import time
import logging
from util.owner.embeds import DebugEmbeds
from util.owner.helpers import DebugHelpers

class DebugPaginator(discord.ui.View):
    """Paginator for debug command outputs"""
    
    def __init__(self, pages: List[str], author_id: int):
        super().__init__(timeout=120)
        self.pages = pages
        self.page = 0
        self.author_id = author_id
        
        # Set initial button states
        self._update_button_states()
    
    def _update_button_states(self):
        """Update button enabled/disabled states"""
        self.first.disabled = self.page == 0
        self.previous.disabled = self.page == 0
        self.next.disabled = self.page == len(self.pages) - 1 or len(self.pages) <= 1
        self.last.disabled = self.page == len(self.pages) - 1 or len(self.pages) <= 1
    
    async def update(self, interaction: discord.Interaction):
        """Update the message with current page"""
        self._update_button_states()
        await interaction.response.edit_message(content=self.pages[self.page], view=self)
    
    @discord.ui.button(label="⏮️ First", style=discord.ButtonStyle.secondary)
    async def first(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You can't use this paginator.", ephemeral=True)
            return
        if self.page != 0:
            self.page = 0
            await self.update(interaction)
    
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You can't use this paginator.", ephemeral=True)
            return
        if self.page > 0:
            self.page -= 1
            await self.update(interaction)
    
    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You can't use this paginator.", ephemeral=True)
            return
        if self.page < len(self.pages) - 1:
            self.page += 1
            await self.update(interaction)
    
    @discord.ui.button(label="⏭️ Last", style=discord.ButtonStyle.secondary)
    async def last(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You can't use this paginator.", ephemeral=True)
            return
        if self.page != len(self.pages) - 1:
            self.page = len(self.pages) - 1
            await self.update(interaction)
            

class ReloadSelect(discord.ui.Select):
    def __init__(self, bot, all_cogs):
        options = [
            discord.SelectOption(label="🔄 Reload ALL Cogs", value="__ALL__",
                                 description="Reload every loaded or unloaded cog!")
        ] + [
            discord.SelectOption(label=cog, value=cog)
            for cog in all_cogs
        ]
        super().__init__(placeholder="Select a cog to reload...",
                         min_values=1, max_values=1, options=options)
        self.bot = bot
        self.all_cogs = all_cogs

    async def callback(self, interaction: discord.Interaction):
        cog = self.values[0]
        logger = logging.getLogger(__name__)
        message = interaction.message

        if cog == "__ALL__":
            start = time.perf_counter()
            failed = []
            for cog_name in self.all_cogs:
                try:
                    if cog_name in self.bot.extensions:
                        await self.bot.reload_extension(cog_name)
                    else:
                        await self.bot.load_extension(cog_name)
                except Exception as e:
                    failed.append(f"{cog_name}: {e}")
            elapsed = (time.perf_counter() - start) * 1000
            logger.info(
                f"All cogs reloaded by {interaction.user} in {elapsed:.2f}ms")
            new_embed = DebugEmbeds.build_status_embed(self.bot, self.all_cogs)
            await message.edit(embed=new_embed, view=CogActionView(self.bot, DebugHelpers.find_cog_extensions()))
            if failed:
                await interaction.response.send_message(
                    f"Some cogs failed to reload:\n" + "\n".join(failed),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "✅ All cogs reloaded successfully.",
                    ephemeral=True
                )
        else:
            start = time.perf_counter()
            try:
                if cog in self.bot.extensions:
                    await self.bot.reload_extension(cog)
                else:
                    await self.bot.load_extension(cog)
                elapsed = (time.perf_counter() - start) * 1000
                logger.info(
                    f"Cog reloaded: {cog} by {interaction.user} in {elapsed:.2f}ms")
                new_embed = DebugEmbeds.build_status_embed(
                    self.bot, self.all_cogs)
                await message.edit(embed=new_embed, view=CogActionView(self.bot, DebugHelpers.find_cog_extensions()))
                await interaction.response.send_message(
                    f"✅ Reloaded `{cog}` in {elapsed:.2f}ms.",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Failed to reload `{cog}`:\n```{e}```",
                    ephemeral=True
                )


class ReloadView(discord.ui.View):
    def __init__(self, bot, cogs):
        super().__init__(timeout=60)
        self.add_item(ReloadSelect(bot, cogs))


class UnloadSelect(discord.ui.Select):
    def __init__(self, bot, cogs):
        options = [
            discord.SelectOption(label=cog, value=cog)
            for cog in cogs
        ]
        super().__init__(placeholder="Select a cog to unload...",
                         min_values=1, max_values=1, options=options)
        self.bot = bot
        self.cogs = cogs

    async def callback(self, interaction: discord.Interaction):
        cog = self.values[0]
        logger = logging.getLogger(__name__)
        message = interaction.message

        start = time.perf_counter()
        try:
            await self.bot.unload_extension(cog)
            elapsed = (time.perf_counter() - start) * 1000
            logger.info(
                f"Cog unloaded: {cog} by {interaction.user} in {elapsed:.2f}ms")
            new_embed = DebugEmbeds.build_status_embed(
                self.bot, DebugHelpers.find_cog_extensions())
            await message.edit(embed=new_embed, view=CogActionView(self.bot, DebugHelpers.find_cog_extensions()))
            await interaction.response.send_message(
                f"✅ Unloaded `{cog}` in {elapsed:.2f}ms.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to unload `{cog}`:\n```{e}```",
                ephemeral=True
            )


class UnloadView(discord.ui.View):
    def __init__(self, bot, cogs):
        super().__init__(timeout=60)
        self.add_item(UnloadSelect(bot, cogs))


class CogActionView(discord.ui.View):
    def __init__(self, bot, all_cogs):
        super().__init__(timeout=60)
        self.bot = bot
        self.all_cogs = all_cogs
        self.add_item(ReloadSelect(bot, all_cogs))
        loaded_cogs = [cog for cog in all_cogs if cog in bot.extensions]
        self.add_item(UnloadSelect(bot, loaded_cogs))
