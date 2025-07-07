from discord.ext import commands
from util.moderation import SetupEmbed, TicketView, SetupView, LogChannelSetupView, ModerationQueries, TicketHelper, ConfirmOverwriteView


class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="modmail", description="Setup modmail ticket system")
    @commands.has_permissions(administrator=True)
    async def modmail(self, ctx):
        # Check if a ticket panel is already set up for this guild
        async with self.bot.db.acquire() as conn:
            row = await ModerationQueries.get_ticket_settings(conn, ctx.guild.id)
        
        if row and row[0]:
            # Prompt for overwrite with buttons
            view = ConfirmOverwriteView(ctx.author)
            msg = await ctx.send(
                f"A ticket panel is already set up in <#{row[0]}>. Do you want to overwrite it?",
                view=view
            )
            await view.wait()
            if view.value is None:
                await msg.edit(content="⏰ Timed out waiting for response. Setup cancelled.", view=None)
                return
            if not view.value:
                await msg.edit(content="Setup cancelled. Existing ticket panel remains unchanged.", view=None)
                return
            await msg.edit(content="⚠️ **Reminder:** The old ticket panel channel and category are not deleted automatically. Please manually delete them if you no longer need them.", view=None)

        # Step 1: Setup ticket panel channel
        ticket_view = SetupView(self.bot, ctx.author)
        ticket_msg = await ctx.send(
            "Would you like to link an existing channel for modmail tickets, or have me create a new category and channel?",
            view=ticket_view
        )
        await ticket_view.wait()
        ticket_panel_channel = ticket_view.result_channel
        if not ticket_panel_channel:
            await ticket_msg.edit(content="⏰ Timed out or no channel selected. Setup cancelled.", view=None)
            return
        await ticket_msg.edit(content=f"Ticket panel channel set to {ticket_panel_channel.mention}", view=None)

        # Save the message ID for the ticket panel
        ticket_panel_message_id = ticket_msg.id

        # Step 2: Setup modmail log channel
        log_view = LogChannelSetupView(self.bot, ctx.author)
        log_msg = await ctx.send(
            "Now set up your modmail log channel. Would you like to link an existing channel or create a new category and channel?",
            view=log_view
        )
        await log_view.wait()
        log_channel = log_view.result_channel
        if not log_channel:
            await log_msg.edit(content="⏰ Timed out or no log channel selected. Setup cancelled.", view=None)
            return
        await log_msg.edit(content=f"Log channel set to {log_channel.mention}", view=None)

        # Save these channels to the database as needed
        async with self.bot.db.acquire() as conn:
            await ModerationQueries.save_ticket_settings(
                conn,
                ctx.guild.id,
                ticket_panel_channel.id,
                ticket_panel_message_id,
                log_channel.id
            )

        # Send the ticket embed with selector to the ticket panel channel
        embed = SetupEmbed.build_ticket_embed(self.bot)
        view = TicketView()
        await ticket_panel_channel.send(embed=embed, view=view)

        await ctx.send("✅ Modmail ticket system setup complete!")

    @commands.command(name="closeticket", description="Close the current ticket and log the conversation")
    @commands.has_permissions(manage_channels=True)
    async def closeticket(self, ctx):
        if not ctx.channel.name.startswith("ticket-"):
            await ctx.send("This command can only be used in a ticket channel.")
            return

        # Fetch the modmail log channel from the DB
        async with self.bot.db.acquire() as conn:
            row = await ModerationQueries.get_ticket_settings(conn, ctx.guild.id)
        
        log_channel = ctx.guild.get_channel(int(row[1])) if row and row[1] else None

        # Limit log to last 100 messages, or add a warning if too long
        try:
            await TicketHelper.close_ticket(ctx.channel, log_channel)
            await ctx.send("Ticket closed and logged.")
        except Exception as e:
            await ctx.send(f"Ticket closed, but log may be too long to send or another error occurred: {e}")
        await ctx.channel.delete()

async def setup(bot):
    await bot.add_cog(SetupCog(bot))
    bot.add_view(TicketView())  # Register persistent view globally