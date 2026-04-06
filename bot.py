import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import InputStream, InputAudioStream
import yt_dlp

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_STRING = os.getenv("SESSION_STRING")

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
call = PyTgCalls(user)

queue = {}

def download(query):
    ydl_opts = {"format": "bestaudio", "quiet": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)
        return info["entries"][0]["url"], info["entries"][0]["title"]

async def play_song(chat_id):
    if chat_id not in queue or len(queue[chat_id]) == 0:
        return

    url, title = queue[chat_id][0]

    await call.join_group_call(
        chat_id,
        InputStream(InputAudioStream(url)),
    )

@bot.on_message(filters.command("play"))
async def play(_, message):
    chat_id = message.chat.id

    if len(message.command) < 2:
        return await message.reply("Usage: /play song name")

    query = " ".join(message.command[1:])
    await message.reply("🔍 Searching...")

    url, title = download(query)

    if chat_id not in queue:
        queue[chat_id] = []

    queue[chat_id].append((url, title))

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ Pause", callback_data="pause"),
            InlineKeyboardButton("⏭ Skip", callback_data="skip"),
            InlineKeyboardButton("⏹ Stop", callback_data="stop")
        ]
    ])

    if len(queue[chat_id]) == 1:
        await play_song(chat_id)
        await message.reply(f"▶️ Playing: {title}", reply_markup=buttons)
    else:
        await message.reply(f"➕ Added to queue: {title}", reply_markup=buttons)

@bot.on_callback_query()
async def controls(_, query):
    chat_id = query.message.chat.id

    if query.data == "stop":
        queue[chat_id] = []
        await call.leave_group_call(chat_id)
        await query.message.reply("⏹ Stopped")

    elif query.data == "skip":
        if chat_id in queue and len(queue[chat_id]) > 1:
            queue[chat_id].pop(0)
            await play_song(chat_id)
            await query.message.reply("⏭ Skipped")
        else:
            await query.message.reply("❌ No next song")

    elif query.data == "pause":
        await call.pause_stream(chat_id)
        await query.message.reply("⏸ Paused")

async def main():
    await bot.start()
    await user.start()
    await call.start()
    print("Bot Running...")
    await idle()

from pyrogram.idle import idle
asyncio.get_event_loop().run_until_complete(main())