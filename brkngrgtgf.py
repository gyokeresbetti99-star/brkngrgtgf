import os
import asyncio
from flask import Flask, request, jsonify
import discord
from discord.ext import commands

# Környezeti változók
TOKEN = os.environ.get("TOKEN")                 # Discord bot token
SERVER_ID = int(os.environ.get("SERVER_ID"))    # Discord szerver ID
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))  # Discord csatorna ID
PORT = int(os.environ.get("PORT", 3000))       # Railway adja a PORT-ot

# Discord bot setup
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Flask setup a webhookhoz
app = Flask(__name__)

# Egy aszinkron Queue a webhook üzenetek tárolásához
message_queue = asyncio.Queue()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Webhook received:", data)
    discord_id_raw = data.get("discordId")
    result = data.get("result")

    if not discord_id_raw or not result:
        print("Invalid webhook data")
        return jsonify({"status": "error", "message": "Missing discordId or result"}), 400

    try:
        discord_id = int(discord_id_raw)
    except Exception as e:
        print(f"Invalid Discord ID: {discord_id_raw}, error: {e}")
        return jsonify({"status": "error", "message": "Invalid discordId"}), 400

    # Üzenet berakása a queue-ba
    message_queue.put_nowait((discord_id, result))

    # Azonnali válasz a webhooknak
    return jsonify({"status": "ok"}), 200

async def message_worker():
    await bot.wait_until_ready()
    while True:
        try:
            discord_id, result = await message_queue.get()
            await send_dm(discord_id, result)
            await send_server_message(discord_id, result)
        except Exception as e:
            print(f"Worker error: {e}")
        await asyncio.sleep(0.1)  # kis szünet a loopban

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

# Flask és Discord futtatása ugyanabban az async loopban
def start_app():
    loop = asyncio.get_event_loop()
    # Indítsuk a queue worker-t
    loop.create_task(message_worker())
    # Indítsuk a Flask ASGI szerveren (Hypercorn)
    import hypercorn.asyncio
    from hypercorn.config import Config
    config = Config()
    config.bind = [f"0.0.0.0:{PORT}"]
    loop.run_until_complete(hypercorn.asyncio.serve(app, config))

# Indítás
if __name__ == "__main__":
    asyncio.run(bot.start(TOKEN))  # Ez indítja a botot
