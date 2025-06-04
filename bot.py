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
        
        cog_files = [f[:-3] for f in os.listdir(cog_dir) if f.endswith('.py') and f != '__init__.py']
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
        conn = sqlite3.connect('cheaters.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS cheaters (
                     activision_id TEXT PRIMARY KEY,
                     reason TEXT,
                     timestamp TEXT,
                     added_by TEXT
                     )''')
        # Prepopulate with an example cheater
        example_activision_id = "ExampleCheater#1234567"  # Dummy Activision ID
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

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have the required permissions to use this command.")
        elif isinstance(error, commands.CommandNotFound):
            pass  # Ignore unknown commands
        else:
            await ctx.send(f"An error occurred: {str(error)}")
            raise error

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