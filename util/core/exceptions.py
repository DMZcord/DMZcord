# ===== BASE EXCEPTION =====

class DMZcordException(Exception):
    """Base exception for DMZcord bot."""
    pass

# ===== INFRASTRUCTURE ERRORS =====

class DatabaseError(DMZcordException):
    """Database operation failed."""
    pass

class ConfigurationError(DMZcordException):
    """Configuration error."""
    pass

class APIError(DMZcordException):
    """External API error (WZHub, etc.)."""
    def __init__(self, api_name, status_code=None, message=None):
        self.api_name = api_name
        self.status_code = status_code
        super().__init__(f"{api_name} API error" + 
                        (f" (status {status_code})" if status_code else "") +
                        (f": {message}" if message else ""))

# ===== DISCORD RESOURCE ERRORS =====

class DiscordPermissionError(DMZcordException):
    """Bot lacks required Discord permissions."""
    def __init__(self, action, channel=None, guild=None):
        self.action = action
        self.channel = channel
        self.guild = guild
        super().__init__(f"Missing permissions to {action}" + 
                        (f" in {channel}" if channel else "") +
                        (f" in guild {guild}" if guild else ""))

class UserNotFoundError(DMZcordException):
    """User not found in Discord or database."""
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(f"User {user_id} not found")

class GuildNotFoundError(DMZcordException):
    """Guild not found."""
    def __init__(self, guild_id):
        self.guild_id = guild_id
        super().__init__(f"Guild {guild_id} not found")

class ChannelNotFoundError(DMZcordException):
    """Channel not found."""
    def __init__(self, channel_id):
        self.channel_id = channel_id
        super().__init__(f"Channel {channel_id} not found")

# ===== FEATURE-SPECIFIC ERRORS =====

class ModerationError(DMZcordException):
    """Error during moderation action."""
    pass

class LoadoutError(DMZcordException):
    """Error with loadout operations."""
    pass

# ===== ACCESS CONTROL ERRORS =====

class BlacklistError(DMZcordException):
    """Error with blacklist operations."""
    pass

class UserBlacklistedError(DMZcordException):
    """User is blacklisted."""
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(f"User {user_id} is blacklisted")

class ChannelBlacklistedError(DMZcordException):
    """Channel is blacklisted."""
    def __init__(self, channel_id):
        self.channel_id = channel_id
        super().__init__(f"Channel {channel_id} is blacklisted")

# ===== VALIDATION & RATE LIMITING ERRORS =====

class ValidationError(DMZcordException):
    """Data validation error."""
    def __init__(self, field, value, expected=None):
        self.field = field
        self.value = value
        self.expected = expected
        super().__init__(f"Invalid {field}: {value}" + 
                        (f" (expected {expected})" if expected else ""))

class CommandCooldownError(DMZcordException):
    """Command is on cooldown."""
    def __init__(self, command_name, retry_after):
        self.command_name = command_name
        self.retry_after = retry_after
        super().__init__(f"Command '{command_name}' is on cooldown. Try again in {retry_after:.1f}s")

class NotBotOwnerError(DMZcordException):
    """Raised when a non-owner tries to use an owner-only command."""
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(f"User {user_id} is not the bot owner")