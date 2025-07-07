import discord
from discord.ui import View, Button
from util.moderation.utils import TicketHelper
import logging

logger = logging.getLogger(__name__)

class ConfirmResetView(View):
    def __init__(self, user_display):
        super().__init__(timeout=30)
        self.value = None
        self.user_display = user_display

        self.confirm_button = Button(
            label="Confirm", style=discord.ButtonStyle.danger)
        self.cancel_button = Button(
            label="Cancel", style=discord.ButtonStyle.secondary)
        self.confirm_button.callback = self.confirm
        self.cancel_button.callback = self.cancel
        self.add_item(self.confirm_button)
        self.add_item(self.cancel_button)

    async def confirm(self, interaction: discord.Interaction):
        self.value = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"Are you absolutely sure you want to reset all moderation entries for {self.user_display}? This cannot be undone.",
            view=FinalConfirmResetView(self.user_display, self)
        )
        self.stop()

    async def cancel(self, interaction: discord.Interaction):
        self.value = False
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="Reset cancelled.", view=None)
        self.stop()


class FinalConfirmResetView(View):
    def __init__(self, user_display, parent_view):
        super().__init__(timeout=30)
        self.value = None
        self.user_display = user_display
        self.parent_view = parent_view

        self.final_confirm_button = Button(
            label="Yes, reset everything", style=discord.ButtonStyle.danger)
        self.final_cancel_button = Button(
            label="Cancel", style=discord.ButtonStyle.secondary)
        self.final_confirm_button.callback = self.final_confirm
        self.final_cancel_button.callback = self.final_cancel
        self.add_item(self.final_confirm_button)
        self.add_item(self.final_cancel_button)

    async def final_confirm(self, interaction: discord.Interaction):
        self.value = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="Confirmed. Resetting moderation entries...", view=None)
        self.stop()

    async def final_cancel(self, interaction: discord.Interaction):
        self.value = False
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="Reset cancelled.", view=None)
        self.stop()


