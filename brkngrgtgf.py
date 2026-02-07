import os
import asyncio
from flask import Flask, request
import discord
from discord.ext import commands
import threading

# Környezeti változók
TOKEN = os.environ.get("TOKEN")                # Discord bot token
SERVER_ID = int(os.environ.get("SERVER_ID"))   # Discord szerver ID
CHANNEL_ID = int(os.environ.get("CHANNEL_ID")) # Discord csatorna ID
PORT = int(os.environ.get("PORT", 3000))      # Railway adja a PORT-ot

# Discord bot setup
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Flask setup a webhookhoz
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Webhook received:", data)  # Debug: lássuk mi érkezik
    discord_id_raw = data.get("discordId")
    result = data.get("result")
    
    if not discord_id_raw or not result:
        print("Invalid webhook data")
        return "Bad Request", 400

    try:
        discord_id = int(discord_id_raw)
    except Exception as e:
        print(f"Invalid Discord ID: {discord_id_raw}, error: {e}")
        return "Bad Discord ID", 400

    # DM küldés
    asyncio.run_coroutine_threadsafe(send_dm(discord_id, result), bot.loop)

    # Szerverre küldés a megadott csatornába
    asyncio.run_coroutine_threadsafe(send_server_message(discord_id, result), bot.loop)

    return "OK", 200

async def send_dm(user_id, result):
    try:
        user = await bot.fetch_user(user_id)
        if user:
            await user.send(f"Teszt eredményed: {result}")
            print(f"✅ DM sent to {user_id}")
        else:
            print(f"❌ User {user_id} not found")
    except Exception as e:
        print(f"DM error for {user_id}: {e}")

async def send_server_message(user_id, result):
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"<@{user_id}> Teszt eredmény: {result}")
            print(f"✅ Message sent to channel {CHANNEL_ID}")
        else:
            print(f"❌ Channel {CHANNEL_ID} not found")
    except Exception as e:
        print(f"Server message error for channel {CHANNEL_ID}: {e}")

# Flask futtatása külön threadben
def run_flask():
    print(f"Flask running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)

threading.Thread(target=run_flask).start()

# Discord bot indítása
print("Bot starting...")
bot.run(TOKEN)
