import os
import asyncio
import discord
from discord.ext import commands

TOKEN = os.environ.get("TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Async Queue a webhook üzenetekhez
message_queue = asyncio.Queue()

# Queue feldolgozása
async def message_worker():
    await bot.wait_until_ready()
    while True:
        discord_id, result = await message_queue.get()
        await send_dm(discord_id, result)
        await send_server_message(discord_id, result)
        await asyncio.sleep(0.1)

async def send_dm(user_id, result):
    try:
        user = await bot.fetch_user(user_id)
        if user:
            await user.send(f"Teszt eredményed: {result}")
            print(f"✅ DM sent to {user_id}")
    except Exception as e:
        print(f"DM error for {user_id}: {e}")

async def send_server_message(user_id, result):
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"<@{user_id}> Teszt eredmény: {result}")
            print(f"✅ Message sent to channel {CHANNEL_ID}")
    except Exception as e:
        print(f"Server message error: {e}")

# Külső process tud üzenetet rakni a queue-ba
async def add_to_queue(discord_id, result):
    await message_queue.put((discord_id, result))

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(message_worker())
    loop.run_until_complete(bot.start(TOKEN))
