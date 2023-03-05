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
testing_channel = int(os.getenv('TESTING_CHANNEL'))
TOKEN = os.getenv('DISCORD_TOKEN') # Get token from .env
bot = commands.Bot(command_prefix="!", intents=intents) # Discord interaction object & load default intents




######################## Classes ########################
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

class MusicPlayer():

    def __init__(self):
        self.queue=queue()
    
    async def join(self, ctx):
        if not ctx.message.author.voice: # if the message author is not in a voice channel
            await ctx.message.delete()
            await ctx.send("Please connect to a voice channel.", delete_after=5)
            return
        
        elif not ctx.guild.voice_client in bot.voice_clients: # if the bot is not connected
            await ctx.message.author.voice.channel.connect() # connect to the same channel as author
            
        return



    async def dequeue_and_play(self, ctx):
        if (self.queue.len >= 1):
            source = self.queue.pop()
            voice_channel = ctx.message.guild.voice_client
            voice_channel.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.dequeue_and_play(ctx), bot.loop))
            embed = generate_embed(ctx, self.queue, source)
            await bot.global_embeds[ctx.guild.id].edit(embed=embed)
            


    async def search_play(self, ctx, url):

        await self.join(ctx) # wait to join voice channel
        voice_channel = ctx.message.guild.voice_client # get the channel
        
        view = playbackUI(timeout=None)
        view.ctx = ctx
        view.musicplayer = bot.music_players[ctx.guild.id]
        
        async with ctx.typing(): # show typing status while this process completes (basically 'loading')
           
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True, ctx=ctx) # AudioSource Object

            if voice_channel.is_playing() or voice_channel.is_paused(): # if a song is playing or is paused
                
                self.queue.push(player) # add it to the queue
                print(self.queue.display())
                #await ctx.send("Added {} to queue".format(player.title))
                await bot.global_embeds[ctx.guild.id].edit(embed = generate_embed(ctx, self.queue, player=voice_channel.source), view=view)

            else:
                voice_channel.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(self.dequeue_and_play(ctx), bot.loop))
                #await ctx.send("Playing: {}".format(player.title))
                await bot.global_embeds[ctx.guild.id].edit(embed = generate_embed(ctx, queue=self.queue, player=player), view=view)
        

    async def stop_song(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            await voice_client.stop()
        else:
            await ctx.send("Ongaku is not playing anything.", delete_after=5)


    async def pause_song(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            await voice_client.pause()
        
        elif not voice_client.is_playing and not voice_client.is_paused:
            await ctx.send("Ongaku is not playing anything.", delete_after=5)


    async def resume_song(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_paused():
            await voice_client.resume()
        
        elif not voice_client.is_paused() and not voice_client.is_playing:
            await ctx.send("No song to resume.", delete_after=5)


    async def next_song(self, ctx):
        if self.queue.display():
            await self.stop_song(ctx)
            await self.dequeue_and_play(ctx)
            
        
        else:
            await ctx.send("No next item in queue", delete_after=5)

    async def disconnect_bot(self, ctx):
        print("I am here")
        if not ctx.message.author.voice:
            print("I am here2")
            await ctx.send("Ongaku is not connected to your voice channel.", delete_after=5)
            return
        
        else:
            print("I am here3")
            await ctx.guild.voice_client.disconnect()
            print("Here")


    def search(self, query):
        try: get(query) # try querying for url
        except: info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0] # if query is not url
        else: info = ytdl.extract_info(query, download=False) # if query is url
        
        return info



class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, ctx):
        loop = loop or asyncio.get_event_loop()
       
        try: get(url) # check if the url is valid or is a search query
        except:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{url}", download=not stream)['entries'][0])
        else:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        

        if 'entries' in data: # if there is a list of songs in the data (data is a playlist)

            for item in range(len(data['entries'])): # for every song in the playlist
                if item == 0:
                    data0 = data['entries'][item] # play the first item
                    filename = data0['url'] if stream else ytdl.prepare_filename(data0)
                    player = cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data0) # create the player object

                else:
                    data_queue = (data['entries'][item]) # queue the remaining items
                    filename = data_queue['url'] if stream else ytdl.prepare_filename(data_queue)
                    player_queue = cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data_queue)
                    bot.music_players[ctx.guild.id].queue.push(player_queue)


        else: 
            filename = data['url'] if stream else ytdl.prepare_filename(data)
            player = cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data) # create the player object
        
        return player


