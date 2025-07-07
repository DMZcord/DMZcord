import discord
from util.core.utils import TableUtils

class TablePaginator(discord.ui.View):
    def __init__(self, rows, title, per_page=10, timeout=120):
        super().__init__(timeout=timeout)
        self.rows = rows
        self.title = title
        self.per_page = per_page
        self.page = 0
        self.max_page = max(0, (len(rows) - 2) // per_page)  # -2 for header row

        self.first_button = discord.ui.Button(
            label="New", style=discord.ButtonStyle.primary, disabled=True)
        self.prev_button = discord.ui.Button(
            label="Previous", style=discord.ButtonStyle.secondary, disabled=True)
        self.next_button = discord.ui.Button(
            label="Next", style=discord.ButtonStyle.secondary, disabled=(self.max_page == 0))
        self.last_button = discord.ui.Button(
            label="Old", style=discord.ButtonStyle.primary, disabled=(self.max_page == 0))

        self.first_button.callback = self.go_first
        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page
        self.last_button.callback = self.go_last

        self.add_item(self.first_button)
        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self.add_item(self.last_button)

    async def go_first(self, interaction):
        if self.page != 0:
            self.page = 0
            await self.update_message(interaction)

    async def go_last(self, interaction):
        if self.page != self.max_page:
            self.page = self.max_page
            await self.update_message(interaction)

    async def prev_page(self, interaction):
        if self.page > 0:
            self.page -= 1
            await self.update_message(interaction)

    async def next_page(self, interaction):
        if self.page < self.max_page:
            self.page += 1
            await self.update_message(interaction)

    async def update_message(self, interaction):
        self.first_button.disabled = self.page == 0
        self.prev_button.disabled = self.page == 0
        self.next_button.disabled = self.page == self.max_page
        self.last_button.disabled = self.page == self.max_page
        table = self.get_page_table()
        await interaction.response.edit_message(content=f"{self.title}\n{table}", view=self)

    def get_page_table(self):
        header = self.rows[0]
        body = self.rows[1:]
        start = self.page * self.per_page
        end = start + self.per_page
        page_rows = [header] + body[start:end]
        return TableUtils.format_table(page_rows)


class ButtonPaginator(discord.ui.View):
    """
    Generic paginator for a list of items, with navigation buttons.
    Each item is a discord.ui.Button.
    """
    def __init__(self, items, label_func, custom_id_func, max_buttons=10, page=0, timeout=60, style=discord.ButtonStyle.primary):
        super().__init__(timeout=timeout)
        self.items = items
        self.label_func = label_func
        self.custom_id_func = custom_id_func
        self.max_buttons = max_buttons
        self.page = page
        self.style = style

        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        start = self.page * self.max_buttons
        end = start + self.max_buttons
        page_items = self.items[start:end]
        for idx, item in enumerate(page_items):
            self.add_item(
                discord.ui.Button(
                    label=self.label_func(item, start + idx),
                    style=self.style,
                    custom_id=self.custom_id_func(item, start + idx)
                )
            )
        # Navigation
        if len(self.items) > self.max_buttons:
            if self.page > 0:
                self.add_item(
                    discord.ui.Button(label="Prev", style=discord.ButtonStyle.secondary, custom_id="prev_page"))
            if end < len(self.items):
                self.add_item(
                    discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary, custom_id="next_page"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Handle navigation
        custom_id = interaction.data.get("custom_id")
        if custom_id == "prev_page" and self.page > 0:
            self.page -= 1
            self.update_buttons()
            await interaction.response.edit_message(view=self)
            return False
        elif custom_id == "next_page" and (self.page + 1) * self.max_buttons < len(self.items):
            self.page += 1
            self.update_buttons()
            await interaction.response.edit_message(view=self)
            return False
        return True
