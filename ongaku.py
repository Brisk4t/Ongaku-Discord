import os
import discord
from dotenv import load_dotenv
from discord.ext import commands

# Initialize discord API objects
load_dotenv()
intents = discord.Intents.all()
command_channel = int(os.getenv('COMMAND_CHANNEL'))
testing_channel = int(os.getenv('TESTING_CHANNEL'))
intents.message_content = True
TOKEN = os.getenv('DISCORD_TOKEN') # Get token from .env
bot = commands.Bot(command_prefix="!", intents=intents) # Discord interaction object & load default intents



#classes

class invalidchannel(commands.CheckFailure):
    pass


#checks


def check_channel():
    def predicate(ctx):
        if not (ctx.channel.id == command_channel or ctx.channel.id == testing_channel):
            raise invalidchannel("Invalid Channel")
        return True
    return commands.check(predicate)



# Event Handlers

@bot.event
async def on_ready(): # On connect 
    print(f'{bot.user} has connected to discord')
    channel = bot.get_channel(command_channel)
    await channel.send("Ongaku Online.", delete_after=10)


@bot.command()
@check_channel()
async def test(ctx): # if !test is sent
    await ctx.send("Test Success", delete_after=5)


@bot.command()
async def horny(ctx):
    await ctx.send("Chup lavde krish saala paani hai nahi horny bol raha.")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, invalidchannel):
        await ctx.send("Please use the Ongaku Commands channel for bot commands.")





#helper functions

# async def check_channel(ctx):
#     if ctx.channel.id == command_channel:
#         return True
    
#     else:
#         await ctx.send("Please use the Ongaku Commands channel for bot commands", delete_after=5)
#         return False


bot.run(TOKEN)