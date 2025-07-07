from discord.ext import commands
from util.core import Database

class AuditCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="audit", description="Show command audit log or specific log entry")
    @commands.is_owner()
    async def audit(self, ctx, log_id: str = None):
        """
        Show command audit log or specific log entry.
        
        Usage:
        - !audit or /audit - Shows paginated command audit log
        - !audit <log_id> or /audit <log_id> - Shows specific log entry details
        """
        
        # If log_id is provided, show that specific entry
        if log_id:
            await self.show_log_entry(ctx, log_id)
            return
        
        # Default: Show command audit log
        await self.show_command_audit(ctx)

    async def show_command_audit(self, ctx):
        """Show paginated command audit log for the current guild."""
        guild_id = str(ctx.guild.id)
        rows = await Database.fetch(
            """
            SELECT log_id, user_id, username, channel_id, channel_name, guild_id, command_name, success, error, response_time, timestamp
            FROM command_logs
            WHERE guild_id = %s
            ORDER BY timestamp DESC
            LIMIT 100
            """,
            guild_id
        )
        
        if not rows:
            await ctx.send("No command logs found for this guild.")
            return

        # Pagination logic
        per_page = 10
        pages = [rows[i:i+per_page] for i in range(0, len(rows), per_page)]

        def format_page(page, idx, total):
            if not page:
                return f"**Command Audit Log (Page {idx+1}/{total})**\nNo data found."
            
            # Define the header
            header = ["Username", "Channel", "Command", "Date/Time", "Log ID"]
            
            lines = [f"**Command Audit Log (Page {idx+1}/{total})**", "```"]
            
            # Add header
            header_line = "  ".join(f"{col:<15}" for col in header)
            lines.append(header_line)
            lines.append("-" * len(header_line))
            
            for entry in page:
                if isinstance(entry, dict):
                    # Extract data and handle None values properly
                    success_emoji = "✅" if entry.get('success') else "❌"
                    username = f"{success_emoji} {str(entry.get('username') or '')[:12]}"
                    channel_name = str(entry.get('channel_name') or '')[:15]
                    
                    # Handle None response_time and add to command name
                    response_time_val = entry.get('response_time')
                    if response_time_val is not None:
                        response_time_str = f"[{response_time_val:.2f}s]"
                    else:
                        response_time_str = "[N/A]"
                    
                    # Combine command name with response time
                    base_command = str(entry.get('command_name') or '')
                    command_with_time = f"{base_command} {response_time_str}"
                    
                    # Convert timestamp to PST and format as HH:MM:SS DD/MM/YYYY
                    timestamp = entry.get('timestamp')
                    if timestamp:
                        try:
                            from datetime import datetime
                            import pytz
                            
                            # Convert to PST and format as requested
                            if isinstance(timestamp, datetime):
                                dt = timestamp
                            else:
                                dt = datetime.fromisoformat(str(timestamp))
                            pst_tz = pytz.timezone('America/Los_Angeles')
                            dt_pst = dt.astimezone(pst_tz)
                            time_str = dt_pst.strftime("%H:%M:%S %d/%m/%Y")
                        except Exception:
                            time_str = "N/A"
                    else:
                        time_str = "N/A"
                    
                    # Get last 6 characters of log_id
                    log_id = str(entry.get('log_id') or '')
                    log_id_short = log_id[-6:] if len(log_id) >= 6 else log_id
                    
                    # Format row with consistent spacing
                    row_data = [username, channel_name, command_with_time, time_str, log_id_short]
                    row_line = "  ".join(f"{col:<15}" for col in row_data)
                    lines.append(row_line)
    
            lines.append("```")
            return "\n".join(lines)

        total_pages = len(pages)
        current = 0
        message = await ctx.send(format_page(pages[current], current, total_pages))

        if total_pages == 1:
            return

        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")

        def check(reaction, user):
            return (
                user == ctx.author
                and reaction.message.id == message.id
                and str(reaction.emoji) in ["⬅️", "➡️"]
            )

        while True:
            try:
                reaction, user = await ctx.bot.wait_for("reaction_add", timeout=60.0, check=check)
                if str(reaction.emoji) == "➡️" and current < total_pages - 1:
                    current += 1
                    await message.edit(content=format_page(pages[current], current, total_pages))
                    await message.remove_reaction(reaction, user)
                elif str(reaction.emoji) == "⬅️" and current > 0:
                    current -= 1
                    await message.edit(content=format_page(pages[current], current, total_pages))
                    await message.remove_reaction(reaction, user)
                else:
                    await message.remove_reaction(reaction, user)
            except Exception:
                break

    async def show_log_entry(self, ctx, log_id_input):
        """Show detailed summary of a specific log entry by log_id (full or last 6 chars), with collision detection."""
        # If input is 6 characters or less, search by suffix
        if len(log_id_input) <= 6:
            query = """
                SELECT log_id, user_id, username, channel_id, channel_name, guild_id, command_name, success, error, response_time, timestamp
                FROM command_logs
                WHERE log_id LIKE %s
                ORDER BY timestamp DESC
                LIMIT 10
            """
            rows = await Database.fetch(query, f"%{log_id_input}")
            # Filter for exact suffix match (in case more than 10 match)
            rows = [row for row in rows if str(row.get('log_id', '')).endswith(log_id_input)]
        else:
            # Search by exact log_id
            query = """
                SELECT log_id, user_id, username, channel_id, channel_name, guild_id, command_name, success, error, response_time, timestamp
                FROM command_logs
                WHERE log_id = %s
                LIMIT 1
            """
            rows = await Database.fetch(query, log_id_input)

        if not rows:
            await ctx.send(f"No command log found with ID `{log_id_input}`")
            return

        if len(rows) > 1:
            # Collision detected!
            lines = [f"⚠️ **Collision detected:** Multiple entries found for `{log_id_input}` (last 6 digits).", "```"]
            for row in rows:
                if isinstance(row, dict):
                    full_id = str(row.get('log_id', ''))
                    command = row.get('command_name', 'Unknown')
                    username = row.get('username', 'Unknown')
                    success = "✅" if row.get('success') else "❌"
                    # Show more of the ID for clarity
                    lines.append(f"{full_id[-12:]} - {command} by {username} {success}")
            lines.append("```")
            lines.append("Please use the full log_id for an exact match.")
            await ctx.send("\n".join(lines))
            return

        # Single match, show detailed summary
        entry = rows[0]
        if isinstance(entry, dict):
            # Format timestamp
            timestamp = entry.get('timestamp')
            if timestamp:
                try:
                    from datetime import datetime
                    import pytz

                    if isinstance(timestamp, datetime):
                        dt = timestamp
                    else:
                        dt = datetime.fromisoformat(str(timestamp))
                    pst_tz = pytz.timezone('America/Los_Angeles')
                    dt_pst = dt.astimezone(pst_tz)
                    formatted_time = dt_pst.strftime("%H:%M:%S %d/%m/%Y")
                except Exception:
                    formatted_time = "N/A"
            else:
                formatted_time = "N/A"

            success_text = "✅ Success" if entry.get('success') else "❌ Failed"
            response_time = entry.get('response_time')
            response_time_text = f"{response_time:.3f}s" if response_time is not None else "N/A"

            # Build detailed summary
            summary_lines = [
                f"**Command Log Summary**",
                f"**Log ID:** `{entry.get('log_id', 'Unknown')}`",
                f"**User:** {entry.get('username', 'Unknown')} (`{entry.get('user_id', 'Unknown')}`)",
                f"**Command:** `{entry.get('command_name', 'Unknown')}`",
                f"**Channel:** #{entry.get('channel_name', 'Unknown')} (`{entry.get('channel_id', 'Unknown')}`)",
                f"**Guild ID:** `{entry.get('guild_id', 'Unknown')}`",
                f"**Status:** {success_text}",
                f"**Response Time:** {response_time_text}",
                f"**Timestamp:** {formatted_time}",
            ]

            # Add error if present
            error = entry.get('error')
            if error:
                # Truncate very long errors
                error_text = error[:200] + "..." if len(error) > 200 else error
                summary_lines.append(f"**Error:** ```{error_text}```")

            await ctx.send("\n".join(summary_lines))

async def setup(bot):
    await bot.add_cog(AuditCog(bot))