class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="General Support", value="general"),
            discord.SelectOption(label="Appeal", value="appeal"),
            discord.SelectOption(label="Report", value="report"),
        ]
        super().__init__(
            placeholder="Choose a ticket type...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="persistent_ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await TicketHelper.create_ticket(interaction)


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


class SetupView(discord.ui.View):
    def __init__(self, bot, admin_user):
        super().__init__(timeout=120)
        self.bot = bot
        self.admin_user = admin_user
        self.result_channel = None

    @discord.ui.button(label="Create Category & Channel", style=discord.ButtonStyle.green)
    async def create_category_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketHelper.create_ticket_category_and_channel(interaction, self.bot, self.admin_user, self)

    @discord.ui.button(label="Link Existing Channel", style=discord.ButtonStyle.blurple)
    async def link_existing_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketHelper.link_existing_ticket_channel(interaction, self.bot, self.admin_user, self)

class LogChannelSetupView(discord.ui.View):
    def __init__(self, bot, admin_user):
        super().__init__(timeout=120)
        self.bot = bot
        self.admin_user = admin_user
        self.result_channel = None

    @discord.ui.button(label="Create Category & Channel", style=discord.ButtonStyle.green)
    async def create_log_category_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketHelper.create_log_category_and_channel(interaction, self.bot, self.admin_user, self)

    @discord.ui.button(label="Link Existing Channel", style=discord.ButtonStyle.blurple)
    async def link_existing_log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketHelper.link_existing_log_channel(interaction, self.bot, self.admin_user, self)


class ConfirmOverwriteView(View):
    def __init__(self, author, timeout=30):
        super().__init__(timeout=timeout)
        self.value = None
        self.author = author

        self.confirm_button = Button(label="Overwrite", style=discord.ButtonStyle.danger)
        self.cancel_button = Button(label="Cancel", style=discord.ButtonStyle.secondary)
        self.confirm_button.callback = self.confirm
        self.cancel_button.callback = self.cancel
        self.add_item(self.confirm_button)
        self.add_item(self.cancel_button)

    async def confirm(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Only the command invoker can confirm.", ephemeral=True)
            return
        self.value = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="Overwriting ticket panel...", view=None)
        self.stop()

    async def cancel(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Only the command invoker can cancel.", ephemeral=True)
            return
        self.value = False
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="Setup cancelled.", view=None)
        self.stop()


class ChannelEditView(discord.ui.View):
    """View for the channel edit prompt with clear and cancel buttons"""

    def __init__(self, parent_view, interaction, setting_key, setting_name, current_value):
        super().__init__(timeout=60)
        self.parent_view = parent_view
        self.interaction = interaction
        self.setting_key = setting_key
        self.setting_name = setting_name
        self.current_value = current_value

        # Disable clear button if no current value is set
        for item in self.children:
            if hasattr(item, 'label') and item.label == "🗑️ Clear Setting":
                item.disabled = not current_value

    @discord.ui.button(label="🗑️ Clear Setting", style=discord.ButtonStyle.danger, row=0)
    async def clear_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.parent_view.ctx.author.id:
            await interaction.response.send_message("You can't use this button.", ephemeral=True)
            return

        # Clear the setting from database
        async with self.parent_view.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM guild_settings WHERE guild_id = %s AND `key` = %s",
                    (self.parent_view.guild_id, self.setting_key)
                )
                await conn.commit()

        # Log the clear action
        logger.info(
            f"Cleared {self.setting_key} for {interaction.user} in guild {self.parent_view.guild_id}.")

        # Update the rows data
        self.parent_view.rows = [
            row for row in self.parent_view.rows if row[0] != self.setting_key]

        # Return to main view
        embed = self.parent_view.create_embed(interaction.guild)
        new_view = WelcomeSettingsView(
            self.parent_view.ctx, self.parent_view.bot, self.parent_view.guild_id, self.parent_view.rows)
        await interaction.response.edit_message(content="", embed=embed, view=new_view)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary, row=0)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.parent_view.ctx.author.id:
            await interaction.response.send_message("You can't use this button.", ephemeral=True)
            return

        # Return to the main welcome settings view
        embed = self.parent_view.create_embed(interaction.guild)
        new_view = WelcomeSettingsView(
            self.parent_view.ctx, self.parent_view.bot, self.parent_view.guild_id, self.parent_view.rows)
        await interaction.response.edit_message(content="", embed=embed, view=new_view)


class WelcomeSettingsView(discord.ui.View):
    def __init__(self, ctx, bot, guild_id, rows):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.bot = bot
        self.guild_id = guild_id
        self.rows = rows

    async def send_response(self, interaction, content, **kwargs):
        if interaction.response.is_done():
            return await interaction.followup.send(content, ephemeral=True, **kwargs)
        else:
            return await interaction.response.send_message(content, ephemeral=True, **kwargs)

    @discord.ui.button(label="🎉 Welcome", style=discord.ButtonStyle.primary, row=0)
    async def welcome_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .utils import WelcomeHelper
        await WelcomeHelper.handle_setting_update(self, interaction, 'welcome_channel_id', '🎉 Welcome')

    @discord.ui.button(label="👥 LFG", style=discord.ButtonStyle.primary, row=0)
    async def squad_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .utils import WelcomeHelper
        await WelcomeHelper.handle_setting_update(self, interaction, 'squad_channel_id', '👥 LFG')

    @discord.ui.button(label="🎬 Highlights", style=discord.ButtonStyle.primary, row=1)
    async def highlights_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .utils import WelcomeHelper
        await WelcomeHelper.handle_setting_update(self, interaction, 'highlights_channel_id', '🎬 Highlights')

    @discord.ui.button(label="📋 Log", style=discord.ButtonStyle.primary, row=1)
    async def log_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .utils import WelcomeHelper
        await WelcomeHelper.handle_setting_update(self, interaction, 'log_channel_id', '📋 Log')

    def create_embed(self, guild):
        from .utils import WelcomeHelper
        return WelcomeHelper.create_settings_embed(guild, self.rows)
