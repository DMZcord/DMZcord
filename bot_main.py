import json
import os
import sys
import time
from dotenv import load_dotenv
import discord
from discord.ext import commands
from util.core import Startup, DMZcordLogger, Database, Filters, DiscordLogHandler
import logging
import asyncio
from util.voice import MusicCacheManager
import aiomysql
from bot_events import setup_event_handlers, start_background_tasks

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)  # Force INFO logs to console
DMZcordLogger().setup()
logger = logging.getLogger(__name__)

discord_logger = logging.getLogger("discord.ext.commands.bot")
discord_logger.addFilter(Filters.filterlogs)
# --- Environment & Intents ---
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

STARTUP_TIME = time.perf_counter()

class MyBot(commands.Bot):
    """Custom Discord bot for DMZcord."""

    def __init__(self, *args, **kwargs):    
        super().__init__(*args, **kwargs)
        self.command_stats = {}
        self.startup_log_lines = []
        self.cog_load_results = []
        self._vacuum_done = False
        self._synced_commands = 0
        self._startup_complete = False
        self._guild_lines = []
        self._presence_str = ""     
        self._startup_elapsed = 0.0
        self._bot_ready_name = ""
        self._connected_guilds = []
        self.log_channel_cache = None

    async def setup_hook(self):
        self.startup_log_lines.append("\n" + "="*40 + f"\nStarting bot process (PID: {os.getpid()})...")
        self.startup_log_lines.append("🤖 MyBot initialized.")
        self.startup_log_lines.append("⚙️ Starting setup_hook...")

        music_result = MusicCacheManager.clear_music_cache()
        self.startup_log_lines.append(str(music_result))

        vacuum_result = await Database.vacuum_report()
        self.startup_log_lines.append(str(vacuum_result))

        def find_cogs(base_dir="cogs"):
            cogs = []
            for root, dirs, files in os.walk(base_dir):
                if "WIP" in root.split(os.sep):
                    continue
                for file in files:
                    if file.endswith("Cog.py"):
                        rel_path = os.path.relpath(os.path.join(root, file), base_dir)
                        module = rel_path.replace(os.sep, ".")[:-3]
                        cogs.append(f"cogs.{module}")
            return cogs
        cog_files = find_cogs()
        for cog in cog_files:
            start = time.perf_counter()
            try:
                await self.load_extension(cog)
                elapsed = time.perf_counter() - start
                self.cog_load_results.append(f"  [OK]   {cog} ({elapsed:.2f}s)")
            except Exception as e:
                elapsed = time.perf_counter() - start
                self.cog_load_results.append(
                    f"  [FAIL] {cog} ({elapsed:.2f}s) ({e})")
        self.startup_log_lines.append(
            "="*40 + "\nLoaded Cogs:\n" +
            "\n".join(self.cog_load_results) + "\n" + "="*40
        )

        # Sync global slash commands
        try:
            synced = await self.tree.sync()
            self._synced_commands = len(synced)
        except Exception as e:
            logger.error("Failed to sync commands: %s", e, exc_info=True)

        self.db = await aiomysql.create_pool(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            db=os.getenv("DB_NAME"),
            autocommit=True
        )

        # Load and cache logging level from DB
        await Startup.load_logging_settings(self)
        # Fetch log_channel_id from the logging settings table
        log_channel_id = None
        async with self.db.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT log_channel FROM logging WHERE `key` = 'logging_level' LIMIT 1")
                row = await cursor.fetchone()
                if row and row[0]:
                    log_channel_id = row[0]
        if log_channel_id:
            self.log_channel_cache = int(log_channel_id)

        # Attach DiscordLogHandler if log_channel_cache is set
        if getattr(self, "log_channel_cache", None):
            discord_handler = DiscordLogHandler(self)
            discord_handler.setFormatter(logging.Formatter("[%(asctime)s]: %(message)s"))
            logging.getLogger().addHandler(discord_handler)

        # Register event handlers (will add to startup_log_lines)
        setup_event_handlers(self)
        
        # Start background tasks (will add to startup_log_lines)
        start_background_tasks(self)

        self.add_check(Startup.global_blacklist_check)

    async def on_ready(self):

        # Startup complete
        elapsed = time.perf_counter() - STARTUP_TIME
        self._startup_elapsed = elapsed
        self.startup_log_lines.append(f"Bot process startup complete in {elapsed:.2f} seconds (PID: {os.getpid()})")
        
        # Bot ready
        self._bot_ready_name = f"Bot is ready as {self.user}"
        self.startup_log_lines.append(self._bot_ready_name)
        
        # Synced commands
        self.startup_log_lines.append(f"Synced {self._synced_commands} global command(s)")

        # Connected guilds
        guild_lines = [f"  {guild.name} ({guild.id})" for guild in self.guilds]
        self._connected_guilds = guild_lines
        self.startup_log_lines.append("="*40 + "\nConnected Guilds:\n" + "\n".join(guild_lines) + "\n" + "="*40)
        startup_message = "\n".join(self.startup_log_lines)
        logger.info(startup_message)

        # Edit restart message if needed
        restart_file = "restart_status.json"
        if os.path.exists(restart_file):
            try:
                with open(restart_file, "r") as f:
                    data = json.load(f)
                channel = self.get_channel(data["channel_id"])
                if channel:
                    msg = await channel.fetch_message(data["message_id"])
                    elapsed = time.time() - data.get("timestamp", time.time())
                    elapsed_str = f"{elapsed:.2f} seconds"
                    await msg.edit(content=f"✅ Restart complete! Bot is back online. (Took {elapsed_str})")
                os.remove(restart_file)
            except Exception as e:
                logger.error("Failed to update restart message: %s", e)

def main():
    bot = MyBot(command_prefix='!', help_command=None, intents=intents,
                case_insensitive=True,
                owner_id=674779677172170755,
                status=discord.Status.online,
                activity=discord.Activity(type=discord.ActivityType.listening,
                name="to DM's!"))

    async def setup_logging_and_run():
        if not BOT_TOKEN:
            logger.error("Error: BOT_TOKEN not found in .env file.")
            return
        try:
            await bot.start(BOT_TOKEN)
        except KeyboardInterrupt:
            logger.info("Bot shutting down...")
            await bot.close()
        except Exception as e:
            logger.error("Error running bot: %s", e, exc_info=True)
        if getattr(bot, "_do_restart", False):
            os.execv(sys.executable, [sys.executable] + sys.argv)

    asyncio.run(setup_logging_and_run())

if __name__ == "__main__":
    main()
