import discord
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, timedelta
import re
import os
import io
from dotenv import load_dotenv

load_dotenv()

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.check_mutes.start()

    def format_timestamp(self, iso_timestamp: str) -> str:
        try:
            dt = datetime.fromisoformat(iso_timestamp)
            return dt.strftime("%d-%m-%Y %H:%M:%S")
        except ValueError:
            return "Invalid timestamp"

    def generate_id(self, user_id: str, table: str, action: str = None) -> str:
        last4 = user_id[-4:]
        prefix = {"warnings": "W", "mutes": "M", "bans": "B"}[table]
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0] + 1
        conn.close()
        return f"{prefix}-{last4}-{count:04d}"

    def format_table(self, rows: list) -> str:
        col_widths = [max(len(str(item)) for item in col) for col in zip(*rows)]
        lines = []
        for row in rows:
            line = "  ".join(str(item).ljust(width) for item, width in zip(row, col_widths))
            lines.append(line)
        return "```\n" + "\n".join(lines) + "\n```"

    def parse_duration(self, duration_str: str) -> int:
        """Parse duration string like '15m', '1h' into seconds. Cap at 1 week."""
        max_duration = 604800  # 1 week in seconds (7 days)
        match = re.match(r'^(\d+)([mh])$', duration_str.lower())
        if not match:
            raise ValueError("Duration must be in the format '15m', '45m', '1h', or '24h' (e.g., 15 minutes, 1 hour).")
        
        value, unit = int(match.group(1)), match.group(2)
        if unit == 'm':
            seconds = value * 60  # Minutes to seconds
        elif unit == 'h':
            seconds = value * 3600  # Hours to seconds
        
        if seconds > max_duration:
            seconds = max_duration
        return seconds

    @tasks.loop(minutes=1)
    async def check_mutes(self):
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        c.execute("SELECT id, user_id, timestamp, duration FROM mutes WHERE action = 'mute' AND duration IS NOT NULL")
        mutes = c.fetchall()
        current_time = datetime.now()
        for mute_id, user_id, timestamp, duration in mutes:
            mute_start = datetime.fromisoformat(timestamp)
            mute_end = mute_start + timedelta(seconds=duration)
            if current_time >= mute_end:
                # Unmute the user
                guild = self.bot.get_guild(int(os.getenv('GUILD_ID')))
                if not guild:
                    continue
                member = guild.get_member(int(user_id))
                if not member:
                    continue
                mute_role = discord.utils.get(guild.roles, name="Muted")
                if not mute_role or mute_role not in member.roles:
                    continue
                await member.remove_roles(mute_role, reason="Mute duration expired")
                unmute_id = self.generate_id(user_id, "mutes")
                c.execute("INSERT INTO mutes (id, user_id, reason, timestamp, added_by, action) VALUES (?, ?, ?, ?, ?, ?)",
                          (unmute_id, user_id, "Mute duration expired", datetime.now().isoformat(), "Bot", "unmute"))
                conn.commit()
        conn.close()

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        user_id = str(member.id)
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        # Count existing warnings
        c.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (user_id,))
        warning_count = c.fetchone()[0] + 1  # Including the new warning
        # Log the warning
        warn_id = self.generate_id(user_id, "warnings")
        c.execute("INSERT INTO warnings (id, user_id, reason, timestamp, added_by) VALUES (?, ?, ?, ?, ?)", 
                  (warn_id, user_id, reason, datetime.now().isoformat(), str(ctx.author)))
        conn.commit()
        await ctx.send(f"Warned {member.mention} for: {reason} (Warning #{warning_count})")
        try:
            await member.send(f"You were warned in {ctx.guild.name} for: {reason} (Warning #{warning_count})")
        except discord.Forbidden:
            await ctx.send(f"Could not DM {member.mention} (DMs disabled or bot blocked).")
        # Apply punishment based on warning count
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted", reason="Created for mute command")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False)
        if warning_count == 1:
            pass  # No punishment
        elif warning_count == 2:
            # 1-hour mute
            if mute_role not in member.roles:
                await member.add_roles(mute_role, reason="2nd warning punishment")
                mute_id = self.generate_id(user_id, "mutes")
                c.execute("INSERT INTO mutes (id, user_id, reason, timestamp, added_by, action, duration) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (mute_id, user_id, "2nd warning: 1-hour mute", datetime.now().isoformat(), str(ctx.author), "mute", 3600))
                conn.commit()
                await ctx.send(f"{member.mention} has been muted for 1 hour due to receiving their 2nd warning.")
                try:
                    await member.send(f"You were muted for 1 hour in {ctx.guild.name} due to your 2nd warning.")
                except discord.Forbidden:
                    await ctx.send(f"Could not DM {member.mention} about mute.")
        elif warning_count == 3:
            # 2-hour mute
            if mute_role not in member.roles:
                await member.add_roles(mute_role, reason="3rd warning punishment")
                mute_id = self.generate_id(user_id, "mutes")
                c.execute("INSERT INTO mutes (id, user_id, reason, timestamp, added_by, action, duration) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (mute_id, user_id, "3rd warning: 2-hour mute", datetime.now().isoformat(), str(ctx.author), "mute", 7200))
                conn.commit()
                await ctx.send(f"{member.mention} has been muted for 2 hours due to receiving their 3rd warning.")
                try:
                    await member.send(f"You were muted for 2 hours in {ctx.guild.name} due to your 3rd warning.")
                except discord.Forbidden:
                    await ctx.send(f"Could not DM {member.mention} about mute.")
        elif warning_count == 4:
            # 7-day mute
            if mute_role not in member.roles:
                await member.add_roles(mute_role, reason="4th warning punishment")
                mute_id = self.generate_id(user_id, "mutes")
                c.execute("INSERT INTO mutes (id, user_id, reason, timestamp, added_by, action, duration) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (mute_id, user_id, "4th warning: 7-day mute", datetime.now().isoformat(), str(ctx.author), "mute", 604800))
                conn.commit()
                await ctx.send(f"{member.mention} has been muted for 7 days due to receiving their 4th warning.")
                try:
                    await member.send(f"You were muted for 7 days in {ctx.guild.name} due to your 4th warning.")
                except discord.Forbidden:
                    await ctx.send(f"Could not DM {member.mention} about mute.")
        elif warning_count >= 5:
            # Ban
            ban_id = self.generate_id(user_id, "bans")
            try:
                await member.send(f"You were banned from {ctx.guild.name} due to receiving your 5th warning.")
            except discord.Forbidden:
                await ctx.send(f"Could not DM {member.mention} about ban.")
            await member.ban(reason="5th warning punishment")
            c.execute("INSERT INTO bans (id, user_id, reason, timestamp, added_by, action) VALUES (?, ?, ?, ?, ?, ?)",
                      (ban_id, user_id, "5th warning: Ban", datetime.now().isoformat(), str(ctx.author), "ban"))
            conn.commit()
            await ctx.send(f"{member.mention} has been banned due to receiving their 5th warning.")
        conn.close()

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def history(self, ctx: commands.Context, arg: str, *args: str):
        id_pattern = re.compile(r'^[WMB]-\d{4}-\d{4}$')
        if id_pattern.match(arg):
            # Specific ID view
            conn = sqlite3.connect('cheaters.db')
            c = conn.cursor()
            c.execute("SELECT user_id, reason, timestamp, added_by FROM warnings WHERE id = ?", (arg,))
            warning = c.fetchone()
            if warning:
                user_id, reason, timestamp, added_by = warning
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    user_display = f"{user.name}#{user.discriminator} ({user_id})"
                except discord.NotFound:
                    user_display = f"User ID {user_id} (not found)"
                response = (
                    f"**History Entry for {user_display}**\n"
                    f"Type: Warning\n"
                    f"Reason: {reason}\n"
                    f"Added By: {added_by}\n"
                    f"ID: {arg}\n"
                    f"Timestamp: {self.format_timestamp(timestamp)}"
                )
                conn.close()
                await ctx.send(response)
                return
            c.execute("SELECT user_id, reason, timestamp, added_by, action FROM mutes WHERE id = ?", (arg,))
            mute = c.fetchone()
            if mute:
                user_id, reason, timestamp, added_by, action = mute
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    user_display = f"{user.name}#{user.discriminator} ({user_id})"
                except discord.NotFound:
                    user_display = f"User ID {user_id} (not found)"
                response = (
                    f"**History Entry for {user_display}**\n"
                    f"Type: {action.capitalize()}\n"
                    f"Reason: {reason}\n"
                    f"Added By: {added_by}\n"
                    f"ID: {arg}\n"
                    f"Timestamp: {self.format_timestamp(timestamp)}"
                )
                conn.close()
                await ctx.send(response)
                return
            c.execute("SELECT user_id, reason, timestamp, added_by, action FROM bans WHERE id = ?", (arg,))
            ban = c.fetchone()
            if ban:
                user_id, reason, timestamp, added_by, action = ban
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    user_display = f"{user.name}#{user.discriminator} ({user_id})"
                except discord.NotFound:
                    user_display = f"User ID {user_id} (not found)"
                response = (
                    f"**History Entry for {user_display}**\n"
                    f"Type: {action.capitalize()}\n"
                    f"Reason: {reason}\n"
                    f"Added By: {added_by}\n"
                    f"ID: {arg}\n"
                    f"Timestamp: {self.format_timestamp(timestamp)}"
                )
                conn.close()
                await ctx.send(response)
                return
            conn.close()
            await ctx.send(f"No history entry found with ID {arg}.")
            return

        # Handle "!history all"
        if arg.lower() == "all":
            sort_by_type = args and args[-1].lower() == "sort"
            conn = sqlite3.connect('cheaters.db')
            c = conn.cursor()
            c.execute("SELECT id, user_id, reason, timestamp, added_by FROM warnings")
            warnings = c.fetchall()
            c.execute("SELECT id, user_id, reason, timestamp, added_by, action FROM mutes")
            mutes = c.fetchall()
            c.execute("SELECT id, user_id, reason, timestamp, added_by, action FROM bans")
            bans = c.fetchall()
            conn.close()
            if not warnings and not mutes and not bans:
                await ctx.send("No history entries found.")
                return
            rows = [["User", "Type", "Reason", "Added By", "ID", "Timestamp"]]
            if sort_by_type:
                warnings = sorted(warnings, key=lambda x: x[3])
                mutes = sorted(mutes, key=lambda x: x[3])
                bans = sorted(bans, key=lambda x: x[3])
                for id_, user_id, reason, timestamp, added_by in warnings:
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        user_display = f"{user.name} ({user_id})"
                    except discord.NotFound:
                        user_display = f"Unknown ({user_id})"
                    reason = (reason[:25] + "...") if len(reason) > 25 else reason
                    added_by = (added_by[:15] + "...") if len(added_by) > 15 else added_by
                    user_display = (user_display[:25] + "...") if len(user_display) > 25 else user_display
                    rows.append([user_display, "Warning", reason, added_by, id_, self.format_timestamp(timestamp)])
                for id_, user_id, reason, timestamp, added_by, action in mutes:
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        user_display = f"{user.name} ({user_id})"
                    except discord.NotFound:
                        user_display = f"Unknown ({user_id})"
                    reason = (reason[:25] + "...") if len(reason) > 25 else reason
                    added_by = (added_by[:15] + "...") if len(added_by) > 15 else added_by
                    user_display = (user_display[:25] + "...") if len(user_display) > 25 else user_display
                    rows.append([user_display, action.capitalize(), reason, added_by, id_, self.format_timestamp(timestamp)])
                for id_, user_id, reason, timestamp, added_by, action in bans:
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        user_display = f"{user.name} ({user_id})"
                    except discord.NotFound:
                        user_display = f"Unknown ({user_id})"
                    reason = (reason[:25] + "...") if len(reason) > 25 else reason
                    added_by = (added_by[:15] + "...") if len(added_by) > 15 else added_by
                    user_display = (user_display[:25] + "...") if len(user_display) > 25 else user_display
                    rows.append([user_display, action.capitalize(), reason, added_by, id_, self.format_timestamp(timestamp)])
            else:
                all_entries = []
                for id_, user_id, reason, timestamp, added_by in warnings:
                    all_entries.append((id_, user_id, "Warning", reason, timestamp, added_by))
                for id_, user_id, reason, timestamp, added_by, action in mutes:
                    all_entries.append((id_, user_id, action.capitalize(), reason, timestamp, added_by))
                for id_, user_id, reason, timestamp, added_by, action in bans:
                    all_entries.append((id_, user_id, action.capitalize(), reason, timestamp, added_by))
                all_entries = sorted(all_entries, key=lambda x: x[4])
                for id_, user_id, type_, reason, timestamp, added_by in all_entries:
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        user_display = f"{user.name} ({user_id})"
                    except discord.NotFound:
                        user_display = f"Unknown ({user_id})"
                    reason = (reason[:25] + "...") if len(reason) > 25 else reason
                    added_by = (added_by[:15] + "...") if len(added_by) > 15 else added_by
                    user_display = (user_display[:25] + "...") if len(user_display) > 25 else user_display
                    rows.append([user_display, type_, reason, added_by, id_, self.format_timestamp(timestamp)])
            table = self.format_table(rows)
            await ctx.send(f"**All History Entries**\n{table}")
            return

        # Existing user ID handling
        try:
            user_id = str(int(arg))  # Validate user ID
        except ValueError:
            await ctx.send("Please provide a valid user ID, history entry ID (e.g., W-6750-0005), or use '!history all'.")
            return
        sort_by_type = args and args[-1].lower() == "sort"
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        c.execute("SELECT id, user_id, reason, timestamp, added_by FROM warnings WHERE user_id = ?", (user_id,))
        warnings = c.fetchall()
        c.execute("SELECT id, user_id, reason, timestamp, added_by, action FROM mutes WHERE user_id = ?", (user_id,))
        mutes = c.fetchall()
        c.execute("SELECT id, user_id, reason, timestamp, added_by, action FROM bans WHERE user_id = ?", (user_id,))
        bans = c.fetchall()
        conn.close()
        if not warnings and not mutes and not bans:
            await ctx.send(f"No history found for user ID {user_id}.")
            return
        rows = [["Type", "Reason", "Added By", "ID", "Timestamp"]]
        if sort_by_type:
            warnings = sorted(warnings, key=lambda x: x[3])
            mutes = sorted(mutes, key=lambda x: x[3])
            bans = sorted(bans, key=lambda x: x[3])
            for id_, user_id, reason, timestamp, added_by in warnings:
                reason = (reason[:25] + "...") if len(reason) > 25 else reason
                added_by = (added_by[:15] + "...") if len(added_by) > 15 else added_by
                rows.append(["Warning", reason, added_by, id_, self.format_timestamp(timestamp)])
            for id_, user_id, reason, timestamp, added_by, action in mutes:
                reason = (reason[:25] + "...") if len(reason) > 25 else reason
                added_by = (added_by[:15] + "...") if len(added_by) > 15 else added_by
                rows.append([action.capitalize(), reason, added_by, id_, self.format_timestamp(timestamp)])
            for id_, user_id, reason, timestamp, added_by, action in bans:
                reason = (reason[:25] + "...") if len(reason) > 25 else reason
                added_by = (added_by[:15] + "...") if len(added_by) > 15 else added_by
                rows.append([action.capitalize(), reason, added_by, id_, self.format_timestamp(timestamp)])
        else:
            all_entries = []
            for id_, user_id, reason, timestamp, added_by in warnings:
                all_entries.append((id_, "Warning", reason, timestamp, added_by))
            for id_, user_id, reason, timestamp, added_by, action in mutes:
                all_entries.append((id_, action.capitalize(), reason, timestamp, added_by))
            for id_, user_id, reason, timestamp, added_by, action in bans:
                all_entries.append((id_, action.capitalize(), reason, timestamp, added_by))
            all_entries = sorted(all_entries, key=lambda x: x[3])
            for id_, type_, reason, timestamp, added_by in all_entries:
                reason = (reason[:25] + "...") if len(reason) > 25 else reason
                added_by = (added_by[:15] + "...") if len(added_by) > 15 else added_by
                rows.append([type_, reason, added_by, id_, self.format_timestamp(timestamp)])
        table = self.format_table(rows)
        try:
            user = await self.bot.fetch_user(int(user_id))
            user_display = f"{user.name}#{user.discriminator} ({user_id})"
        except discord.NotFound:
            user_display = f"User ID {user_id} (not found)"
        await ctx.send(f"**History for {user_display}**\n{table}")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted", reason="Created for mute command")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False)
        if mute_role in member.roles:
            await ctx.send(f"{member.mention} is already muted.")
            return
        try:
            duration_seconds = self.parse_duration(duration)
        except ValueError as e:
            await ctx.send(str(e))
            return
        user_id = str(member.id)
        mute_id = self.generate_id(user_id, "mutes")
        await member.add_roles(mute_role, reason=reason)
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        c.execute("INSERT INTO mutes (id, user_id, reason, timestamp, added_by, action, duration) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                  (mute_id, user_id, reason, datetime.now().isoformat(), str(ctx.author), "mute", duration_seconds))
        conn.commit()
        conn.close()
        duration_display = duration_seconds // 60 if duration_seconds < 3600 else duration_seconds // 3600
        unit = "minutes" if duration_seconds < 3600 else "hours"
        await ctx.send(f"Muted {member.mention} for {duration_display} {unit} with reason: {reason}")
        try:
            await member.send(f"You were muted in {ctx.guild.name} for {duration_display} {unit} with reason: {reason}. You received the 'Muted' role.")
        except discord.Forbidden:
            await ctx.send(f"Could not DM {member.mention} (DMs disabled or bot blocked).")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        user_id = str(member.id)
        unmute_id = self.generate_id(user_id, "mutes")
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            await ctx.send("No 'Muted' role found. User is not muted.")
            return
        if mute_role in member.roles:
            await member.remove_roles(mute_role, reason=reason)
            conn = sqlite3.connect('cheaters.db')
            c = conn.cursor()
            c.execute("INSERT INTO mutes (id, user_id, reason, timestamp, added_by, action, duration) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                      (unmute_id, user_id, reason, datetime.now().isoformat(), str(ctx.author), "unmute", None))
            conn.commit()
            conn.close()
            await ctx.send(f"Unmuted {member.mention} for: {reason}")
            try:
                await member.send(f"You were unmuted in {ctx.guild.name} for: {reason}. The 'Muted' role was removed.")
            except discord.Forbidden:
                await ctx.send(f"Could not DM {member.mention} (DMs disabled or bot blocked).")
        else:
            await ctx.send(f"{member.mention} is not muted.")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        user_id = str(member.id)
        ban_id = self.generate_id(user_id, "bans")
        try:
            await member.send(f"You were banned from {ctx.guild.name} for: {reason}")
        except discord.Forbidden:
            await ctx.send(f"Could not DM {member.mention} (DMs disabled or bot blocked).")
        await member.ban(reason=reason)
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        c.execute("INSERT INTO bans (id, user_id, reason, timestamp, added_by, action) VALUES (?, ?, ?, ?, ?, ?)", 
                  (ban_id, user_id, reason, datetime.now().isoformat(), str(ctx.author), "ban"))
        conn.commit()
        conn.close()
        await ctx.send(f"Banned {member.mention} for: {reason}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user: str):
        banned_users = [entry async for entry in ctx.guild.bans()]
        user_id = None
        if "#" in user:
            name, discrim = user.split("#")
            for entry in banned_users:
                if entry.user.name == name and entry.user.discriminator == discrim:
                    user_id = entry.user.id
                    break
        else:
            try:
                user_id = int(user)
            except ValueError:
                await ctx.send("Please provide a valid user ID or username#discriminator.")
                return
        if user_id:
            user_id = str(user_id)
            unban_id = self.generate_id(user_id, "bans")
            try:
                await ctx.guild.unban(discord.Object(id=int(user_id)))
                conn = sqlite3.connect('cheaters.db')
                c = conn.cursor()
                c.execute("INSERT INTO bans (id, user_id, reason, timestamp, added_by, action) VALUES (?, ?, ?, ?, ?, ?)", 
                          (unban_id, user_id, "Unbanned", datetime.now().isoformat(), str(ctx.author), "unban"))
                conn.commit()
                conn.close()
                await ctx.send(f"Unbanned user with ID {user_id}.")
            except discord.Forbidden:
                await ctx.send("Failed to unban: Bot lacks permissions.")
            except discord.HTTPException:
                await ctx.send("Failed to unban: User not found in ban list.")
        else:
            await ctx.send("User not found in ban list.")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def remove(self, ctx: commands.Context, id: str):
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        c.execute("SELECT user_id, reason FROM warnings WHERE id = ?", (id,))
        warning = c.fetchone()
        if warning:
            c.execute("DELETE FROM warnings WHERE id = ?", (id,))
            conn.commit()
            conn.close()
            await ctx.send(f"Removed warning (ID {id}) for user ID {warning[0]}: {warning[1]}")
            return
        c.execute("SELECT user_id, reason, action FROM mutes WHERE id = ?", (id,))
        mute = c.fetchone()
        if mute:
            c.execute("DELETE FROM mutes WHERE id = ?", (id,))
            conn.commit()
            conn.close()
            await ctx.send(f"Removed {mute[2]} (ID {id}) for user ID {mute[0]}: {mute[1]}")
            return
        c.execute("SELECT user_id, reason, action FROM bans WHERE id = ?", (id,))
        ban = c.fetchone()
        if ban:
            c.execute("DELETE FROM bans WHERE id = ?", (id,))
            conn.commit()
            conn.close()
            await ctx.send(f"Removed {ban[2]} (ID {id}) for user ID {ban[0]}: {ban[1]}")
            return
        conn.close()
        await ctx.send(f"No history entry found with ID {id}.")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Track when a muted user leaves the server."""
        user_id = str(member.id)
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        c.execute("SELECT id, duration FROM mutes WHERE user_id = ? AND action = 'mute' AND duration IS NOT NULL ORDER BY timestamp DESC LIMIT 1", (user_id,))
        mute = c.fetchone()
        if mute:
            # User is muted; no action needed here, just ensure the mute entry persists
            pass
        conn.close()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Reapply mute if user was muted before leaving, reset duration, and DM them."""
        user_id = str(member.id)
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        c.execute("SELECT id, reason, duration FROM mutes WHERE user_id = ? AND action = 'mute' AND duration IS NOT NULL ORDER BY timestamp DESC LIMIT 1", (user_id,))
        mute = c.fetchone()
        if mute:
            mute_id, reason, duration = mute
            mute_role = discord.utils.get(member.guild.roles, name="Muted")
            if not mute_role:
                mute_role = await member.guild.create_role(name="Muted", reason="Created for mute command")
                for channel in member.guild.channels:
                    await channel.set_permissions(mute_role, send_messages=False)
            if mute_role not in member.roles:
                await member.add_roles(mute_role, reason=f"Reapplied mute after rejoin: {reason}")
                # Reset the mute duration by updating the timestamp
                new_timestamp = datetime.now().isoformat()
                c.execute("UPDATE mutes SET timestamp = ? WHERE id = ?", (new_timestamp, mute_id))
                conn.commit()
                duration_display = duration // 60 if duration < 3600 else duration // 3600
                unit = "minutes" if duration < 3600 else "hours"
                try:
                    await member.send(f"Leaving the server and rejoining resets the original mute duration. You have been remuted for {duration_display} {unit} with reason: {reason}. If you have any issues open a ticket by DM'ing <@1379580463265615922>")
                except discord.Forbidden:
                    pass  # Can't DM user, proceed silently
        conn.close()

    @commands.command(name='clear')
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, arg: str):
        log_entries = []

        async def log_message(msg):
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            log_entries.append(f"[{timestamp}] {msg.author} ({msg.author.id}): {msg.content}")

        try:
            if arg.isdigit():
                number = int(arg)

                if 1 <= number <= 100:
                    deleted = await ctx.channel.purge(limit=number + 1, before=ctx.message)
                    for msg in deleted:
                        await log_message(msg)

                    await ctx.send(f"✅ Deleted {len(deleted) - 1} messages.", delete_after=5)

                else:
                    target_message = await ctx.channel.fetch_message(number)
                    deleted = await ctx.channel.purge(limit=None, check=lambda m: m.created_at > target_message.created_at)

                    for msg in deleted:
                        await log_message(msg)

                    await ctx.send(f"✅ Deleted {len(deleted)} messages after the specified message.", delete_after=5)

                # --- Send log to logging channel ---
                log_channel = self.bot.get_channel(1377733230857551956)
                if log_entries and log_channel:
                    output = io.StringIO()
                    output.write(f"Command run by {ctx.author} ({ctx.author.id}) at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                    output.write(f"In channel: #{ctx.channel} (ID: {ctx.channel.id})\n\n")
                    output.write("\n".join(reversed(log_entries)))  # chronological order
                    output.seek(0)

                    file = discord.File(fp=output, filename="deleted_messages_log.txt")
                    await log_channel.send(file=file)

            else:
                await ctx.send("❌ Please enter a valid number of messages or message ID.", delete_after=5)

        except discord.NotFound:
            await ctx.send("❌ Message ID not found in this channel.", delete_after=5)
        except discord.Forbidden:
            await ctx.send("❌ I do not have permission to delete messages.", delete_after=5)
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to delete messages: {e}", delete_after=5)
                
async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
