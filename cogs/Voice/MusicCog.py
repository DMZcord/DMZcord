import discord
from discord.ext import commands
import asyncio
from util.voice.download import MusicDownloader
from util.voice.playback import MusicPlayback
from util.voice.validation import MusicValidation
from util.voice.state import GuildMusicState

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_states = {}  # guild_id: GuildMusicState

    def get_guild_state(self, guild_id):
        if guild_id not in self.guild_states:
            self.guild_states[guild_id] = GuildMusicState()
        return self.guild_states[guild_id]

    @commands.hybrid_command(name="join", description="Join your current voice channel.")
    async def join(self, ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        if ctx.interaction:
            await ctx.interaction.response.defer()

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("You are not in a voice channel.")
            return

        state = self.get_guild_state(ctx.guild.id)
        if state.voice_client and state.voice_client.is_connected():
            await ctx.send("I'm already connected to a voice channel.")
            return

        vc = await ctx.author.voice.channel.connect()
        state.voice_client = vc
        await ctx.send("Joined!")

    @commands.hybrid_command(name="play", description="Play a YouTube link in your voice channel.")
    async def play(self, ctx, url: str):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        if ctx.interaction:
            await ctx.interaction.response.defer()

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("You must be in a voice channel to use this command.")
            return

        state = self.get_guild_state(ctx.guild.id)
        if not state.voice_client or not state.voice_client.is_connected():
            await ctx.invoke(self.join)
            state = self.get_guild_state(ctx.guild.id)
        vc = state.voice_client

        if not MusicValidation.is_youtube_url(url):
            await ctx.send("That does not look like a valid YouTube link. Please provide a valid YouTube URL.")
            return

        # Download and queue
        await ctx.send("Downloading and processing...")
        outtmpl = f"temp/{ctx.guild.id}_%(id)s.%(ext)s"
        try:
            info, filename = await MusicDownloader.download_youtube(url, outtmpl)
        except Exception as e:
            await ctx.send(f"Error downloading: {e}")
            return
        info['queued_by'] = str(ctx.author)
        state.queue.append((info, filename))
        await ctx.send(f"Queued: {info.get('title', 'Unknown Title')}")

        # If nothing is playing, start playback
        if not vc.is_playing() and not vc.is_paused():
            await self._play_next(ctx, state)

    async def _play_next(self, ctx, state):
        if not state.queue:
            await ctx.send("Queue is empty.")
            return
        info, filename = state.queue.pop(0)
        state.now_playing = info
        vc = state.voice_client
        def after_playing(error):
            fut = self._play_next(ctx, state)
            asyncio.run_coroutine_threadsafe(fut, self.bot.loop)
        vc.play(discord.FFmpegPCMAudio(source=filename), after=after_playing)
        await ctx.send(f"Now playing: {info.get('title', 'Unknown Title')} (queued by {info.get('queued_by', 'Unknown')})")

    @commands.hybrid_command(name="queue", description="Show the current music queue.")
    async def queue(self, ctx):
        state = self.get_guild_state(ctx.guild.id)
        if not state.queue:
            await ctx.send("The queue is empty.")
            return
        msg = "\n".join([
            f"{i+1}. {info.get('title', 'Unknown Title')} (queued by {info.get('queued_by', 'Unknown')})"
            for i, (info, _) in enumerate(state.queue)
        ])
        await ctx.send(msg)

    @commands.hybrid_command(name="stop", description="Stop music and disconnect from the voice channel.")
    async def stop(self, ctx):
        state = self.get_guild_state(ctx.guild.id)
        if state.voice_client and state.voice_client.is_connected():
            await state.voice_client.disconnect()
            state.voice_client = None
            state.queue.clear()
            await ctx.send("Disconnected and cleared the queue.")
        else:
            await ctx.send("I'm not in a voice channel.")

    @commands.hybrid_command(name="skip", description="Vote to skip the current song.")
    async def skip(self, ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        if ctx.interaction:
            await ctx.interaction.response.defer()

        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            await ctx.send("I'm not playing anything to skip.")
            return

        # If user has manage_guild or manage_messages, skip immediately
        perms = ctx.author.guild_permissions
        if perms.manage_guild or perms.manage_messages:
            vc.stop()
            await ctx.send("Song skipped by a moderator.")
            return

        # Only allow users in the same voice channel to vote
        if not ctx.author.voice or ctx.author.voice.channel != vc.channel:
            await ctx.send("You must be in the same voice channel as me to vote to skip.")
            return

        # Register the vote
        guild_id = ctx.guild.id
        votes_set = self.state.get_skip_votes(guild_id)
        votes_set.add(ctx.author.id)

        members = [m for m in vc.channel.members if not m.bot]
        votes = len(votes_set)
        needed = max(1, len(members) // 2 + (len(members) % 2 > 0))

        await ctx.send(f"{votes}/{needed} votes to skip.")

        if votes >= needed:
            vc.stop()
            await ctx.send("Vote passed! Skipping song.")

    @commands.hybrid_command(name="priority", description="Move a song in the queue to the top and skip the current song (mod only).")
    async def priority(self, ctx, number: int = None):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        if ctx.interaction:
            await ctx.interaction.response.defer()

        # Only allow server owner or users with manage_guild or manage_messages
        perms = ctx.author.guild_permissions
        if not (ctx.author == ctx.guild.owner or perms.manage_guild or perms.manage_messages):
            await ctx.send("Only moderators or the server owner can use this command.")
            return

        queue = self.state.get_queue(ctx.guild.id)
        if not queue:
            await ctx.send("The queue is empty.")
            return

        if number is None or number < 2 or number > len(queue):
            await ctx.send(f"Please specify a valid song number between 2 and {len(queue)}.")
            return

        index = number - 1
        song = queue.pop(index)
        queue.insert(0, song)

        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.stop()

    @play.error
    async def play_error(self, ctx, error):
        await MusicPlayback.play_error(ctx, error)

    @commands.hybrid_command(name="join", description="Join your current voice channel.")
    async def join(self, ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        if ctx.interaction:
            await ctx.interaction.response.defer()

        # Check if user is in a voice channel
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("You are not in a voice channel.")
            return

        # Check if bot is already connected to a voice channel in this guild
        if ctx.voice_client and ctx.voice_client.is_connected():
            await ctx.send("I'm already connected to a voice channel.")
            return

        # Connect to the user's voice channel
        await ctx.author.voice.channel.connect()
        await ctx.send("Joined!")

async def setup(bot):
    await bot.add_cog(MusicCog(bot))