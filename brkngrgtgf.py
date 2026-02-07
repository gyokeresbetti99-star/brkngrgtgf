import os
import asyncio
from fastapi import FastAPI, Request
import discord
from discord.ext import commands
import threading

# Környezeti változók Railway-ről
TOKEN = os.environ.get("TOKEN")                # Discord bot token
SERVER_ID = int(os.environ.get("SERVER_ID"))   # Discord szerver ID
CHANNEL_ID = int(os.environ.get("CHANNEL_ID")) # Discord csatorna ID
PORT = int(os.environ.get("PORT", 8080))      # Railway adja

# Discord bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Szükséges a content intent
bot = commands.Bot(command_prefix="!", intents=intents)

# FastAPI setup
app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    discord_id = int(data.get("discordId"))
    result = data.get("result")

    # DM küldés
    asyncio.create_task(send_dm(discord_id, result))

    # Szerver csatornába küldés
    asyncio.create_task(send_server_message(discord_id, result))

    return {"status": "ok"}

async def send_dm(user_id, result):
    try:
        user = await bot.fetch_user(user_id)
        if user:
            await user.send(f"Teszt eredményed: {result}")
    except Exception as e:
        print(f"DM error: {e}")

async def send_server_message(user_id, result):
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"<@{user_id}> Teszt eredmény: {result}")
        else:
            print("Csatorna nem található")
    except Exception as e:
        print(f"Server message error: {e}")

# Discord ready event
@bot.event
async def on_ready():
    print(f"Bot ready! Logged in as {bot.user}")

# FastAPI futtatása külön szálon
def run_api():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

threading.Thread(target=run_api).start()

# Discord bot indítása
bot.run(TOKEN)