class playbackUI(discord.ui.View):
    ctx = None
    musicplayer = None

    @discord.ui.button(label=None, emoji=":play512:1078651539230564362", style=discord.ButtonStyle.success)
    async def playbutton(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.musicplayer.resume_song(self.ctx)
   
    @discord.ui.button(label=None, emoji=":pause256:1078650829227180064",  style=discord.ButtonStyle.danger)
    async def pausebutton(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.musicplayer.pause_song(self.ctx)

    @discord.ui.button(label=None, emoji=":hydra_stop:971015680696672356", style=discord.ButtonStyle.secondary)
    async def stopbutton(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.musicplayer.stop_song(self.ctx)

    @discord.ui.button(label=None, emoji=":hydra_skip:971015680654729216", style=discord.ButtonStyle.secondary)
    async def nextbutton(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.musicplayer.next_song(self.ctx)


class invalidchannel(commands.CheckFailure):
    pass



######################## Checks ########################


# def check_channel():
#     def predicate(ctx):
#         if not (ctx.channel.id == command_channel or ctx.channel.id == testing_channel):
#             return False
#     return commands.check(predicate)


def check_channel():
    def predicate(ctx):
        if not (ctx.channel.id in bot.command_channels):
            return False
    return commands.check(predicate)


@bot.check
async def checkchannel(ctx):
    if not (ctx.channel.id in bot.command_channels or ctx.channel.id == testing_channel):
            raise invalidchannel("Invalid Channel")
    return True


########################### Event Handlers ###########################



async def setup():
    bot.command_channels = []
    bot.global_embeds = {}
    bot.music_players = {}


    for guild in bot.guilds:
        
        bot.command_channels.append((discord.utils.get(guild.channels, name="ongaku-commands")).id)
        bot.music_players[guild.id]= MusicPlayer()

    print(bot.command_channels)

    print(f'{bot.user} has connected to discord')
    

    for item in bot.command_channels:
        channel = bot.get_channel(item)

        #iterator = channel.history(limit = 5, oldest_first=True)
        messages = [msg async for msg in channel.history(limit=100, oldest_first=True)]

        for msg in messages:
            await msg.delete()

        embed = generate_embed() 
        view = playbackUI(timeout=None)
        view.musicplayer=bot.music_players[channel.guild.id]
        view.ctx = channel
        bot.global_embeds[channel.guild.id] = await channel.send(embed=embed, view=view)



@bot.event
async def on_ready(): # On connect 
    await setup()




@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, invalidchannel):
        await ctx.send("Please use the Ongaku Commands channel for bot commands.", delete_after=5)



@bot.event
async def on_message(message):
    if (message.author.id != bot.user.id) and not (message.content.startswith('!')) : # If the message is not sent by the bot and is not a command
        if (message.channel.id in bot.command_channels or message.channel.id == testing_channel): # if the message is sent in the command or testing channel
            ctx = await bot.get_context(message) # Get message
            await bot.music_players[ctx.guild.id].search_play(ctx, message.content)
            await ctx.message.delete()

    await bot.process_commands(message) # prevents on_message from overriding on_command



@bot.command(brief='Responds with a test message', category="Playback")
async def test(ctx): # if !test is sent
    await ctx.message.delete()
    await ctx.send("Test Success", delete_after=5)



@bot.command(brief='Play song from search query or url') # if !play is sent
async def play(ctx, *, url):
   await ctx.message.delete()
   await bot.music_players[ctx.guild.id].search_play(ctx, url)
   


@bot.command(brief='Stop song playback') # if !stop is sent
async def stop(ctx):
    await ctx.message.delete()
    await bot.music_players[ctx.guild.id].stop_song(ctx)
    


@bot.command(brief="Disconnect from voice channel") # if !leave is sent
async def leave(ctx):
    await ctx.message.delete()
    await bot.music_players[ctx.guild.id].disconnect_bot(ctx)
   


@bot.command(brief='Pause song playback')
async def pause(ctx):
    await ctx.message.delete()
    await bot.music_players[ctx.guild.id].pause_song(ctx)
    


@bot.command(brief="Resume playback")
async def resume(ctx):
    await ctx.message.delete()
    await bot.music_players[ctx.guild.id].resume_song(ctx)
    

@bot.command(brief="Next song")
async def next(ctx):
    await ctx.message.delete()
    await bot.music_players[ctx.guild.id].next_song(ctx)


@bot.command(hidden=True)
async def reset(ctx):
    if(ctx.author.id == ctx.guild.owner):
        await ctx.message.delete()
        await setup()
        


######################## Embed ########################

def generate_embed(ctx=None, queue=None, player=None):

    if not player:
        embed = discord.Embed(title="No Song Playing", color=discord.Colour.teal(), description="Queue Empty")



    else:    
        embed = discord.Embed(title=player.title, url=player.data['original_url'], color=discord.Colour.teal(), description="Queue:")
        embed.set_image(url=player.data['thumbnail'])
        embed.set_author(name=("Last Command: {}".format(ctx.message.author)))
        embed.set_footer(text=player.data['duration_string'])

        current_queue = queue.display()

        for i in range(len(current_queue)): # Add queue items as fields
            if i < 24:
                embed.add_field(name=current_queue[i], value="", inline=False)

            elif i==24:
                embed.add_field(name="..........", value="", inline=False)

    return embed



bot.run(TOKEN)