import os
import discord
import asyncio
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



# class playbackButtons(discord.ui.Button):
#     def setup(self, data):
#         self.label = data['label']
#         self.custom_id = data['custom_id']
#         self.ctx = data['ctx']

#     async def callback(self, interaction=discord.Interaction):
#         await resume_song(self.ctx)


class playbackUI(discord.ui.View):
    ctx : None

    @discord.ui.button(label=None, emoji=":play512:1078651539230564362", style=discord.ButtonStyle.success)
    async def playbutton(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await resume_song(self.ctx)
   
    @discord.ui.button(label=None, emoji=":pause256:1078650829227180064",  style=discord.ButtonStyle.danger)
    async def pausebutton(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await pause_song(self.ctx)

    @discord.ui.button(label=None, emoji=":hydra_stop:971015680696672356", style=discord.ButtonStyle.secondary)
    async def stopbutton(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await stop_song(self.ctx)

    @discord.ui.button(label=None, emoji=":hydra_skip:971015680654729216", style=discord.ButtonStyle.secondary)
    async def nextbutton(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await next_song(self.ctx)


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


class queue():
    def __init__(self):
        self.song_queue = []
        self.len = 0
    
    def pop(self):
        self.len -= 1
        return self.song_queue.pop(0)
        


    def push(self, player):
        self.len += 1
        self.song_queue.append(player)
        
    def length(self):
        return self.len

    def display(self): # returns a alist of the song titles
        titles = []
        for song in self.song_queue:
            titles.append(song.title) 

        return titles



# class MusicPlayer():

#     def __init__(self):
#         self. 


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

bot.global_embed = None

@bot.event
async def on_ready(): # On connect 
    print(f'{bot.user} has connected to discord')
    channel = bot.get_channel(command_channel)

    #iterator = channel.history(limit = 5, oldest_first=True)
    messages = [msg async for msg in channel.history(limit=100, oldest_first=True)]

    for msg in messages:
        await msg.delete()

    embed = generate_embed() 
    view = playbackUI()
    view.ctx = channel
    bot.global_embed = await channel.send(embed=embed, view=view)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, invalidchannel):
        await ctx.send("Please use the Ongaku Commands channel for bot commands.", delete_after=5)

######################## Player Functions ########################

q = queue() # instantiate a queue

async def join(ctx):
    if not ctx.message.author.voice: # if the message author is not in a voice channel
        await ctx.message.delete()
        await ctx.send("Please connect to a voice channel.", delete_after=5)
        return
    
    elif not ctx.guild.voice_client in bot.voice_clients: # if the bot is not connected
        await ctx.message.author.voice.channel.connect() # connect to the same channel as author
        
    return



async def get_song(ctx, url):
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True) # AudioSource Object
        return player    
        

async def dequeue_and_play(ctx):
    if (q.len >= 1):
        source = q.pop()
        voice_channel = ctx.message.guild.voice_client
        voice_channel.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(dequeue_and_play(ctx), bot.loop))
        embed = generate_embed(ctx, q, source)
        await bot.global_embed.edit(embed=embed)
        


async def search_play(ctx, url):

    await join(ctx) # wait to join voice channel
    voice_channel = ctx.message.guild.voice_client # get the channel
    
    view = playbackUI()
    view.ctx = ctx
    
    async with ctx.typing(): # show typing status while this process completes (basically 'loading')
        player = await get_song(ctx, url)

        if voice_channel.is_playing(): # if a song is playing 
            q.push(player) # add it to the queue
            print(q.display())
            #await ctx.send("Added {} to queue".format(player.title))
            view = playbackUI()
            view.ctx = ctx
            await bot.global_embed.edit(embed = generate_embed(ctx, q, player=voice_channel.source), view=view)

        else:
            voice_channel.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(dequeue_and_play(ctx), bot.loop))
            #await ctx.send("Playing: {}".format(player.title))
            view = playbackUI()
            view.ctx = ctx
            await bot.global_embed.edit(embed = generate_embed(ctx, queue=q, player=player), view=view)
    

async def stop_song(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.stop()
    else:
        await ctx.send("Ongaku is not playing anything.", delete_after=5)


async def pause_song(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
    
    elif not voice_client.is_playing and not voice_client.is_paused:
        await ctx.send("Ongaku is not playing anything.", delete_after=5)


async def resume_song(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    
    elif not voice_client.is_paused() and not voice_client.is_playing:
        await ctx.send("No song to resume.", delete_after=5)


async def next_song(ctx):
    if q.display():
        await stop_song(ctx)
        await dequeue_and_play(ctx)
        
    
    else:
        await ctx.send("No next item in queue", delete_after=5)


# async def seek(ctx, time):
    
    

async def disconnect_bot(ctx):
    if not ctx.message.author.voice:
        await ctx.send("Ongaku is not connected to your voice channel.", delete_after=5)
        return
    
    else:
        await ctx.voice_client.disconnect()

######################## Command Event Handlers ########################


@bot.command()
async def test(ctx): # if !test is sent
    await ctx.message.delete()
    await ctx.send("Test Success", delete_after=5)



@bot.command() # if !play is sent
async def play(ctx, *, url):
   await ctx.message.delete()
   await search_play(ctx, url)
   


@bot.command() # if !stop is sent
async def stop(ctx):
    await ctx.message.delete()
    await stop_song(ctx)
    


@bot.command() # if !stop is sent
async def leave(ctx):
    await ctx.message.delete()
    await disconnect_bot(ctx)
    


@bot.command()
async def pause(ctx):
    await ctx.message.delete()
    await pause_song(ctx)
    


@bot.command()
async def resume(ctx):
    await ctx.message.delete()
    await resume_song(ctx)
    

@bot.command()
async def next(ctx):
    await ctx.message.delete()
    await next_song(ctx)

######################## Embed ########################

def generate_embed(ctx=None, queue=q, player=None):

    if not player:
        embed = discord.Embed(title="No Song Playing", color=discord.Colour.teal(), description="Queue Empty")



    else:    
        embed = discord.Embed(title=player.title, url=player.data['original_url'], color=discord.Colour.teal(), description="Queue:")
        embed.set_image(url=player.data['thumbnail'])
        embed.set_author(name=ctx.message.author)
        embed.set_footer(text=player.data['duration_string'])

        current_queue = queue.display()

        for i in range(len(current_queue)): # Add queue items as fields
            if i < 25:
                embed.add_field(name=current_queue[i], value="", inline=False)

            elif i==25:
                embed.add_field(name="..........", value="", inline=False)

    return embed


######################## Message Handler ########################


@bot.event
async def on_message(message):
    if (message.author.id != bot.user.id) and not (message.content.startswith('!')) :
        if (message.channel.id == command_channel or message.channel.id == testing_channel):
            ctx = await bot.get_context(message)
            await search_play(ctx, message.content)
            await ctx.message.delete()

    await bot.process_commands(message) # prevents on_message from overriding on_command








bot.run(TOKEN)