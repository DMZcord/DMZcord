import os
import aiomysql
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import asyncio
import time
import logging
from util.core.utils import SizeUtils
import discord
import datetime

load_dotenv()

logger = logging.getLogger(__name__)

class LoggingCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    async def execute(self, sql, params=None):
        params = params or ()
        start = time.perf_counter()
        result = await self.cursor.execute(sql, params)
        elapsed = time.perf_counter() - start
        await self._log_query(sql, params, elapsed)
        return result

    async def executemany(self, sql, seq_of_params):
        start = time.perf_counter()
        result = await self.cursor.executemany(sql, seq_of_params)
        elapsed = time.perf_counter() - start
        await self._log_query(sql, list(seq_of_params), elapsed)
        return result

    def __getattr__(self, name):
        return getattr(self.cursor, name)

    async def _log_query(self, sql, params, elapsed):
        # Avoid recursive logging if you log to the same DB
        if "query_logs" in sql:
            return
        try:
            # logger.info(f"SQL: {sql} | Params: {params} | Elapsed: {elapsed:.4f}s") -- OPTIONAL SQL Logging
            conn = await DatabaseConnection.get_db_connection()
            try:
                async with conn.cursor() as log_cursor:
                    await log_cursor.execute(
                        "INSERT INTO query_logs (`sql`, params, elapsed, created_at) VALUES (%s, %s, %s, NOW())",
                        (str(sql), str(params), float(elapsed))
                    )
                    await conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Failed to log query: {e}", exc_info=True)

class DatabaseConnection:
    # Database configuration as class attributes
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_NAME = os.getenv("DB_NAME", "dmzcord")
    DB_USER = os.getenv("DB_USER", "dmzcord_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")

    @classmethod
    async def get_db_connection(cls):
        """Establish a connection to the MySQL database."""
        return await aiomysql.connect(
            host=cls.DB_HOST,
            port=cls.DB_PORT,
            user=cls.DB_USER,
            password=cls.DB_PASSWORD,
            db=cls.DB_NAME,
            autocommit=True,
        )

    @classmethod
    @asynccontextmanager
    async def db_cursor(cls):
        """
        Provides a context manager for interacting with the MySQL database.
        Automatically handles connection and cursor cleanup.
        """
        conn = await cls.get_db_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as c:
                yield LoggingCursor(c)
        finally:
            conn.close()

