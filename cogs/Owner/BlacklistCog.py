from discord.ext import commands
from util.owner import BlacklistQueries, BlacklistUtils
from datetime import datetime
import logging

class BlacklistCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="blacklist", description="Blacklist a user, channel, guild, or show records")
    @commands.is_owner()
    async def blacklist(self, ctx, user_or_channel: str = None, duration: int = None):
        if user_or_channel is None:
            await ctx.send("❌ Argument required: Please provide a user, channel, guild, or 'records'.")
            return

        if user_or_channel.lower() == "records":
            all_data = await BlacklistQueries.all_blacklisted(guild_id=None, include_fields=True)
            all_entries = []
            for row in all_data:
                # Support both dict and tuple
                if isinstance(row, dict):
                    entry = {
                        "user_id": row.get("user_id"),
                        "channel_id": row.get("channel_id"),
                        "guild_id": row.get("guild_id"),
                        "added_at": row.get("added_at"),
                        "duration_seconds": row.get("duration_seconds"),
                        "expires_at": row.get("expires_at"),
                        "active": row.get("active"),
                    }
                else:
                    entry = {
                        "user_id": row[0],
                        "channel_id": row[1],
                        "guild_id": row[2],
                        "added_at": row[3],
                        "duration_seconds": row[4],
                        "expires_at": row[5],
                        "active": row[6],
                    }
                # Convert date strings to datetime for sorting
                for key in ["added_at", "expires_at"]:
                    val = entry[key]
                    if isinstance(val, str):
                        try:
                            entry[key] = datetime.fromisoformat(val)
                        except Exception:
                            entry[key] = None
                all_entries.append(entry)

            # Sort: active first, then by expires_at (None last)
            def sort_key(x):
                expires = x["expires_at"]
                return (not x["active"], expires or datetime.max)
            all_entries.sort(key=sort_key)

            if not all_entries:
                await ctx.send("No blacklist records found.")
                return

            header = "**Blacklist Records:**"
            lines = []
            for entry in all_entries:
                user_display = None
                channel_display = None
                guild_display = None

                # Try to resolve user, channel, or guild names
                if entry["user_id"]:
                    try:
                        user_obj = await ctx.bot.fetch_user(int(entry["user_id"]))
                        user_display = f"`{user_obj}` ({entry['user_id']})"
                    except Exception:
                        user_display = f"{entry['user_id']} (unknown user)"
                if entry["channel_id"]:
                    channel = ctx.bot.get_channel(int(entry["channel_id"]))
                    if channel:
                        channel_display = f"`{channel.name}` ({entry['channel_id']})"
                    else:
                        channel_display = f"{entry['channel_id']} (unknown channel)"
                if entry["guild_id"]:
                    guild = ctx.bot.get_guild(int(entry["guild_id"]))
                    if guild:
                        guild_display = f"`{guild.name}` ({entry['guild_id']})"
                    else:
                        guild_display = f"{entry['guild_id']} (unknown guild)"

                target = (
                    f"User {user_display}" if entry["user_id"] else
                    f"Channel {channel_display}" if entry["channel_id"] else
                    f"Guild {guild_display}" if entry["guild_id"] else "Unknown"
                )
                added = entry["added_at"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(entry["added_at"], datetime) else str(entry["added_at"]) if entry["added_at"] else "N/A"
                duration = f"{entry['duration_seconds']}s" if entry["duration_seconds"] else "Permanent"
                expires = entry["expires_at"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(entry["expires_at"], datetime) else str(entry["expires_at"]) if entry["expires_at"] else "Never"
                status = "🟢 Active" if entry["active"] else "🔴 Expired"
                lines.append(f"{status} | {target} | Added: {added} | Duration: {duration} | Expires: {expires}")

            # Split into pages under 2000 chars
            pages = []
            current = header
            for line in lines:
                if len(current) + len(line) + 1 > 1990:  # 10 chars buffer for safety
                    pages.append(current)
                    current = header
                current += "\n" + line
            if current != header:
                pages.append(current)

            # Send paginated messages
            for i, page in enumerate(pages):
                page_header = f"{header} (Page {i+1}/{len(pages)})\n" if len(pages) > 1 else header + "\n"
                await ctx.send(page_header + page[len(header):])  # Remove duplicate header in page

            return

        # Resolve target
        user_id, channel_id, guild_id = await BlacklistUtils.resolve_blacklist_target(ctx.bot, ctx, user_or_channel)
        if not any([user_id, channel_id, guild_id]):
            await ctx.send("Please provide a valid user mention, user ID, channel ID, or 'guild'.")
            return

        # Ensure only one target is set
        if user_id:
            channel_id = None
            guild_id = None
        elif channel_id:
            user_id = None
            guild_id = None
        elif guild_id:
            user_id = None
            channel_id = None

        # Check if already blacklisted
        already_blacklisted = await BlacklistQueries.check_blacklist(
            user_id=user_id,
            channel_id=channel_id,
            guild_id=guild_id
        )
        if already_blacklisted:
            target = (
                f"user {user_id}" if user_id else
                f"channel {channel_id}" if channel_id else
                f"guild {guild_id}" if guild_id else "unknown"
            )
            await ctx.send(f"❌ {target.capitalize()} is already blacklisted.")
            return

        await BlacklistQueries.add_to_blacklist(
            user_id=user_id,
            channel_id=channel_id,
            guild_id=guild_id,
            added_by=ctx.author.id,
            duration_seconds=duration,  # None means permanent
            active=True
        )
        # Logging
        target = (
            f"user {user_id}" if user_id else
            f"channel {channel_id}" if channel_id else
            f"guild {guild_id}" if guild_id else "unknown"
        )
        logger = logging.getLogger("dmzcord.blacklist")
        logger.info(f"{ctx.author} ({ctx.author.id}) blacklisted {target} (duration: {duration or 'permanent'})")

        if user_id:
            await ctx.send(f"User `{user_id}` has been globally blacklisted." + (f" (for {duration} seconds)" if duration else ""))
        elif channel_id:
            await ctx.send(f"Channel `{channel_id}` has been blacklisted." + (f" (for {duration} seconds)" if duration else ""))
        elif guild_id:
            await ctx.send(f"Guild `{guild_id}` has been blacklisted." + (f" (for {duration} seconds)" if duration else ""))

    @commands.hybrid_command(name="unblacklist", description="Remove a user, channel, or guild from the blacklist")
    @commands.is_owner()
    async def unblacklist(self, ctx, user_or_channel: str = None):
        if user_or_channel is None:
            await ctx.send("❌ Argument required: Please provide a user, channel, or guild to unblacklist.")
            return

        # Use the same resolution logic as blacklist
        user_id, channel_id, guild_id = await BlacklistUtils.resolve_blacklist_target(ctx.bot, ctx, user_or_channel)
        if not any([user_id, channel_id, guild_id]):
            await ctx.send("Please provide a valid user mention, user ID, channel ID, or 'guild'.")
            return

        # Ensure only one target is set
        if user_id:
            channel_id = None
            guild_id = None
        elif channel_id:
            user_id = None
            guild_id = None
        elif guild_id:
            user_id = None
            channel_id = None

        await BlacklistQueries.remove_from_blacklist(
            user_id=user_id,
            channel_id=channel_id,
            guild_id=guild_id,
            active=False
        )
        # Logging
        target = (
            f"user {user_id}" if user_id else
            f"channel {channel_id}" if channel_id else
            f"guild {guild_id}" if guild_id else "unknown"
        )
        logger = logging.getLogger("dmzcord.blacklist")
        logger.info(f"{ctx.author} ({ctx.author.id}) unblacklisted {target}")

        if user_id:
            await ctx.send(f"User `{user_id}` has been removed from the global blacklist.")
        elif channel_id:
            await ctx.send(f"Channel `{channel_id}` has been removed from the blacklist.")
        elif guild_id:
            await ctx.send(f"Guild `{guild_id}` has been removed from the blacklist.")

async def setup(bot):
    await bot.add_cog(BlacklistCog(bot))