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
ROLE_ID = int(os.environ.get("ROLE_ID"))
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
async def process_messages():
    while not message_queue.empty():
        data = await message_queue.get()
        discord_id = int(data.get("discordId"))
        result = data.get("result")

        await send_dm(discord_id, result)
        await send_server_message(discord_id, result)

        # 👉 RANG OSZTÁS
        await give_role(discord_id)


# ===== ACTIONS =====
async def give_role(user_id: int):
    try:
        guild = bot.get_guild(SERVER_ID)
        if not guild:
            print("Szerver nem található")
            return

        member = guild.get_member(user_id)
        if not member:
            print("Felhasználó nincs a szerveren")
            return

        role = guild.get_role(ROLE_ID)
        if not role:
            print("Rang nem található")
            return

        if role in member.roles:
            print("Rang már megvan")
            return

        await member.add_roles(role, reason="TG sikeres")
        print(f"Rang kiosztva: {member.name}")

    except Exception as e:
        print(f"Role error: {e}")


# ===== RUN API =====
def run_api():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

threading.Thread(target=run_api).start()

bot.run(TOKEN)