class Database:
    @staticmethod
    async def execute(query, *args):
        """Execute a query that modifies the database (INSERT, UPDATE, DELETE)."""
        conn = await DatabaseConnection.get_db_connection()
        try:
            async with conn.cursor() as real_cursor:
                cursor = LoggingCursor(real_cursor)
                await cursor.execute(query, args)
                await conn.commit()
        finally:
            conn.close()

    @staticmethod
    async def fetch(query, *args):
        """Fetch multiple rows from the database."""
        conn = await DatabaseConnection.get_db_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as real_cursor:
                cursor = LoggingCursor(real_cursor)
                await cursor.execute(query, args)
                return await cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    async def fetchrow(query, *args):
        """Fetch a single row from the database."""
        conn = await DatabaseConnection.get_db_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as real_cursor:
                cursor = LoggingCursor(real_cursor)
                await cursor.execute(query, args)
                return await cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    async def vacuum_report():
        """
        Optimizes all tables in the MySQL database using OPTIMIZE TABLE.
        Returns a string with the size before and after optimization.
        """
        conn = await DatabaseConnection.get_db_connection()
        try:
            async with conn.cursor() as real_cursor:
                cursor = LoggingCursor(real_cursor)
                # Get total size before
                await cursor.execute("""
                    SELECT SUM(data_length + index_length)
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                """)
                before_size = await cursor.fetchone()
                before_size = before_size[0] if before_size and before_size[0] is not None else 0

                await cursor.execute("SHOW TABLES;")
                tables = await cursor.fetchall()
                if not tables:
                    return "No tables found in the database to optimize."

                optimized_tables = []
                for (table_name,) in tables:
                    await cursor.execute(f"OPTIMIZE TABLE `{table_name}`;")
                    result = await cursor.fetchall()
                    msg = result[0][3] if len(result[0]) > 3 else str(result[0])
                    optimized_tables.append(f"{table_name}: {msg}")

                # Get total size after
                await cursor.execute("""
                    SELECT SUM(data_length + index_length)
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                """)
                after_size = await cursor.fetchone()
                after_size = after_size[0] if after_size and after_size[0] is not None else 0

                return f"✅ Database VACUUM completed automatically. Size change: {SizeUtils.format_size(before_size)} -> {SizeUtils.format_size(after_size)}"
        except Exception as e:
            return f"❌ Vacuum operation failed: {e}"
        finally:
            conn.close()
    
    @staticmethod
    async def get_mysql_db_size(db_name=None):
        """
        Returns the size of the MySQL database in MB.
        If db_name is None, uses the default from DatabaseConnection.
        """
        if db_name is None:
            db_name = DatabaseConnection.DB_NAME
        conn = await DatabaseConnection.get_db_connection()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT
                        table_schema AS 'DB Name',
                        ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    GROUP BY table_schema
                    """,
                    (db_name,)
                )
                row = await cur.fetchone()
                if row:
                    return float(row[1])
                return 0.0
        finally:
            conn.close()

class UniqueUser:
    @staticmethod
    async def check_unique_user(ctx):
        user_id = str(ctx.author.id)
        username = str(ctx.author)
        guild_id = str(ctx.guild.id) if ctx.guild else None
        guild_name = ctx.guild.name if ctx.guild else None
        channel_id = str(ctx.channel.id) if hasattr(ctx.channel, "id") else None
        channel_name = ctx.channel.name if hasattr(ctx.channel, "name") else "DM"

        tos_embed = discord.Embed(
            title="📜 DMZcord Terms of Service",
            description=(
                "Hi there! 👋\n"
                "By using this bot, you agree to the following:\n\n"
                "**__No Abuse Or Automation__**\n"
                "Do not use this bot for spam, scraping, or mass automation\n\n"
                "**__Loadout Data Storage__**\n"
                "Your loadout data may be stored for bot features only\n"
                "This data is never sold, shared, or used externally\n\n"
                "**__No Affiliation__**\n"
                "This bot is not affiliated with any 3rd parties such as:\n"
                "Activision, Infinity Ward, or Wzhub.gg\n\n"
                "**__Third-Party Terms__**\n"
                "This bot fetches public info from 3rd party sources\n"
                "By using this bot you agree not to violate those parties' TOS\n"
                "📎 [Wzhub TOS](https://wzhub.gg/terms)\n\n"
                "📎 [DMZcord TOS](https://github.com/DMZcord/DMZcord/blob/main/TERMS.md) "
                "🐞 [Report a Bug](https://github.com/DMZcord/DMZcord/issues) "
                "💬 [Support Server](https://discord.gg/CHUynnZdae)"
            ),
            color=discord.Color.green()
        )
        
        tos_embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/1377733230857551956/1388226989755990016/bbd0afbc-b752-40d3-88bd-37f5cf79eb72.png?ex=686c1422&is=686ac2a2&hm=2fb65b0be409d6d4149efea50aaa1393b5cdaf5d33d35ae6a3579834ae63d150&")
        tos_embed.set_footer(
            text="🚨 Violating the TOS may result in a DMZcord ban")
        tos_embed.timestamp = datetime.datetime.now(datetime.timezone.utc)

        async with ctx.bot.db.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT user_id FROM unique_users WHERE user_id = %s",
                    (user_id,)
                )
                exists = await cursor.fetchone()
                if not exists:
                    await cursor.execute(
                        '''
                        INSERT INTO unique_users (user_id, username, guild_id, guild_name, channel_id, channel_name)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ''',
                        (user_id, username, guild_id, guild_name, channel_id, channel_name)
                    )
                    await conn.commit()
                    # Try to DM the user with the embed
                    try:
                        await ctx.author.send(embed=tos_embed)
                    except Exception:
                        await ctx.send(f"{ctx.author.mention}", embed=tos_embed, delete_after=60)
