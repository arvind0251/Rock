# bot.py
import asyncio
import random
import re
import logging
import os
from pyrogram.enums import ChatAction
from pyrogram import Client, filters
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram.types import Message
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# MongoDB setup
mongo_client = AsyncIOMotorClient(MONGO_URL)
word_db = mongo_client["Word"]["WordDb"]
asyncio.get_event_loop().run_until_complete(word_db.create_index("word"))

# Regex for filtering unwanted messages
UNWANTED_MESSAGE_REGEX = r"^[\W_]+$|[\/!?\~\\]"

# Pyrogram Client
RADHIKA = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@RADHIKA.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    await message.reply_text("Hey! Main ek learning chatbot hoon. Mujhe message bhejo ya reply mein jawaab do, main seekh jaunga!")

@RADHIKA.on_message(filters.all & ~filters.bot)
async def chatbot_handler(client, message: Message):
    if not message.text:
        return

    logger.info(f"Received message: {message.text} (Chat ID: {message.chat.id}, Private: {message.chat.type == 'private'})")

    if re.match(UNWANTED_MESSAGE_REGEX, message.text):
        logger.info("Unwanted message (special characters). Ignored.")
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
                    await message.reply_text(response["text"])
            except Exception as e:
                logger.error(f"Error sending response: {e}")
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
                        await message.reply_text(response["text"])
                except Exception as e:
                    logger.error(f"Error sending response: {e}")
        else:
            try:
                if message.text:
                    exists = await word_db.find_one({
                        "word": reply.text.lower().strip(),
                        "text": message.text
                    })
                    if not exists:
                        await word_db.insert_one({
                            "word": reply.text.lower().strip(),
                            "text": message.text,
                            "check": "text"
                        })
                elif message.sticker:
                    exists = await word_db.find_one({
                        "word": reply.text.lower().strip(),
                        "text": message.sticker.file_id
                    })
                    if not exists:
                        await word_db.insert_one({
                            "word": reply.text.lower().strip(),
                            "text": message.sticker.file_id,
                            "check": "sticker"
                        })
                logger.info("Learned new word-response pair.")
            except Exception as e:
                logger.error(f"Error learning new response: {e}")
