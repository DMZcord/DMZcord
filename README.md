# DMZcord

A powerful Discord bot for Call of Duty: DMZ communities, featuring loadout management, weapon statistics, and community tools.

🔗 **[Join DMZcord](https://discord.gg/CHUynnZdae)** 

---

## ✨ Features

### 🔫 Loadout Management
- **Save & Share**: Create and share weapon loadouts with your community
- **Sync Integration**: Connect with Wzhub.gg for seamless loadout syncing
- **Smart Caching**: Fast loadout retrieval and display
- **Visual Formatting**: Clean, readable loadout displays with emojis

### 🛠️ Utility Commands
- **Help System**: Interactive help with categorized commands
- **Sync Tools**: Member synchronization and username management
- **Moderation**: Welcome messages, modmail system, and user management
- **Admin Tools**: Comprehensive logging, blacklist management, and debugging

### 📊 Community Features
- **Server Management**: Automated welcome messages and member tracking
- **Data Analytics**: Command usage statistics and audit logs
- **Customization**: Server-specific settings and configurations

---

## 🚀 Quick Start

### Adding the Bot
1. **Invite DMZcord** to your server using our invite link
2. **Set permissions** for the channels you want the bot to access
3. **Run `/help`** to see all available commands

### Basic Commands
- `/help` - Interactive help system with all commands
- `/sync <username>` - Sync your Wzhub.gg username
- `/loadout <search>` - Search and display weapon loadouts

---

## 📋 Terms of Service

By using DMZcord, you agree to our [Terms of Service](TERMS.md). Key points:

- **Age Requirement**: Users must be 18+ to use Wzhub.gg integration features
- **Data Privacy**: We securely store only necessary data for bot functionality
- **Fair Use**: Respect third-party services and their terms of service
- **Open Source**: Code is available on GitHub under MIT License

**[📜 Read Full Terms](TERMS.md)**

---

## 🏗️ Project Structure

```
DMZcord/
├── 📄 Configuration Files
│   ├── .env                  # Environment variables
│   ├── .gitignore            # Git ignore rules
│   ├── requirements.txt      # Python dependencies
│   ├── LICENSE.txt           # MIT License
│   └── TERMS.md              # Terms of Service
├── 🤖 Bot Core
│   ├── bot_main.py           # Main bot entry point
│   ├── bot_events.py         # Global event handlers
│   ├── bot_tasks.py          # Background tasks
│   └── init_db.py            # Database initialization
├── 🧩 Commands (cogs/)
│   ├── Community/            # Community features
│   ├── General/              # General commands
│   │   ├── HelpCog.py        # Interactive help system
│   │   ├── SyncCog.py        # Username synchronization
│   │   ├── UtilCog.py        # Utility commands
│   │   └── CheaterCog.py     # Anti-cheat tools
│   ├── Moderation/           # Moderation tools
│   │   ├── ModmailCog.py     # Modmail system
│   │   └── WelcomeCog.py     # Welcome messages
│   └── Owner/                # Owner-only commands
│       ├── AuditCog.py       # Command audit logs
│       ├── BlacklistCog.py   # User blacklist
│       ├── DebugCog.py       # Debug information
│       └── LoggingCog.py     # Logging management
└── 🛠️ Utilities (util/)
    ├── community/            # Community features
    ├── core/                 # Core bot utilities
    ├── general/              # General helpers
    ├── moderation/           # Moderation tools
    ├── owner/                # Owner utilities
    ├── setup/                # Setup helpers
    └── voice/                # Voice features
```

---

## 🔧 Development Setup

### Prerequisites
- **Python 3.8+**
- **MySQL/MariaDB** database
- **Discord Bot Token**

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/DMZcord/DMZcord.git
   cd DMZcord
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   Create a `.env` file in the project root:
   ```env
   BOT_TOKEN=your_discord_bot_token
   
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=dmzcord
   DB_USER=dmzcord_user
   DB_PASSWORD=your_db_password
   
   GIT_COMMIT=your_commit_hash
   ```

4. **Initialize the database:**
   ```bash
   python init_db.py
   ```

5. **Run the bot:**
   ```bash
   python bot_main.py
   ```

---

## 📁 Utility Modules

### `util/community/`
- `cache.py` — Loadout caching system
- `constants.py` — Game constants and emojis
- `data.py` — Weapon and attachment data
- `formatter.py` — Loadout display formatting
- `lookup.py` — Attachment lookup utilities
- `models.py` — Data models and structures
- `queries.py` — Database queries
- `repository.py` — Data access layer
- `sync.py` — Member synchronization
- `types.py` — Type definitions

### `util/core/`
- `commandlogger.py` — Command logging and statistics
- `config.py` — Bot configuration management
- `constants.py` — Core constants (timezones, etc.)
- `database.py` — Database utilities and connections
- `exceptions.py` — Custom exception classes
- `logger.py` — Logging setup and Discord handlers
- `pagination.py` — Message pagination utilities
- `startup.py` — Bot startup procedures
- `utils.py` — General utility functions

### `util/general/`
- `buttons.py` — UI buttons and interactive elements
- `embeds.py` — Help system and embed formatting
- `helpers.py` — General helper functions
- `views.py` — Discord UI views and menus

### `util/moderation/`
- `embeds.py` — Moderation embed formatting
- `events.py` — Moderation event handlers
- `queries.py` — Moderation database queries
- `utils.py` — Moderation helper functions
- `views.py` — Moderation UI components

### `util/owner/`
- `blacklist.py` — Blacklist management utilities
- `embeds.py` — Owner/debug embed formatting
- `helpers.py` — Owner command helpers

### `util/setup/` & `util/voice/`
- Setup utilities and voice/music features
- Cache management and audio processing

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Follow the existing code style** and structure
4. **Test your changes** thoroughly
5. **Submit a pull request** with a clear description

### Development Guidelines
- **Modular design**: Keep features in appropriate cogs and utilities
- **Error handling**: Use proper exception handling and logging
- **Documentation**: Comment complex logic and update README when needed
- **Database**: Use the existing database utilities and patterns

---

## 📜 License & Legal

### MIT License
This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.

### Third-Party Content
⚠️ **Important Disclaimers:**

- **Not affiliated** with Activision, Infinity Ward, or Wzhub.gg
- **Fair use**: Fetches public Call of Duty weapon stats for convenience
- **No republishing**: Does not store or redistribute third-party data
- **Compliance**: Respects all third-party terms of service

This bot relies on publicly viewable content from third-party sources. If you represent a rights holder and would like us to stop referencing your content, please contact us.

---

## 📞 Support & Community

### Get Help
- 🎮 **[Join DMZcord Community](https://discord.gg/CHUynnZdae)** - Get support and connect with users
- 🐞 **[Report Issues](https://github.com/DMZcord/DMZcord/issues)** - Found a bug? Let us know!
- 📖 **[Documentation](https://github.com/DMZcord/DMZcord)** - View all commands and features

### Community Guidelines
- Be respectful and helpful to other users
- Follow Discord's Terms of Service
- Don't spam or abuse bot features
- Report any issues or concerns to moderators

---

**Built with ❤️ for the Call of Duty: DMZ community**


