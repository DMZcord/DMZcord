import statistics
import discord
import sys
import psutil
import os
import time
import aiohttp
from util.core.database import Database

class DebugEmbeds:
    @staticmethod
    def build_status_embed(bot, all_cogs):
        loaded_extensions = set(bot.extensions.keys())
        lines = []
        for ext in all_cogs:
            status = "🟢" if ext in loaded_extensions else "🔴"
            lines.append(f"{status} {ext}")
        embed = discord.Embed(
            title="🔄 Reload/Unload a Cog",
            description="Use the dropdowns below to reload or unload a cog.",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="Cogs Status",
            value="\n".join(lines) if lines else "No cogs found.",
            inline=False
        )
        return embed

    @staticmethod
    async def build_botinfo_embed(bot, info, uptime_str):
        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent(interval=0.1)
        python_version = sys.version.split()[0]
        dpy_version = discord.__version__

        # Commit hash/version
        commit_hash = os.getenv("GIT_COMMIT")
        if not commit_hash:
            try:
                with open("version.txt") as f:
                    commit_hash = f.read().strip()
            except Exception:
                commit_hash = "Unknown"

        # Channel counts
        total_text_channels = sum(len(guild.text_channels) for guild in bot.guilds)
        total_voice_channels = sum(len(guild.voice_channels) for guild in bot.guilds)

        # PebbleHost API stats
        pebble_stats = None
        api_key = os.getenv("PEBBLEHOST_API_KEY")
        server_id = os.getenv("PEBBLEHOST_SERVER_ID")
        if api_key and server_id:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json"
            }
            url = f"https://panel.pebblehost.com/api/client/servers/{server_id}/resources"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            stats = data["attributes"]["resources"]
                            pebble_stats = stats
                        else:
                            pebble_stats = None
            except Exception as e:
                pebble_stats = None
        else:
            pebble_stats = None

        # Latency: WebSocket, API, and DB
        ws_latency = bot.latency * 1000  # ms

        # API latency
        start = time.perf_counter()
        try:
            await bot.application_info()
            api_latency = (time.perf_counter() - start) * 1000
        except Exception:
            api_latency = -1

        # DB latency
        db_latency = -1
        try:
            pool = getattr(bot, "db", None)
            if pool:
                start_db = time.perf_counter()
                async with pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT 1")
                        await cur.fetchone()
                db_latency = (time.perf_counter() - start_db) * 1000
        except Exception:
            db_latency = -1

        latency_str = (
            f"WS: {ws_latency:.2f}ms\n"
            f"API: {api_latency:.2f}ms\n"
            f"DB: {db_latency:.2f}ms"
            if api_latency >= 0 and db_latency >= 0
            else f"WS: {ws_latency:.2f}ms\nAPI: {'N/A' if api_latency < 0 else f'{api_latency:.2f}ms'}\nDB: {'N/A' if db_latency < 0 else f'{db_latency:.2f}ms'}"
        )

        # Calculate memory percent (always out of 1 GB)
        if pebble_stats and isinstance(pebble_stats, dict):
            mem_percent = (pebble_stats['memory_bytes'] / (1024**3)) * 100
        else:
            mem_percent = (mem_mb / 1024) * 100  # mem_mb / 1024 MB = fraction of 1GB

        # Usage field (CPU, Memory, DB) - always 3 lines
        if pebble_stats and isinstance(pebble_stats, dict):
            usage_str = (
                f"CPU: {pebble_stats['cpu_absolute']:.2f}%\n"
                f"Mem: {pebble_stats['memory_bytes'] / (1024**2):.2f} MB ({mem_percent:.2f}%)\n"
                f"DB: {pebble_stats['disk_bytes'] / (1024**3):.2f} GB"
            )
        else:
            usage_str = (
                f"CPU: {cpu_percent:.2f}%\n"
                f"Mem: {mem_mb:.2f} MB ({mem_percent:.2f}%)\n"
                f"DB: {getattr(bot, 'db_size', 'N/A')} MB (0.00%)"
            )

        # Combined channels
        channels_str = f"📃 {total_text_channels}  🔊 {total_voice_channels}"

        embed = discord.Embed(
            title="🤖 Bot Instance Information",
            color=discord.Color.blue()
        )
        # Top row
        embed.add_field(
            name="📈 Stats",
            value=f"Servers: {len(bot.guilds)}\nUsers: {len(bot.users)}\nCommands: {len(bot.commands)}",
            inline=True
        )
        embed.add_field(
            name="🏓 Latency",
            value=latency_str,
            inline=True
        )
        embed.add_field(
            name="📊 Usage",
            value=usage_str,
            inline=True
        )
        # Second row
        embed.add_field(
            name="📺 Channels",
            value=channels_str,
            inline=True
        )
        embed.add_field(
            name="⏰ Uptime",
            value=uptime_str,
            inline=True
        )
        embed.add_field(
            name="🔗 Support",
            value="[Support Server](https://discord.gg/CHUynnZdae)",
            inline=True
        )
        # Footer: PID, Python, discord.py, Version
        embed.set_footer(
            text=f"📊 PID: {info['pid']}   🐍 Python: {python_version}   📦 Discord.py: {dpy_version}   📝 Github: {commit_hash}"
        )
        # Thumbnail: Bot profile picture
        if bot.user and bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        elif bot.user and bot.user.display_avatar:
            embed.set_thumbnail(url=bot.user.display_avatar.url)
        return embed

    @staticmethod
    def build_commandstats_embed(stats):
        embed = discord.Embed(
            title="📊 Command Usage Stats",
            color=discord.Color.green(),
            description="Statistics for global command usage"
        )
        header = f"{'Commmand':<12}{'Run':>4}{'Avg':>6}{'Med':>6}{'Min':>6}{'Max':>6}"
        lines = [header, "-" * len(header)]
        for stat in stats:
            times = stat.get("times", [])
            median = statistics.median(times) if times else stat["avg_time"]
            cmd = stat['command_name'][:12]
            lines.append(
                f"{cmd:<12}{stat['count']:>4}{stat['avg_time']:>6.2f}{median:>6.2f}{stat['min_time']:>6.2f}{stat['max_time']:>6.2f}"
            )
        embed.add_field(
            name="📊 Stats",
            value="```\n" + "\n".join(lines) + "\n```",
            inline=False
        )
        return embed

    @staticmethod
    async def build_commandabuse_embed(stats, blacklist_stats, bot):
        embed = discord.Embed(
            title="🚨 Command Abuse Stats",
            color=discord.Color.orange()
        )

        # Top 10 most active users
        user_lines = []
        for stat in stats:
            try:
                user = bot.get_user(int(stat['user_id']))
                if user is None:
                    user = await bot.fetch_user(int(stat['user_id']))
                user_display = user.mention if user else f"<@{stat['user_id']}>"
            except Exception:
                user_display = f"<@{stat['user_id']}>"
            user_lines.append(
                f"👤 {user_display}: {stat['total_runs']} runs, avg {stat['avg_time']:.2f}s, max {stat['max_time']:.2f}s"
            )
        embed.add_field(
            name="🏅 Top 10 Most Active Users",
            value="\n".join(user_lines) if user_lines else "No data.",
            inline=False
        )

        # Top 5 most blacklisted users
        bl_lines = []
        if blacklist_stats:
            for user in blacklist_stats:
                try:
                    user_obj = bot.get_user(int(user['user_id']))
                    if user_obj is None:
                        user_obj = await bot.fetch_user(int(user['user_id']))
                    user_display = user_obj.mention if user_obj else f"<@{user['user_id']}>"
                except Exception:
                    user_display = f"<@{user['user_id']}>"
                bl_lines.append(f"⛔ {user_display}: {user['count']} blacklist entries")
        else:
            bl_lines.append("No blacklist data found.")

        embed.add_field(
            name="🚫 Top 5 Most Blacklisted Users",
            value="\n".join(bl_lines),
            inline=False
        )
        return embed