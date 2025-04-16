import asyncio
import random
import re
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from motor.motor_asyncio import AsyncIOMotorClient

from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URL, IMG, STICKER, EMOJIOS

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# MongoDB
mongo_client = AsyncIOMotorClient(MONGO_URL)
word_db = mongo_client["Word"]["WordDb"]
asyncio.get_event_loop().run_until_complete(word_db.create_index("word"))

# Bot client
RADHIKA = Client("r-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Regex to ignore symbols
UNWANTED_MESSAGE_REGEX = r"^[\W_]+$|[\/!?\~\\]"

@RADHIKA.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    await message.reply_photo(
        photo=random.choice(IMG),
        caption="Hey! Main Nikku ka setting hu, friend.",
    )

@RADHIKA.on_message(filters.all & ~filters.bot)
async def chatbot_handler(client, message: Message):
    if not message.text:
        return

    logger.info(f"Received: {message.text} (From: {message.chat.id})")

    if re.match(UNWANTED_MESSAGE_REGEX, message.text):
        return

    if message.chat.type in ("private", "group", "supergroup"):
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)

    user_text = message.text.lower().strip()

    if not message.reply_to_message:
        responses = await word_db.find({"word": user_text}).to_list(length=10)
        if responses:
            response = random.choice(responses)
            try:
                if response["check"] == "sticker":
                    await message.reply_sticker(response["text"])
                else:
                    emoji = random.choice(EMOJIOS)
                    await message.reply_text(f"{emoji} {response['text']}")
            except Exception as e:
                logger.error(f"Send error: {e}")
    else:
        reply = message.reply_to_message
        if reply.from_user and reply.from_user.id == (await client.get_me()).id:
            responses = await word_db.find({"word": user_text}).to_list(length=10)
            if responses:
                response = random.choice(responses)
                try:
                    if response["check"] == "sticker":
                        await message.reply_sticker(response["text"])
                    else:
                        emoji = random.choice(EMOJIOS)
                        await message.reply_text(f"{emoji} {response['text']}")
                except Exception as e:
                    logger.error(f"Send error: {e}")
        else:
            try:
                if message.text:
                    await word_db.insert_one({
                        "word": reply.text.lower().strip(),
                        "text": message.text,
                        "check": "text"
                    })
                elif message.sticker:
                    await word_db.insert_one({
                        "word": reply.text.lower().strip(),
                        "text": message.sticker.file_id,
                        "check": "sticker"
                    })
                logger.info("Learned a new response.")
            except Exception as e:
                logger.error(f"Learning error: {e}")

if __name__ == "__main__":
    RADHIKA.run()
