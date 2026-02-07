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
    print(f"✅ Bot ready: {bot.user} | Guilds: {[g.id for g in bot.guilds]}")
    process_queue.start()

# ===== QUEUE PROCESSOR =====
@tasks.loop(seconds=1)
async def process_queue():
    while not queue.empty():
        data = await queue.get()

        try:
            discord_id = int(data.get("discordId"))
            result = data.get("result")

            print(f"📩 Webhook received: discordId={discord_id}, result={result}")

            await send_dm(discord_id, result)
            await send_server_message(discord_id, result)

            # ✅ csak akkor adjon rangot, ha sikeres
            # Ha más szöveg jön a GAS-ból, ezt írd át (pl. "Sikeres", "OK", "PASS")
            if str(result).lower() in ["sikeres", "success", "ok", "pass", "true", "1"]:
                await give_role(discord_id)
            else:
                print("ℹ️ Result nem 'sikeres', ezért nem osztok rangot.")

        except Exception as e:
            print(f"❌ process_queue error: {e}")

# ===== ACTIONS =====
async def send_dm(user_id, result):
    try:
        user = await bot.fetch_user(user_id)
        await user.send(f"Teszt eredményed: {result}")
        print("✅ DM sent")
    except Exception as e:
        print(f"DM error: {e}")

async def send_server_message(user_id, result):
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"<@{user_id}> Teszt eredmény: {result}")
            print("✅ Channel message sent")
        else:
            print("❌ Channel not found (CHANNEL_ID wrong or bot has no access)")
    except Exception as e:
        print(f"Channel message error: {e}")

async def give_role(user_id):
    try:
        guild = bot.get_guild(SERVER_ID)
        if not guild:
            print(f"❌ Guild not found. SERVER_ID={SERVER_ID} | bot guilds={[g.id for g in bot.guilds]}")
            return

        # 1) próbáljuk cache-ből (ha megvan)
        member = guild.get_member(user_id)

        # 2) ha nincs, fetch (API)
        if not member:
            print("ℹ️ Member not in cache, fetching from Discord API...")
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound:
                print("❌ Member not found on server (user is not in guild)")
                return

        role = guild.get_role(ROLE_ID)
        if not role:
            print(f"❌ Role not found. ROLE_ID={ROLE_ID}")
            print("ℹ️ Roles on server:", [r.id for r in guild.roles])
            return

        # Bot role hierarchia ellenőrzés (nagyon gyakori hiba)
        me = guild.me or await guild.fetch_member(bot.user.id)
        if me.top_role <= role:
            print(f"❌ Role hierarchy issue: bot top_role ({me.top_role.id}) <= target role ({role.id})")
            print("➡️ Emeld a bot rangját a kiosztandó rang fölé a szerveren!")
            return

        if role in member.roles:
            print("ℹ️ Member already has the role")
            return

        await member.add_roles(role, reason="Webhook alapú rangosztás")
        print(f"✅ Role added: member={member} role={role.name} ({role.id})")

    except discord.Forbidden:
        print("❌ Forbidden: Bot has no permission to manage roles OR role hierarchy is wrong.")
    except Exception as e:
        print(f"ROLE ERROR: {e}")

# ===== RUN API =====
def run_api():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

threading.Thread(target=run_api, daemon=True).start()

bot.run(TOKEN)
