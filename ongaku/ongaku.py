import os
import discord
import asyncio
from dotenv import load_dotenv
from discord.ext import commands
import yt_dlp as youtube_dl
from requests import get
from collections import deque
import random

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
command_prefix = os.getenv('COMMAND_PREFIX_DEV')
TOKEN = os.getenv('DEV_TOKEN') # Get token from .env
bot = commands.Bot(command_prefix=command_prefix, intents=intents) # Discord interaction object & load default intents




######################## Classes ########################
class queue():
    def __init__(self):
        self.song_queue = deque()
        self.len = 0
    
    def pop(self, index=0):
        if self.len >= 1:
            self.len -= 1
            
            if index != 0:
                item = self.song_queue[index]
                del self.song_queue[index]
                self.song_queue.appendleft(item)

            else:
                return self.song_queue.popleft()
        
        else:
            raise IndexError()

    def pushnext(self, player):
        self.len += 1
        self.song_queue.appendleft(player)

    def push(self, player):
        self.len += 1
        self.song_queue.append(player)
        
    def length(self):
        return self.len

    def clear(self):
        self.len = 0
        self.song_queue.clear()
        return

    # def shuffle_v2(self):
    #     """
    #     Implements v2.1 but generalizes the probability of reshuffling.
    #     :param (dict) playlist: Dictionary of track information, including the track data.
    #     :return (list): Permutation of tracks to shuffle through.
    #     """
    #     track_permutation = []
    #     new_queue = deque()

    #     current_position = 1
    #     queue_length = self.len


    #     if queue_length in [0, 1]:
    #       return self.song_queue

    #     while len(track_permutation) < queue_length:
    #         print("track_permutations", track_permutation)
    #         shuffle_position = random.randint(0, queue_length - 1) # generate a poistion index x where 0 < x < len
    #         print("Shuffle_position 1:", shuffle_position)
    #         delta_position = abs(shuffle_position - current_position) # get distance between items before and after shuffle
    #         print("Delta", delta_position)
    #         print(shuffle_position not in track_permutation)
    #         if not (shuffle_position in track_permutation):
    #             randomfloat = random.random()
    #             print((1 / delta_position+1))
    #             print("Randomfloat:", randomfloat)
    #             if ((queue_length > 2) and randomfloat < (float(1 / delta_position+1))) :
    #                 shuffle_position = random.randint(0, queue_length - 1)
    #                 print("Shuffle_position :", shuffle_position)
    #             track_permutation.append(shuffle_position)

    #     print("Track Permutation:", track_permutation)

    #     for index in track_permutation:
    #         new_queue.append(self.song_queue[index])

    #     print("New Queue:", new_queue)
    #     self.song_queue = new_queue

    #     return

    def display(self): # returns a alist of the song titles
        titles = []
        for song in range(self.len):
            questring = str(song+1) + ". " + self.song_queue[song].title
            titles.append(questring) 

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



    async def dequeue_and_play(self, ctx, index=0):
        if (self.queue.len >= 1):
            source = self.queue.pop(index)
            voice_channel = ctx.message.guild.voice_client
            voice_channel.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.dequeue_and_play(ctx), bot.loop))
            embed = generate_embed(ctx, self.queue, source)
            await bot.global_embeds[ctx.guild.id].edit(embed=embed)
        
        else:
            print("Else:")
            embed = generate_embed()
            await bot.global_embeds[ctx.guild.id].edit(embed=embed)
            


    async def search_play(self, ctx, url):

        await self.join(ctx) # wait to join voice channel
        voice_channel = ctx.message.guild.voice_client # get the channel
        view = generate_view(ctx)
        
        async with ctx.typing(): # show typing status while this process completes (basically 'loading')
           
            await YTDLSource.build_queue(url, loop=bot.loop, stream=True, ctx=ctx) # AudioSource Object
            await bot.global_embeds[ctx.guild.id].edit(embed = generate_embed(ctx, self.queue, player=voice_channel.source), view=view)
        


    async def stop_song(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing() or voice_client.is_paused():
            self.queue.clear()
            voice_client.stop()
            view = generate_view(ctx.guild.id)

            await bot.global_embeds[ctx.guild.id].edit(embed=generate_embed(), view=view)
        else:
            await ctx.send("Ongaku is not playing anything.", delete_after=5)


    async def pause_song(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            voice_client.pause()
        
        elif not voice_client.is_playing and not voice_client.is_paused:
            await ctx.send("Ongaku is not playing anything.", delete_after=5)


    async def resume_song(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_paused():
            voice_client.resume()
        
        elif not voice_client.is_paused() and not voice_client.is_playing:
            await ctx.send("No song to resume.", delete_after=5)


    async def next_song(self, ctx, index):
        voice_client = ctx.message.guild.voice_client

        if self.queue.len >=1 and index <= self.queue.len:
            
            if index != 0:
                self.queue.pop(index)
            
            await voice_client.stop() # stop triggers the "after" of dequeue_and_play 
            
        elif self.queue.len >=1 and index > self.queue.len:
            await ctx.send("Queue item unavailable", delete_after=5)

        else:
            await ctx.send("No next item in queue", delete_after=5)

    async def shuffle_queue(self, ctx):
        print("Before queue shuffle:",self.queue.display())
        self.queue.shuffle_v2()
        print("After Queue Shuffle:", self.queue.display())

        voice_channel = ctx.message.guild.voice_client
        view = generate_view(ctx)
        await bot.global_embeds[ctx.guild.id].edit(embed=generate_embed(ctx, self.queue, player=voice_channel.source), view=view)

    async def disconnect_bot(self, ctx):
        if not ctx.message.author.voice:
            await ctx.send("Ongaku is not connected to your voice channel.", delete_after=5)
            return
        
        else:
            await ctx.guild.voice_client.disconnect()



class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def get_metadata(cls, url, *, loop=None, stream=False):
        
        try: get(url) # check if the url is valid or is a search query
        except:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{url}", download=not stream)['entries'][0])
        else:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        return data

    @classmethod
    def make_player(cls, data, stream):
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        player = cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

        return player

    @classmethod
    def play_or_queue(cls, vc, player, ctx):
        if vc.is_playing() or vc.is_paused():
            bot.music_players[ctx.guild.id].queue.push(player)

        else:
            vc.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(bot.music_players[ctx.guild.id].dequeue_and_play(ctx), bot.loop))

    @classmethod
    async def build_queue(cls, url, *, loop=None, stream=False, ctx):
        loop = loop or asyncio.get_event_loop()
       
        data = await cls.get_metadata(url, loop=loop, stream=stream) # returns metadata of a given url
        voice_channel = ctx.message.guild.voice_client

        if 'entries' in data: # if there is a list of songs in the data (data is a playlist)

            for item in range(len(data['entries'])): # for every song in the playlist
                if item == 0:
                    data0 = data['entries'][item] # get the first song in the playlist
                    player = cls.make_player(data0, stream)
                    cls.play_or_queue(voice_channel, player, ctx)
                    

                else:
                    data_queue = (data['entries'][item]) # queue the remaining items
                    player_queue = cls.make_player(data_queue, stream)
                    bot.music_players[ctx.guild.id].queue.push(player_queue)


        else: 
            player = cls.make_player(data, stream)
            cls.play_or_queue(voice_channel, player, ctx)
        

        return


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
        await self.musicplayer.next_song(self.ctx, 0)

    


class invalidchannel(commands.CheckFailure):
    pass



######################## Checks ########################


def check_channel():
    def predicate(ctx):
        if not (ctx.channel.id in bot.command_channels):
            return False
    return commands.check(predicate)


async def format_command_channel(guild):
    command_channel = (discord.utils.get(guild.channels, name="ongaku-dev"))

    if command_channel not in bot.command_channels:
        bot.command_channels.append(command_channel.id)
        bot.music_players[guild.id] = MusicPlayer()

    messages = [msg async for msg in command_channel.history(limit=100, oldest_first=True)]
    for msg in messages:
        await msg.delete()

    embed = generate_embed()
    view = generate_view(command_channel)

    bot.global_embeds[guild.id] = await command_channel.send(embed=embed, view=view)


@bot.check
async def checkchannel(ctx):
    if not (ctx.channel.id in bot.command_channels):
            raise invalidchannel("Invalid Channel")
    return True


########################### Event Handlers ###########################



async def setup():
    bot.command_channels = []
    bot.global_embeds = {}
    bot.music_players = {}


    for guild in bot.guilds:
        
        bot.command_channels.append((discord.utils.get(guild.channels, name="ongaku-dev")).id)
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
        view = generate_view(channel)

        bot.global_embeds[channel.guild.id] = await channel.send(embed=embed, view=view)



@bot.event
async def on_ready(): # On connect 
    await setup()


@bot.event
async def on_guild_join(guild): # On connecting to server
    await format_command_channel(guild)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, invalidchannel):
        await ctx.send("Please use the Ongaku Commands channel for bot commands.", delete_after=5)


@bot.event
async def on_message(message):
    if (message.author.id != bot.user.id) and not (message.content.startswith(command_prefix)) : # If the message is not sent by the bot and is not a command
        if (message.channel.id in bot.command_channels): # if the message is sent in the command channel
            ctx = await bot.get_context(message) # Get message
            await bot.music_players[ctx.guild.id].search_play(ctx, message.content)
            await ctx.message.delete()

    await bot.process_commands(message) # prevents on_message from overriding on_command


@bot.event
async def on_voice_state_update(member, before, after):

    if (member.id != bot.user.id):
        return
    
    elif before.channel is None:
        voice = after.channel.guild.voice_client
        time = 0
        while True:
            await asyncio.sleep(1)
            time = time + 1
            if voice.is_playing() and not voice.is_paused():
                time = 0
            if time == 600: # 5 Minutes
                await bot.music_players[after.channel.guild.id].stop_song(after)
                await voice.disconnect()
            if not voice.is_connected():
                break


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
    

@bot.command(brief="Next song or song at queue position")
async def next(ctx, index=1):
    await ctx.message.delete()
    await bot.music_players[ctx.guild.id].next_song(ctx, index-1)


@bot.command(brief="Shuffles Playlist")
async def shuffle(ctx):
    await ctx.message.delete()
    await bot.music_players[ctx.guild.id].shuffle_queue(ctx)


# @bot.command(aliases=["setup"])
# async def reset(ctx):
#     await ctx.message.delete()
#     await format_command_channel(ctx.guild)
    


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


def generate_view(ctx):
    view = playbackUI(timeout=None)
    view.musicplayer=bot.music_players[ctx.guild.id]
    view.ctx = ctx
    
    return view


bot.run(TOKEN)
