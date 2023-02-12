import os
import discord
from dotenv import load_dotenv


# Initialize discord API objects
intents = discord.Intents.default()
intents.message_content = True
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN') # Get token from .env
client = discord.Client(intents=intents) # Discord interaction object & load default intents

@client.event
async def on_ready():
    print(f'{client.user} has connected to discord')

client.run(TOKEN)