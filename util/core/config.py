import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class BotConfig:
    token: str
    guild_id: Optional[int] = None
    log_channel_id: Optional[int] = None
    
    @classmethod
    def from_env(cls):
        return cls(
            token=os.getenv('BOT_TOKEN'),
            guild_id=int(os.getenv('GUILD_ID')) if os.getenv('GUILD_ID') else None,
            log_channel_id=int(os.getenv('LOG_CHANNEL_ID')) if os.getenv('LOG_CHANNEL_ID') else None
        )