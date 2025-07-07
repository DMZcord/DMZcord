import asyncio
from util.core import DatabaseConnection
async def get_current_db_name():
    conn = await DatabaseConnection.get_db_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT DATABASE()")
            row = await cursor.fetchone()
            return row[0] if row else None
    finally:
        conn.close()

async def get_existing_tables():
    conn = await DatabaseConnection.get_db_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute("SHOW TABLES")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    finally:
        conn.close()
        
async def create_tables():
    """
    Create necessary database tables and indexes for MySQL.
    """
    conn = await DatabaseConnection.get_db_connection()
    created_indexes = []
    try:
        async with conn.cursor() as cursor:
            # Suppress warnings for the session
            await cursor.execute("SET sql_notes = 0;")

            # Combined Abuse Table
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS abuse (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    username VARCHAR(100) NOT NULL,
                    guild_id VARCHAR(100) NOT NULL,
                    block_time VARCHAR(50) NOT NULL,
                    block_duration INT NOT NULL,
                    block_until VARCHAR(50) NOT NULL,
                    reason TEXT,
                    block_type VARCHAR(50) DEFAULT 'command',
                    notified BOOLEAN DEFAULT FALSE
                )
            ''')

            # Moderation (combined warns, mutes, bans)
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS moderation (
                    id VARCHAR(100),
                    user_id VARCHAR(100) NOT NULL,
                    discord_username VARCHAR(100),
                    reason TEXT,
                    timestamp VARCHAR(50),
                    added_by VARCHAR(100),
                    guild_id VARCHAR(100),
                    action ENUM('warn', 'mute', 'ban') NOT NULL,
                    duration INT,
                    active BOOLEAN DEFAULT TRUE,
                    quashed BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (id, guild_id)
                )
            ''')

            # Categories
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    category_name VARCHAR(100),
                    role_ids TEXT,
                    guild_id VARCHAR(100),
                    PRIMARY KEY (category_name, guild_id)
                )
            ''')

            # Cheaters
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS cheaters (
                    activision_id VARCHAR(100),
                    reason TEXT,
                    timestamp VARCHAR(50),
                    added_by VARCHAR(100),
                    added_by_id VARCHAR(100),
                    guild_id VARCHAR(100),
                    PRIMARY KEY (activision_id, guild_id)
                )
            ''')

            # Command Logs
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS command_logs (
                    log_id VARCHAR(32) PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    username VARCHAR(100),
                    channel_id VARCHAR(100),
                    channel_name VARCHAR(100) NOT NULL,
                    guild_id VARCHAR(100),
                    command_name VARCHAR(100) NOT NULL,
                    success BOOLEAN,
                    error TEXT,
                    response_time FLOAT,
                    timestamp VARCHAR(50) NOT NULL
                )
            ''')

            # Community Loadouts
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS community_loadouts (
                    username VARCHAR(100),
                    data TEXT,
                    last_updated VARCHAR(50),
                    guild_id VARCHAR(100),
                    PRIMARY KEY (username, guild_id)
                )
            ''')

            # Query Logs
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS query_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    `sql` TEXT,
                    params TEXT,
                    elapsed DOUBLE,
                    created_at VARCHAR(50)
                )
            ''')

            # Reaction Roles
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS reaction_roles (
                    message_id VARCHAR(100),
                    role_id VARCHAR(100),
                    emoji VARCHAR(100),
                    category VARCHAR(100),
                    guild_id VARCHAR(100),
                    PRIMARY KEY (message_id, role_id, emoji, guild_id)
                )
            ''')

            # TicketSettings
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticket_settings (
                    guild_id VARCHAR(100) PRIMARY KEY,
                    ticket_channel VARCHAR(100),
                    message_id VARCHAR(100),
                    log_channel VARCHAR(100)
                )
            ''')

            # User Sync
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sync (
                    discord_id VARCHAR(100) PRIMARY KEY,
                    wzhub_username VARCHAR(100),
                    discord_username VARCHAR(100)
                )
            ''')

            # Welcome Roles
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS welcome_roles (
                    role_id VARCHAR(100),
                    guild_id VARCHAR(100),
                    PRIMARY KEY (role_id, guild_id)
                )
            ''')

            # Blacklist
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS blacklist (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(100),
                    channel_id VARCHAR(100),
                    guild_id VARCHAR(100),
                    added_by VARCHAR(100),
                    added_at VARCHAR(50),
                    duration_seconds INT,
                    expires_at VARCHAR(50),
                    active BOOLEAN DEFAULT TRUE,
                    UNIQUE KEY unique_blacklist (user_id, channel_id, guild_id)
                )
            ''')

            # Logging
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS logging (
                    `key` VARCHAR(100) PRIMARY KEY,
                    `value` VARCHAR(255) DEFAULT 'WARNING',
                    log_channel VARCHAR(100) DEFAULT '1386083199431475250'
                )
            ''')
            
            # Guild settings
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id VARCHAR(100),
                    `key` VARCHAR(100),
                    `value` TEXT,
                    PRIMARY KEY (guild_id, `key`)
                )
            ''')
            
            # Unique Users
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS unique_users (
                    user_id VARCHAR(100) PRIMARY KEY,
                    username VARCHAR(100),
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    guild_id VARCHAR(100),
                    guild_name VARCHAR(100),
                    channel_id VARCHAR(100),
                    channel_name VARCHAR(100)
                )
            ''')

            # Create indexes for all tables (only the requested ones)
            if await create_index_if_not_exists(cursor, 'idx_moderation_user_id_active', 'moderation', 'user_id, active'):
                created_indexes.append('idx_moderation_user_id_active')
            if await create_index_if_not_exists(cursor, 'idx_cheaters_activision_id', 'cheaters', 'activision_id'):
                created_indexes.append('idx_cheaters_activision_id')
            if await create_index_if_not_exists(cursor, 'idx_community_loadouts_username', 'community_loadouts', 'username'):
                created_indexes.append('idx_community_loadouts_username')
            if await create_index_if_not_exists(cursor, 'idx_community_loadouts_guild_id', 'community_loadouts', 'guild_id'):
                created_indexes.append('idx_community_loadouts_guild_id')
            if await create_index_if_not_exists(cursor, 'idx_user_sync_discord_id', 'user_sync', 'discord_id'):
                created_indexes.append('idx_user_sync_discord_id')
            if await create_index_if_not_exists(cursor, 'idx_user_sync_wzhub_username', 'user_sync', 'wzhub_username'):
                created_indexes.append('idx_user_sync_wzhub_username')
            if await create_index_if_not_exists(cursor, 'idx_welcome_roles_role_id', 'welcome_roles', 'role_id'):
                created_indexes.append('idx_welcome_roles_role_id')
            if await create_index_if_not_exists(cursor, 'idx_welcome_roles_guild_id', 'welcome_roles', 'guild_id'):
                created_indexes.append('idx_welcome_roles_guild_id')
            if await create_index_if_not_exists(cursor, 'idx_command_logs_guild_id_timestamp', 'command_logs', 'guild_id, timestamp'):
                created_indexes.append('idx_command_logs_guild_id_timestamp')
            if await create_index_if_not_exists(cursor, 'idx_command_logs_user_id', 'command_logs', 'user_id'):
                created_indexes.append('idx_command_logs_user_id')
            if await create_index_if_not_exists(cursor, 'idx_command_logs_command_name', 'command_logs', 'command_name'):
                created_indexes.append('idx_command_logs_command_name')

        await conn.commit()
    finally:
        conn.close()
    return created_indexes

async def create_index_if_not_exists(cursor, index_name, table_name, columns):
    """
    Check if an index exists and create it if it does not.
    Returns True if created, False if already exists.
    """
    escaped_columns = ", ".join([f"`{col.strip()}`" for col in columns.split(",")])
    await cursor.execute('''
        SELECT COUNT(1)
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
        AND table_name = %s
        AND index_name = %s
    ''', (table_name, index_name))
    index_exists = await cursor.fetchone()

    # If the index does not exist, create it
    if index_exists and index_exists[0] == 0:
        await cursor.execute(f'''
            CREATE INDEX {index_name} ON {table_name} ({escaped_columns})
        ''')
        return True
    return False

async def clear_all_tables():
    """
    Drops all tables in the current database and prints their names.
    """
    conn = await DatabaseConnection.get_db_connection()
    dropped_tables = []
    try:
        async with conn.cursor() as cursor:
            await cursor.execute("SHOW TABLES")
            tables = await cursor.fetchall()
            for row in tables:
                table = row[0]
                await cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
                dropped_tables.append(table)
        await conn.commit()
        if dropped_tables:
            print("🧹 Tables dropped:")
            for t in dropped_tables:
                print(f"  - {t}")
        else:
            print("🧹 No tables to drop.")
    finally:
        conn.close()

async def main():
    print("=" * 50)
    print("🔗 Connecting to database...")
    db_name = await get_current_db_name()
    print(f"📂 Current database: {db_name}")
    print("=" * 50)

    # Clear all tables before initializing
    await clear_all_tables()

    before_tables = await get_existing_tables()
    print("📋 Tables before initialization:")
    if before_tables:
        for t in before_tables:
            print(f"  - {t}")
    else:
        print("  (No tables found)")

    print("=" * 50)
    print("🛠️  Creating tables and indexes")
    created_indexes = await create_tables()
    print("=" * 50)

    after_tables = await get_existing_tables()

    new_tables = [t for t in after_tables if t not in before_tables]
    if new_tables:
        print("✅ New tables created:")
        for t in new_tables:
            print(f"  - {t}")
    else:
        print("ℹ️  No new tables were created.")

    if created_indexes:
        print("=" * 50)
        print("🔑 Indexes created:")
        for idx in created_indexes:
            print(f"  - {idx}")
    else:
        print("=" * 50)
        print("ℹ️  No new indexes were created.")

    print("=" * 50)

    # Insert default logging settings if not exists
    conn = await DatabaseConnection.get_db_connection()  # <-- Add this line
    async with conn.cursor() as cursor:
        await cursor.execute('''
            INSERT IGNORE INTO logging (`key`, `value`, log_channel)
            VALUES ('logging_level', 'INFO', '1386083199431475250')
        ''')
        await conn.commit()
    conn.close()  # <-- Optionally close the connection

if __name__ == "__main__":
    asyncio.run(main())
