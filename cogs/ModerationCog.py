import discord
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, timedelta
import re
import os
from dotenv import load_dotenv
import io
from cogs.utils import get_setting

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
        conn = sqlite3.connect('dmzcord.db')
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
        max_duration = 604800
        match = re.match(r'^(\d+)([mh])$', duration_str.lower())
        if not match:
            raise ValueError("Duration must be in the format '15m', '45m', '1h', or '24h' (e.g., 15 minutes, 1 hour).")
        value, unit = int(match.group(1)), match.group(2)
        if unit == 'm':
            seconds = value * 60
        elif unit == 'h':
            seconds = value * 3600
        if seconds > max_duration:
            seconds = max_duration
        return seconds

    @tasks.loop(minutes=1)
    async def check_mutes(self):
        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()
        c.execute("SELECT id, user_id, timestamp, duration FROM mutes WHERE action = 'mute' AND duration IS NOT NULL")
        mutes = c.fetchall()
        current_time = datetime.now()
        for mute_id, user_id, timestamp, duration in mutes:
            mute_start = datetime.fromisoformat(timestamp)
            mute_end = mute_start + timedelta(seconds=duration)
            if current_time >= mute_end:
                guild = self.bot.get_guild(int(os.getenv('GUILD_ID')))
                if not guild:
                    continue
                member = guild.get_member(int(user_id))
                mute_role = discord.utils.get(guild.roles, name="Muted") if guild else None
                # Always log the unmute, even if the member isn't in the server
                unmute_id = self.generate_id(user_id, "mutes")
                c.execute("INSERT INTO mutes (id, user_id, reason, timestamp, added_by, action) VALUES (?, ?, ?, ?, ?, ?)",
                          (unmute_id, user_id, "Mute duration expired", datetime.now().isoformat(), "Bot", "unmute"))
                if member and mute_role and mute_role in member.roles:
                    await member.remove_roles(mute_role, reason="Mute duration expired")
                conn.commit()
        conn.close()

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """!warn <member> [reason]"""
        user_id = str(member.id)
        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (user_id,))
        warning_count = c.fetchone()[0] + 1
        warn_id = self.generate_id(user_id, "warnings")
        c.execute("INSERT INTO warnings (id, user_id, reason, timestamp, added_by) VALUES (?, ?, ?, ?, ?)", 
                  (warn_id, user_id, reason, datetime.now().isoformat(), str(ctx.author)))
        conn.commit()
        await ctx.send(f"Warned {member.mention} for: {reason} (Warning #{warning_count})")
        try:
            await member.send(f"You were warned in {ctx.guild.name} for: {reason} (Warning #{warning_count})")
        except discord.Forbidden:
            await ctx.send(f"Could not DM {member.mention} (DMs disabled or bot blocked).")
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted", reason="Created for mute command")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False)
        if warning_count == 1:
            pass
        elif warning_count == 2:
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
    async def history(self, ctx: commands.Context, arg: str = None, *args: str):
        """!history <user_id||W-|M-|B-> [sort]"""
        id_pattern = re.compile(r'^[WMB]-\d{4}-\d{4}$')
        # If arg is None, default to "all"
        if arg is None:
            arg = "all"
        if id_pattern.match(arg):
            conn = sqlite3.connect('dmzcord.db')
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

        if arg.lower() == "all":
            sort_by_type = args and args[-1].lower() == "sort"
            conn = sqlite3.connect('dmzcord.db')
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

        try:
            user_id = str(int(arg))
        except ValueError:
            await ctx.send("Please provide a valid user ID, history entry ID (e.g., W-6750-0005), or use '!history all'.")
            return
        sort_by_type = args and args[-1].lower() == "sort"
        conn = sqlite3.connect('dmzcord.db')
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
        """!mute <member> <duration> [reason]"""
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
        conn = sqlite3.connect('dmzcord.db')
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
        """!unmute <member> [reason]"""
        user_id = str(member.id)
        unmute_id = self.generate_id(user_id, "mutes")
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            await ctx.send("No 'Muted' role found. User is not muted.")
            return
        if mute_role in member.roles:
            await member.remove_roles(mute_role, reason=reason)
            conn = sqlite3.connect('dmzcord.db')
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
        """!ban <member> [reason]"""
        user_id = str(member.id)
        ban_id = self.generate_id(user_id, "bans")
        try:
            await member.send(f"You were banned from {ctx.guild.name} for: {reason}")
        except discord.Forbidden:
            await ctx.send(f"Could not DM {member.mention} (DMs disabled or bot blocked).")
        await member.ban(reason=reason)
        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()
        c.execute("INSERT INTO bans (id, user_id, reason, timestamp, added_by, action) VALUES (?, ?, ?, ?, ?, ?)", 
                  (ban_id, user_id, reason, datetime.now().isoformat(), str(ctx.author), "ban"))
        conn.commit()
        conn.close()
        await ctx.send(f"Banned {member.mention} for: {reason}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user: str):
        """!unban <user_id|username#discriminator>"""
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
                conn = sqlite3.connect('dmzcord.db')
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
        """!remove <W-xxxx-yyyy>"""
        conn = sqlite3.connect('dmzcord.db')
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

    @commands.command(name='clear')
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, arg: str):
        """!clear <number|message_id>"""
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
                log_channel_id = get_setting('log_channel_id')
                log_channel = self.bot.get_channel(int(log_channel_id)) if log_channel_id else None
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

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        user_id = str(member.id)
        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()
        c.execute("SELECT id, duration FROM mutes WHERE user_id = ? AND action = 'mute' AND duration IS NOT NULL ORDER BY timestamp DESC LIMIT 1", (user_id,))
        mute = c.fetchone()
        if mute:
            pass
        conn.close()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        user_id = str(member.id)
        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()
        c.execute("SELECT id, reason, duration FROM mutes WHERE user_id = ? AND action = 'mute' AND duration IS NOT NULL ORDER BY timestamp DESC LIMIT 1", (user_id,))
        mute = c.fetchone()
        
        log_channel_id = get_setting('log_channel_id')
        log_channel = self.bot.get_channel(int(log_channel_id)) if log_channel_id else None
        
        if mute:
            mute_id, reason, duration = mute
            # Check if mute is still active
            mute_start = datetime.fromisoformat(c.execute("SELECT timestamp FROM mutes WHERE id = ?", (mute_id,)).fetchone()[0])
            mute_end = mute_start + timedelta(seconds=duration)
            current_time = datetime.now()
            
            if current_time < mute_end:  # Mute is still active
                mute_role = discord.utils.get(member.guild.roles, name="Muted")
                if not mute_role:
                    mute_role = await member.guild.create_role(name="Muted", reason="Created for mute command")
                    for channel in member.guild.channels:
                        await channel.set_permissions(mute_role, send_messages=False)
                
                if mute_role not in member.roles:
                    await member.add_roles(mute_role, reason=f"Reapplied mute after rejoin: {reason}")
                
                # Update timestamp regardless of role application
                new_timestamp = datetime.now().isoformat()
                c.execute("UPDATE mutes SET timestamp = ? WHERE id = ?", (new_timestamp, mute_id))
                conn.commit()
                
                duration_display = duration // 60 if duration < 3600 else duration // 3600
                unit = "minutes" if duration < 3600 else "hours"
                support_user_id = str(self.bot.user.id)
                support_mention = f"<@{support_user_id}>"
                
                # Send DM regardless of whether the role was applied
                try:
                    await member.send(f"Leaving the server and rejoining resets the original mute duration. You have been remuted for {duration_display} {unit} with reason: {reason}. If you have any issues open a ticket by DM'ing {support_mention}")
                except discord.Forbidden:
                    pass
        conn.close()

    @commands.command(name="moderation")
    @commands.has_permissions(administrator=True)
    async def moderation(self, ctx: commands.Context):
        """Show all current mutes and bans"""
        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()

        # Fetch active mutes (action='mute' and duration not expired if duration is set)
        c.execute("SELECT id, user_id, reason, timestamp, added_by, duration FROM mutes WHERE action = 'mute'")
        mutes = c.fetchall()

        # Fetch active bans (action='ban')
        c.execute("SELECT id, user_id, reason, timestamp, added_by FROM bans WHERE action = 'ban'")
        bans = c.fetchall()

        conn.close()

        rows = [["Type", "User ID", "Reason", "Timestamp", "Added By", "Duration/Action", "Mute End"]]
        now = datetime.now()

        # Process mutes
        for mute in mutes:
            id_, user_id, reason, timestamp, added_by, duration = mute
            mute_end = ""
            if duration:
                mute_start = datetime.fromisoformat(timestamp)
                mute_end_dt = mute_start + timedelta(seconds=duration)
                mute_end = mute_end_dt.strftime("%d-%m-%Y %H:%M:%S")
                # Only show if mute is still active
                if now > mute_end_dt:
                    continue
            else:
                mute_end = "N/A"
            rows.append([
                "Mute", user_id, (reason[:25] + "...") if len(reason) > 25 else reason,
                self.format_timestamp(timestamp), (added_by[:15] + "...") if len(added_by) > 15 else added_by,
                str(duration) if duration else "N/A", mute_end
            ])

        # Process bans
        for ban in bans:
            id_, user_id, reason, timestamp, added_by = ban
            rows.append([
                "Ban", user_id, (reason[:25] + "...") if len(reason) > 25 else reason,
                self.format_timestamp(timestamp), (added_by[:15] + "...") if len(added_by) > 15 else added_by,
                "ban", "N/A"
            ])

        if len(rows) == 1:
            await ctx.send("There are currently no active mutes or bans.")
            return

        table = self.format_table(rows)
        await ctx.send(f"**Current Mutes and Bans**\n{table}")

    @commands.command(name="setstatus")
    @commands.has_permissions(administrator=True)
    async def setstatus(self, ctx: commands.Context, status: str, activity_type: str = "playing", *, activity: str = None):
        """!setstatus <status> <activity_type> [activity]"""
        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }
        activity_type_map = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "streaming": discord.ActivityType.streaming
        }
        status_lower = status.lower()
        activity_type_lower = activity_type.lower()
        if status_lower not in status_map:
            await ctx.send("Invalid status. Choose from: online, idle, dnd, invisible.")
            return
        if activity_type_lower not in activity_type_map:
            await ctx.send("Invalid activity type. Choose from: playing, watching, listening, streaming.")
            return

        discord_status = status_map[status_lower]
        activity_obj = None
        if activity:
            if activity_type_lower == "streaming":
                activity_obj = discord.Streaming(name=activity, url="https://twitch.tv/")
            else:
                activity_obj = discord.Activity(type=activity_type_map[activity_type_lower], name=activity)

        await self.bot.change_presence(status=discord_status, activity=activity_obj)
        await ctx.send(
            f"Bot status set to **{status_lower}** with activity type **{activity_type_lower}**"
            f"{' and activity: ' + activity if activity else ''}."
        )

    @commands.command(name="echo", description="Repeats your message in the specified channel with custom emojis. Usage: !echo <channel_id> <text with emoji IDs> [animated:yes/no]")
    @commands.has_permissions(manage_messages=True)
    async def echo(self, ctx, channel_id: int, *, text: str):
        """!echo <channel_id> <text with emoji IDs> [animated:yes/no]"""
        try:
            # Fetch the channel using the provided channel ID
            channel = self.bot.get_channel(channel_id)
            
            # Check if the channel exists
            if channel is None:
                await ctx.send("Error: Channel not found. Please provide a valid channel ID.")
                return
            
            # Check if the bot has permission to send messages in the channel
            if not channel.permissions_for(ctx.guild.me).send_messages:
                await ctx.send("Error: I don't have permission to send messages in that channel.")
                return
            
            # Split the text to check for the animated flag at the end
            parts = text.split()
            is_animated = False
            message_text = text

            # Check if the last part is an animated flag
            if parts and parts[-1].lower() in ["yes", "no"]:
                animated_flag = parts[-1].lower()
                is_animated = animated_flag == "yes"
                message_text = " ".join(parts[:-1])  # Remove the animated flag from the message

            # Find all emoji IDs in the message (17-19 digit numbers), but exclude those in role pings
            # Use negative lookahead to avoid matching numbers inside <@&...>
            emoji_ids = re.findall(r'\b\d{17,19}\b(?![^<]*>)', message_text)
            
            # Format each emoji ID and replace it in the message
            formatted_message = message_text
            for emoji_id in emoji_ids:
                # Use a placeholder name since the user doesn't provide the emoji name
                emoji_name = "customemoji"
                emoji_format = f"<a:{emoji_name}:{emoji_id}>" if is_animated else f"<:{emoji_name}:{emoji_id}>"
                # Replace the raw emoji ID with the formatted emoji
                formatted_message = re.sub(r'\b' + emoji_id + r'\b(?![^<]*>)', emoji_format, formatted_message)

            # Send the formatted message to the specified channel
            await channel.send(formatted_message)
            
            # Confirm to the user that the message was sent
            await ctx.send(f"Message sent to {channel.mention}!")

        except ValueError:
            await ctx.send("Error: Please provide a valid channel ID (it should be a number).")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
