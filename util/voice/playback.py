import discord
import datetime

class MusicPlayback:
    @staticmethod
    async def play_audio(vc, info, filename, ctx):
        vc.play(discord.FFmpegPCMAudio(source=filename))
        duration = info.get('duration')
        duration_str = f"{int(duration//60)}:{int(duration%60):02d}" if duration else "Unknown"
        await ctx.send(f"Now playing: {info.get('title', 'Unknown Title')} ({duration_str}) (queued by {info.get('queued_by', 'Unknown')})")