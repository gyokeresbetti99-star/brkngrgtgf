import os
import asyncio
from fastapi import FastAPI, Request
import discord
from discord.ext import commands, tasks
import threading

# ===== ENV =====
TOKEN = os.environ["TOKEN"]
SERVER_ID = int(os.environ["SERVER_ID"])
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
ROLE_ID = int(os.environ["ROLE_ID"])
PORT = int(os.environ.get("PORT", 8080))

# ===== DISCORD =====
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== API =====
app = FastAPI()
queue = asyncio.Queue()

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    await queue.put(data)
    return {"status": "ok"}

# ===== BOT READY =====
@bot.event
async def on_ready():
    print(f"✅ Bot ready: {bot.user}")
    process_queue.start()

# ===== QUEUE PROCESSOR =====
@tasks.loop(seconds=1)
async def process_queue():
    while not queue.empty():
        data = await queue.get()

        discord_id = int(data.get("discordId"))
        result = data.get("result")

        await send_dm(discord_id, result)
        await send_server_message(discord_id, result)
        await give_role(discord_id)

# ===== ACTIONS =====
async def send_dm(user_id, result):
    try:
        user = await bot.fetch_user(user_id)
        await user.send(f"Teszt eredményed: {result}")
    except Exception as e:
        print(f"DM error: {e}")

async def send_server_message(user_id, result):
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"<@{user_id}> Teszt eredmény: {result}")
    except Exception as e:
        print(f"Channel message error: {e}")

async def give_role(user_id):
    try:
        guild = bot.get_guild(SERVER_ID)
        if not guild:
            print("❌ Guild nem található")
            return

        member = await guild.fetch_member(user_id)
        if not member:
            print("❌ Member nem található")
            return

        role = guild.get_role(ROLE_ID)
        if not role:
            print("❌ Role nem található")
            return

        if role in member.roles:
            print("ℹ️ Felhasználónak már van rangja")
            return

        await member.add_roles(role, reason="Webhook alapú rangosztás")
        print(f"✅ Rang kiosztva: {member} ({role.name})")

    except Exception as e:
        print(f"ROLE ERROR: {e}")

# ===== RUN API =====
def run_api():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

threading.Thread(target=run_api).start()

bot.run(TOKEN)
