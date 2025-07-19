import discord
from discord.ext import commands
from discord import app_commands
from util.general import GeneralHelpers, HelpEmbed, HelpMainView, HelpCommandView
from util.owner import DebugEmbeds, DebugHelpers
import time

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Show help for commands")
    @app_commands.describe(command_name="Command name")
    async def help_command(self, ctx: commands.Context, command_name: str = None):
        is_slash = hasattr(ctx, "interaction") and ctx.interaction is not None
        user = ctx.author if not is_slash else ctx.interaction.user
        author_id = user.id

        # Delete the user's message for regular commands (not slash commands)
        if not is_slash:
            try:
                await ctx.message.delete()
            except (discord.NotFound, discord.Forbidden):
                pass  # Message already deleted or no permission

        # Defer immediately for slash commands
        if is_slash and not ctx.interaction.response.is_done():
            await ctx.interaction.response.defer(ephemeral=True)

        try:
            if command_name:
                command = self.bot.get_command(command_name)
                if command:
                    # Hide commands the user can't run
                    if not await GeneralHelpers.filter_help_commands(command, ctx, self.bot):
                        not_found_msg = f"❌ Command `{command_name}` not found."
                        if is_slash:
                            await ctx.interaction.edit_original_response(content=not_found_msg)
                        else:
                            msg = await ctx.send(not_found_msg)
                            ctx.bot.loop.create_task(GeneralHelpers.delete_after_timeout(ctx, msg, timeout=120))
                        return

                    # Use centralized embed builder for command help
                    embed = HelpEmbed.build_command_help_embed(command, user)
                    
                    # Find the cog this command belongs to and get all commands in that cog
                    cog_name = command.cog_name or "No Category"
                    all_commands = []
                    for cmd in self.bot.commands:
                        if await GeneralHelpers.filter_help_commands(cmd, ctx, self.bot):
                            if (cmd.cog_name or "No Category") == cog_name:
                                all_commands.append(cmd)
                    
                    # Sort commands alphabetically
                    all_commands.sort(key=lambda cmd: cmd.qualified_name.lower())
                    
                    # Create HelpCommandView with the command's cog information
                    display_name = cog_name[:-3] if cog_name.lower().endswith("cog") else cog_name
                    
                    if is_slash:
                        await ctx.interaction.edit_original_response(embed=embed)
                        message = await ctx.channel.fetch_message(ctx.interaction.message.id)
                        view = HelpCommandView(
                            self, ctx, all_commands, is_slash, display_name, user, message.id, author_id
                        )
                        await message.edit(embed=embed, view=view)
                    else:
                        message = await ctx.send(embed=embed)
                        view = HelpCommandView(
                            self, ctx, all_commands, is_slash, display_name, user, message.id, author_id
                        )
                        await message.edit(embed=embed, view=view)
                        ctx.bot.loop.create_task(GeneralHelpers.delete_after_timeout(ctx, message, timeout=120))
                else:
                    not_found_msg = f"❌ Command `{command_name}` not found."
                    if is_slash:
                        await ctx.interaction.edit_original_response(content=not_found_msg)
                    else:
                        msg = await ctx.send(not_found_msg)
                        ctx.bot.loop.create_task(GeneralHelpers.delete_after_timeout(ctx, msg, timeout=120))
            else:
                # Main help: filter out commands the user can't run
                all_commands = []
                for cmd in self.bot.commands:
                    if await GeneralHelpers.filter_help_commands(cmd, ctx, self.bot):
                        all_commands.append(cmd)
                
                # Use centralized embed organizer and builder
                cogs_with_commands = await HelpEmbed.organize_help_embed(self.bot, commands_list=all_commands)
                
                # Sort cogs alphabetically and sort commands within each cog
                sorted_cogs_with_commands = {}
                for cog_name in sorted(cogs_with_commands.keys(), key=str.lower):
                    # Sort commands within each cog alphabetically
                    sorted_commands = sorted(cogs_with_commands[cog_name], key=lambda cmd: cmd.qualified_name.lower())
                    sorted_cogs_with_commands[cog_name] = sorted_commands
                
                embed = HelpEmbed.build_main_help_embed(sorted_cogs_with_commands, user)
                
                if is_slash:
                    await ctx.interaction.edit_original_response(embed=embed)
                    message = await ctx.channel.fetch_message(ctx.interaction.message.id)
                    view = HelpMainView(self, ctx, sorted_cogs_with_commands, is_slash, message_id=message.id, author_id=author_id, timeout=120)
                    await message.edit(embed=embed, view=view)
                else:
                    message = await ctx.send(embed=embed)
                    view = HelpMainView(self, ctx, sorted_cogs_with_commands, is_slash, message_id=message.id, author_id=author_id, timeout=120)
                    await message.edit(embed=embed, view=view)
                    ctx.bot.loop.create_task(GeneralHelpers.delete_after_timeout(ctx, message))
        except Exception as e:
            # Always respond with an error if something goes wrong
            error_msg = f"❌ An error occurred: {e}"
            if is_slash:
                try:
                    await ctx.interaction.edit_original_response(content=error_msg)
                except Exception:
                    pass
            else:
                await ctx.send(error_msg)

    @commands.command(name="info")
    @commands.is_owner()
    async def botinfo(self, ctx):
        """Show info about this bot process and server stats."""

        # Bot info
        info = DebugHelpers.get_bot_info()
        current_time = time.time()
        uptime_seconds = current_time - info['start_timestamp']
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        try:
            embed = await DebugEmbeds.build_botinfo_embed(self.bot, info, uptime_str)
            if not embed or (not embed.fields and not embed.description):
                await ctx.send("❌ Failed to generate bot info embed.")
                return
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Failed to generate bot info: {e}")

async def setup(bot):
    await bot.add_cog(HelpCog(bot))