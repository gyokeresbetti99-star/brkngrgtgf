import os
import threading
import queue  # <-- THREAD-SAFE QUEUE
from fastapi import FastAPI, Request
import discord
from discord.ext import commands, tasks

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
message_queue = queue.Queue()  # <-- THREAD-SAFE

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    message_queue.put(data)  # <-- NEM await, sima put
    return {"status": "ok"}

# ===== BOT READY =====
@bot.event
async def on_ready():
    print(f"✅ Bot ready: {bot.user} | Guilds: {[g.id for g in bot.guilds]}", flush=True)
    process_queue.start()

# ===== QUEUE PROCESSOR =====
@tasks.loop(seconds=1)
async def process_queue():
    while not message_queue.empty():
        data = message_queue.get()

        discord_id = int(data.get("discordId"))
        result = data.get("result")

        print(f"📩 Processing: discordId={discord_id}, result={result}", flush=True)

        await send_dm(discord_id, result)
        await send_server_message(discord_id, result)
        await give_role(discord_id)

# ===== ACTIONS =====
async def send_dm(user_id, result):
    try:
        user = await bot.fetch_user(user_id)
        await user.send(f"Teszt eredményed: {result}")
        print("✅ DM sent", flush=True)
    except Exception as e:
        print(f"DM error: {e}", flush=True)

async def send_server_message(user_id, result):
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"<@{user_id}> Teszt eredmény: {result}")
            print("✅ Channel message sent", flush=True)
        else:
            print("❌ Channel not found", flush=True)
    except Exception as e:
        print(f"Channel message error: {e}", flush=True)

async def give_role(user_id: int):
    try:
        guild = bot.get_guild(SERVER_ID)
        if not guild:
            print(f"❌ Guild not found. SERVER_ID={SERVER_ID}", flush=True)
            return

        # fetch_member biztosan API-ból jön
        member = await guild.fetch_member(user_id)

        role = guild.get_role(ROLE_ID)
        if role is None:
            print(f"❌ Role not found. ROLE_ID={ROLE_ID}", flush=True)
            return

        bot_member = guild.get_member(bot.user.id) or await guild.fetch_member(bot.user.id)

        print("====== ROLE DEBUG ======", flush=True)
        print(f"Target member: {member} ({member.id})", flush=True)
        print(f"Target role: {role.name} ({role.id}) managed={role.managed}", flush=True)
        print(f"Bot top role: {bot_member.top_role.name} ({bot_member.top_role.id})", flush=True)
        print(f"Bot perms: manage_roles={bot_member.guild_permissions.manage_roles} admin={bot_member.guild_permissions.administrator}", flush=True)
        print("========================", flush=True)

        if role.managed:
            print("❌ Managed role (integráció), nem osztható.", flush=True)
            return

        if bot_member.top_role <= role:
            print("❌ Role hierarchy: bot top_role <= target role", flush=True)
            return

        if role in member.roles:
            print("ℹ️ Member already has role", flush=True)
            return

        await member.add_roles(role, reason="Webhook alapú rangosztás")
        print(f"✅ ROLE ADDED -> {member} got {role.name}", flush=True)

    except discord.Forbidden:
        print("❌ Forbidden (permission/hierarchy)", flush=True)
    except discord.NotFound:
        print("❌ NotFound (user not in guild / bad ID)", flush=True)
    except Exception as e:
        print(f"❌ ROLE ERROR: {type(e).__name__}: {e}", flush=True)

# ===== RUN API =====
def run_api():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

threading.Thread(target=run_api, daemon=True).start()

bot.run(TOKEN)
