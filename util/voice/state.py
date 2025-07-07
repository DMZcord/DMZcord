import asyncio


class GuildMusicState:
    def __init__(self):
        self.queue = []
        self.now_playing = None
        self.voice_client = None
        self.lock = asyncio.Lock()
