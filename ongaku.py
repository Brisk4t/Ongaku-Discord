import os
import discord
from dotenv import load_dotenv
from discord.ext import commands

# Initialize discord API objects
load_dotenv()
intents = discord.Intents.all()
command_channel = int(os.getenv('COMMAND_CHANNEL'))
intents.message_content = True
TOKEN = os.getenv('DISCORD_TOKEN') # Get token from .env
bot = commands.Bot(command_prefix="!", intents=intents) # Discord interaction object & load default intents




# Event Handlers

@bot.event
async def on_ready(): # On connect 
    print(f'{bot.user} has connected to discord')
    channel = bot.get_channel(command_channel)
    await channel.send("Ongaku Online.", delete_after=10)


@bot.command()
async def test(ctx): # if !test is sent
    if await check_channel(ctx):
        await ctx.send("Test Success", delete_after=5)







#helper functions

async def check_channel(ctx):
    if ctx.channel.id == command_channel:
        return True
    
    else:
        await ctx.send("Please use the Ongaku Commands channel for bot commands", delete_after=5)
        return False


bot.run(TOKEN)