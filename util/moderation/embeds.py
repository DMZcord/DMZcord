import discord

class SetupEmbed:
    TICKET_IMAGE_URL = "https://cdn.discordapp.com/attachments/1377733230857551956/1390764905812066396/raw.png?ex=68697240&is=686820c0&hm=9e1284d59a1fe56cc1df3637cd68335ad56b97f16047e97b526f57a4eb38b734&"

    @staticmethod
    def build_ticket_embed(bot: discord.Client) -> discord.Embed:
        """Create the main ticket panel embed."""
        embed = discord.Embed(
            title="DMZcord Staff Support",
            description=(
                "Select a ticket type from the menu below:\n\n"
                "• **General Support** — Get help from staff\n"
                "• **Appeal** — Appeal a moderation action\n"
                "• **Report** — Report a user or issue\n"
            ),
            color=discord.Color.blurple()
        )
        embed.set_image(url=SetupEmbed.TICKET_IMAGE_URL)
        return embed

    @staticmethod
    def create_ticket_embed(user: discord.User, ticket_type: str) -> discord.Embed:
        """Create embed for when a ticket is created."""
        embed = discord.Embed(
            title="Ticket Created",
            description=(
                f"{user.mention} Ticket created for **`{ticket_type.capitalize()}`**.\n"
                "A staff member will be with you soon."
            ),
            color=discord.Color.blurple()
        )
        embed.set_image(url=SetupEmbed.TICKET_IMAGE_URL)
        return embed


# Backward compatibility aliases
build_ticket_embed = SetupEmbed.build_ticket_embed
create_ticket_embed = SetupEmbed.create_ticket_embed
