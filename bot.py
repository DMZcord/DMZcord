import discord
from discord.ext import commands
import sqlite3
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Load environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')
MODMAIL_LOG_CHANNEL_ID = os.getenv('MODMAIL_LOG_CHANNEL_ID')

# Set up intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

# Define custom bot class
class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registered_commands = []
        print("MyBot initialized.")

    async def setup_hook(self):
        print("Starting setup_hook...")
        # Create database tables
        self.create_tables()

        # Load cogs dynamically from the cogs directory
        cog_dir = "cogs"
        if not os.path.exists(cog_dir):
            print(f"Error: '{cog_dir}' directory not found. Creating it...")
            os.makedirs(cog_dir)
        
        cog_files = [f[:-3] for f in os.listdir(cog_dir) if f.endswith('.py') and f != '__init__.py' and f != 'utils.py']
        print(f"Found cog files: {cog_files}")

        for cog in cog_files:
            try:
                await self.load_extension(f'{cog_dir}.{cog}')
                print(f"Successfully loaded cog: {cog}")
            except Exception as e:
                print(f"Failed to load cog {cog}: {str(e)}")

        # Sync commands
        try:
            synced = await self.tree.sync(guild=discord.Object(id=int(GUILD_ID)))
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    def create_tables(self):
        print("Creating database tables...")
        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS cheaters (
                     activision_id TEXT PRIMARY KEY,
                     reason TEXT,
                     timestamp TEXT,
                     added_by TEXT
                     )''')
        # Prepopulate with an example cheater
        example_activision_id = "ExampleCheater#1234567"
        c.execute("INSERT OR IGNORE INTO cheaters (activision_id, reason, timestamp, added_by) VALUES (?, ?, ?, ?)",
                  (example_activision_id, "Example cheater entry", datetime.now().isoformat(), "Bot"))
        c.execute('''CREATE TABLE IF NOT EXISTS warnings (
                     id TEXT PRIMARY KEY,
                     user_id TEXT,
                     reason TEXT,
                     timestamp TEXT,
                     added_by TEXT
                     )''')
        c.execute('''CREATE TABLE IF NOT EXISTS mutes (
                     id TEXT PRIMARY KEY,
                     user_id TEXT,
                     reason TEXT,
                     timestamp TEXT,
                     added_by TEXT,
                     action TEXT,
                     duration INTEGER
                     )''')
        c.execute('''CREATE TABLE IF NOT EXISTS bans (
                     id TEXT PRIMARY KEY,
                     user_id TEXT,
                     reason TEXT,
                     timestamp TEXT,
                     added_by TEXT,
                     action TEXT
                     )''')
        c.execute('''CREATE TABLE IF NOT EXISTS reaction_roles (
                     message_id TEXT,
                     role_id TEXT,
                     emoji TEXT,
                     PRIMARY KEY (message_id, role_id, emoji)
                     )''')
        c.execute('''CREATE TABLE IF NOT EXISTS categories (
                     category_id TEXT PRIMARY KEY,
                     name TEXT
                     )''')
        c.execute('''CREATE TABLE IF NOT EXISTS welcome_roles (
                     role_id TEXT PRIMARY KEY
                     )''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
                     key TEXT PRIMARY KEY,
                     value TEXT
                     )''')
        # Initialize default settings if not present
        default_settings = [
            ('welcome_channel_id', ''),
            ('squad_channel_id', ''),
            ('highlights_channel_id', ''),
            ('log_channel_id', ''),
            ('support_user_id', '')
        ]
        c.executemany("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", default_settings)
        conn.commit()
        conn.close()
        print("Database tables created.")

    async def on_ready(self):
        print(f"Bot is ready as {self.user}")
        guild = self.get_guild(int(GUILD_ID))
        if guild:
            print(f"Connected to guild: {guild.name} ({guild.id})")
        else:
            print(f"Guild with ID {GUILD_ID} not found.")
        self.registered_commands = [command.name for command in self.commands]
        print(f"Registered commands: {self.registered_commands}")

        # Restore bot status and activity from settings
        conn = sqlite3.connect('dmzcord.db')
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = 'bot_status'")
        status_row = c.fetchone()
        c.execute("SELECT value FROM settings WHERE key = 'bot_activity_type'")
        activity_type_row = c.fetchone()
        c.execute("SELECT value FROM settings WHERE key = 'bot_activity'")
        activity_row = c.fetchone()
        conn.close()

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

        status = status_row[0] if status_row else "online"
        activity_type = activity_type_row[0] if activity_type_row else "playing"
        activity = activity_row[0] if activity_row else None

        discord_status = status_map.get(status, discord.Status.online)
        discord_activity_type = activity_type_map.get(activity_type, discord.ActivityType.playing)
        activity_obj = None
        if activity:
            if activity_type == "streaming":
                activity_obj = discord.Streaming(name=activity, url="https://twitch.tv/")
            else:
                activity_obj = discord.Activity(type=discord_activity_type, name=activity)
        await self.change_presence(status=discord_status, activity=activity_obj)

    @commands.command(name="audit")
    @commands.has_permissions(administrator=True)
    async def audit(self, ctx):
        """Lists all commands and their required Discord permissions."""
        lines = ["**Available Commands and Requirements:**"]
        for command in self.commands:
            if command.hidden:
                continue
            perms = []
            for check in getattr(command, "checks", []):
                # Check for has_permissions decorator
                if hasattr(check, "__closure__") and check.__closure__:
                    for cell in check.__closure__:
                        value = cell.cell_contents
                        if isinstance(value, dict):
                            for perm, required in value.items():
                                if required:
                                    perms.append(perm.replace('_', ' ').title())
                # Check for is_owner
                if getattr(check, "__qualname__", "").startswith("is_owner"):
                    perms.append("Bot Owner Only")
            # If no perms found, check for admin via cog_check
            if not perms and hasattr(command.cog, "cog_check"):
                perms.append("Administrator (via cog_check)")
            doc = command.help or command.short_doc or "No description provided."
            perms_str = ", ".join(set(perms)) if perms else "None"
            lines.append(f"**!{command.name}**: {doc}\nRequirements: {perms_str}")
        await ctx.send("\n\n".join(lines))

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator

class ModmailCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not GUILD_ID or not MODMAIL_LOG_CHANNEL_ID:
            raise ValueError("GUILD_ID or MODMAIL_LOG_CHANNEL_ID missing in .env")
        self.guild_id = int(GUILD_ID)
        self.modmail_log_channel_id = int(MODMAIL_LOG_CHANNEL_ID)

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator

class ReactionRolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator

class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator

# Initialize bot as MyBot
bot = MyBot(command_prefix='!', intents=intents)

# Run the bot
if __name__ == "__main__":
    if not BOT_TOKEN or not GUILD_ID:
        print("Error: BOT_TOKEN or GUILD_ID not found in .env file.")
    else:
        try:
            bot.run(BOT_TOKEN)
        except KeyboardInterrupt:
            print("Bot shutting down...")
            bot.loop.run_until_complete(bot.close())
        except Exception as e:
            print(f"Error running bot: {e}")
