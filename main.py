import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"✅ {bot.user} est connecté et prêt !")

bot.run("TON_TOKEN_ICI")
