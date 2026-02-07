import os
import asyncio
from fastapi import FastAPI, Request
import discord
from discord.ext import commands
import uvicorn

# Környezeti változók
TOKEN = os.environ.get("TOKEN")                 # Discord bot token
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))  # Discord csatorna ID
PORT = int(os.environ.get("PORT", 3000))       # Railway adja a PORT-ot

# Discord bot setup
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# FastAPI app setup a bot service-ben
app = FastAPI()

# Async Queue
message_queue = asyncio.Queue()

# Queue worker feldolgozza az üzeneteket
async def message_worker():
    await bot.wait_until_ready()
    while True:
        try:
            discord_id, result = await message_queue.get()
            await send_dm(discord_id, result)
            await send_server_message(discord_id, result)
        except Exception as e:
            print(f"Worker error: {e}")
        await asyncio.sleep(0.1)

# DM küldés
async def send_dm(user_id, result):
    try:
        user = await bot.fetch_user(user_id)
        if user:
            await user.send(f"Teszt eredményed: {result}")
            print(f"✅ DM sent to {user_id}")
    except Exception as e:
        print(f"DM error for {user_id}: {e}")

# Szerver üzenet küldés
async def send_server_message(user_id, result):
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"<@{user_id}> Teszt eredmény: {result}")
            print(f"✅ Message sent to channel {CHANNEL_ID}")
    except Exception as e:
        print(f"Server message error: {e}")

# Queue endpoint a webhook számára
@app.post("/queue")
async def queue_endpoint(request: Request):
    data = await request.json()
    discord_id = data.get("discordId")
    result = data.get("result")

    if not discord_id or not result:
        return {"status": "error", "message": "Missing discordId or result"}

    try:
        discord_id = int(discord_id)
    except Exception:
        return {"status": "error", "message": "Invalid discordId"}

    await message_queue.put((discord_id, result))
    return {"status": "ok"}

# Indítás
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # Indítsuk a queue worker-t
    loop.create_task(message_worker())

    # Discord bot indítása külön taskban
    loop.create_task(bot.start(TOKEN))

    # FastAPI ASGI szerver indítása ugyanabban a containerben
    uvicorn.run(app, host="0.0.0.0", port=PORT)
