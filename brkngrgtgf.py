import os
import asyncio
from flask import Flask, request
import discord
from discord.ext import commands
import threading

# Környezeti változók
TOKEN = os.environ.get("TOKEN")  # Discord bot token
SERVER_ID = int(os.environ.get("SERVER_ID"))  # Discord szerver ID
PORT = int(os.environ.get("PORT", 3000))  # Railway adja a PORT-ot

# Discord bot setup
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Flask setup a webhookhoz
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    discord_id = int(data.get("discordId"))
    result = data.get("result")

    # DM küldés
    asyncio.run_coroutine_threadsafe(send_dm(discord_id, result), bot.loop)

    # Szerverre küldés
    asyncio.run_coroutine_threadsafe(send_server_message(discord_id, result), bot.loop)

    return "OK", 200

async def send_dm(user_id, result):
    try:
        user = await bot.fetch_user(user_id)
        if user:
            await user.send(f"Teszt eredményed: {result}")
    except Exception as e:
        print(f"DM error: {e}")

async def send_server_message(user_id, result):
    try:
        guild = bot.get_guild(SERVER_ID)
        if guild:
            channel = discord.utils.get(guild.text_channels)
            if channel:
                await channel.send(f"<@{user_id}> Teszt eredmény: {result}")
    except Exception as e:
        print(f"Server message error: {e}")

# Flask futtatása külön threadben
def run_flask():
    app.run(host="0.0.0.0", port=PORT)

threading.Thread(target=run_flask).start()

# Discord bot indítása
bot.run(TOKEN)
