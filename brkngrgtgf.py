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

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")
    process_queue.start()

@tasks.loop(seconds=1)
async def process_queue():
    while not queue.empty():
        data = await queue.get()
        discord_id = int(data["discordId"])
        result = data["result"]

        await send_dm(discord_id, result)
        await send_server_message(discord_id, result)
        await give_role(discord_id)

# ===== ACTIONS =====
async def send_dm(user_id, result):
    try:
        user = await bot.fetch_user(user_id)
        await user.send(f"🎉 Teszt eredményed: **{result}**")
    except Exception as e:
        print("DM error:", e)

async def send_server_message(user_id, result):
    try:
        channel = bot.get_channel(CHANNEL_ID)
        await channel.send(f"<@{user_id}> sikeresen teljesítette a tesztet! ✅")
    except Exception as e:
        print("Channel error:", e)

async def give_role(user_id):
    try:
        guild = bot.get_guild(SERVER_ID)
        member = await guild.fetch_member(user_id)
        role = guild.get_role(ROLE_ID)

        if role in member.roles:
            print("ℹ️ Rang már megvan")
            return

        await member.add_roles(role)
        print("✅ Rang kiosztva")

    except Exception as e:
        print("Role error:", e)

# ===== RUN API =====
def run_api():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

threading.Thread(target=run_api).start()

bot.run(TOKEN)
