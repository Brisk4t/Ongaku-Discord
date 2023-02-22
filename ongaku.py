import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
import yt_dlp as youtube_dl
from requests import get

ytdl_opts = {
    'format': 'bestaudio/best', # Audio quality
    'restrictfilenames': True, # Don't allow '&' in filenames
    'nocheckcertificate': True, # Do not use ssl
    'ignoreerrors': False, # Do not stop on download errors
    'logtostderr': False, # Do not log
    'quiet': True, # Do not print messages
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'

}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
     'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_opts) # make ytdl object


# Initialize discord API objects
load_dotenv()
intents = discord.Intents.all()
command_channel = int(os.getenv('COMMAND_CHANNEL'))
testing_channel = int(os.getenv('TESTING_CHANNEL'))
TOKEN = os.getenv('DISCORD_TOKEN') # Get token from .env
bot = commands.Bot(command_prefix="!", intents=intents) # Discord interaction object & load default intents






######################## Classes ########################


def search(query):
    try: get(query)
    except: info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
    else: info = ytdl.extract_info(query, download=False)
    
    return info


class invalidchannel(commands.CheckFailure):
    pass

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        url = search(url)['original_url']
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)



######################## Checks ########################


def check_channel():
    def predicate(ctx):
        if not (ctx.channel.id == command_channel or ctx.channel.id == testing_channel):
            return False
    return commands.check(predicate)

@bot.check
async def checkchannel(ctx):
    if not (ctx.channel.id == command_channel or ctx.channel.id == testing_channel):
            raise invalidchannel("Invalid Channel")
    return True

########################### Event Handlers ###########################

@bot.event
async def on_ready(): # On connect 
    print(f'{bot.user} has connected to discord')
    channel = bot.get_channel(command_channel)
    await channel.send("Ongaku Online.", delete_after=10)



@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, invalidchannel):
        await ctx.send("Please use the Ongaku Commands channel for bot commands.", delete_after=5)

######################## Player Functions ########################

async def search_play(ctx, url):
    if not ctx.message.author.voice:
        await ctx.send("Please connect to a voice channel.")
        return
    
    else:
        await ctx.message.author.voice.channel.connect() # connect to the same channel as author
        voice_channel = ctx.message.guild.voice_client # get the channel

        async with ctx.typing(): # show typing status while this process completes (basically 'loading')
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            voice_channel.play(player)
        
        await ctx.send("Playing: {}".format(player.title))


async def stop_song(ctx):
    if not ctx.message.author.voice:
        await ctx.send("Ongaku is not connected to your voice channel.")
        return
    
    else:
        await ctx.voice_client.disconnect()


async def pause_song(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
    else:
        await ctx.send("Ongaku is not playing anything.")


async def resume_song(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    else:
        await ctx.send("No song to resume.")
    

######################## Command Event Handlers ########################


@bot.command()
async def test(ctx): # if !test is sent
    await ctx.send("Test Success", delete_after=5)
    await ctx.message.delete()


@bot.command() # if !play is sent
async def play(ctx, *, url):
   await search_play(ctx, url)
   await ctx.message.delete()


@bot.command() # if !stop is sent
async def stop(ctx):
    await stop_song(ctx)
    await ctx.message.delete()


@bot.command()
async def pause(ctx):
    await pause_song(ctx)
    await ctx.message.delete()


@bot.command()
async def resume(ctx):
    await resume_song(ctx)
    await ctx.message.delete()




######################## Message Handler ########################
@bot.event
async def on_message(message):
    if (message.author.id != bot.user.id) and not (message.content.startswith('!')) :
        if (message.channel.id == command_channel or message.channel.id == testing_channel):
            ctx = await bot.get_context(message)
            await search_play(ctx, message.content)
            await message.delete()

    await bot.process_commands(message) # prevents on_message from overriding on_command








bot.run(TOKEN)