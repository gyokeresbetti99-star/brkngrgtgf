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

# ===== ROLE (HARD DEBUG) =====
async def give_role(user_id: int):
    try:
        guild = bot.get_guild(SERVER_ID)
        if not guild:
            print(f"❌ Guild not found. SERVER_ID={SERVER_ID} | bot guilds={[g.id for g in bot.guilds]}")
            return

        # Member: cache -> fetch fallback
        member = guild.get_member(user_id)
        if member is None:
            print("ℹ️ Member not in cache -> fetch_member()")
            member = await guild.fetch_member(user_id)

        role = guild.get_role(ROLE_ID)
        if role is None:
            print(f"❌ Role not found. ROLE_ID={ROLE_ID}")
            print("ℹ️ Available role IDs:", [r.id for r in guild.roles])
            return

        # Bot saját member objektuma
        bot_member = guild.get_member(bot.user.id)
        if bot_member is None:
            bot_member = await guild.fetch_member(bot.user.id)

        # HARD DEBUG
        print("====== ROLE DEBUG ======")
        print(f"Guild: {guild.name} ({guild.id})")
        print(f"Target member: {member} ({member.id})")
        print(f"Target role: {role.name} ({role.id}) managed={role.managed}")
        print(f"Bot top role: {bot_member.top_role.name} ({bot_member.top_role.id})")
        print(f"Bot perms: manage_roles={bot_member.guild_permissions.manage_roles} admin={bot_member.guild_permissions.administrator}")
        print("========================")

        # 1) managed role nem osztható
        if role.managed:
            print("❌ Ez a role 'managed' (integráció/automata), Discord nem engedi kiosztani.")
            return

        # 2) permission check
        if not bot_member.guild_permissions.manage_roles and not bot_member.guild_permissions.administrator:
            print("❌ Botnak nincs Manage Roles (guild szinten).")
            return

        # 3) hierarchia check
        if bot_member.top_role <= role:
            print("❌ Role hierarchy: bot top_role <= target role. Emeld a bot rangját még feljebb!")
            return

        # 4) már megvan?
        if role in member.roles:
            print("ℹ️ Member already has role.")
            return

        # 5) add role
        await member.add_roles(role, reason="Webhook alapú rangosztás")
        print(f"✅ ROLE ADDED OK -> {member} got {role.name}")

    except discord.Forbidden:
        print("❌ Forbidden: Discord tiltja (legtöbbször hierarchy vagy nincs Manage Roles).")
    except discord.NotFound:
        print("❌ NotFound: a felhasználó nincs a szerveren (vagy rossz ID).")
    except Exception as e:
        print(f"❌ ROLE ERROR: {type(e).__name__}: {e}")

# ===== RUN API =====
def run_api():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

threading.Thread(target=run_api, daemon=True).start()

bot.run(TOKEN)
