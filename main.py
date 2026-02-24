import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from motor.motor_asyncio import AsyncIOMotorClient

# ENV
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# Bot setup
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Mongo setup
client = AsyncIOMotorClient(MONGO_URI)
db = client["quizbot"]
quizzes = db["quizzes"]
games = db["games"]

# ---------------- START ---------------- #

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(
        "👋 Welcome to Quiz Bot\n\n"
        "Commands:\n"
        "/create - Create quiz\n"
        "/myquiz - View quizzes\n"
        "/ready - Ready in group"
    )

# ---------------- CREATE QUIZ ---------------- #

@dp.message(Command("create"))
async def create_quiz(message: Message):
    quiz = {
        "owner": message.from_user.id,
        "title": "Sample Quiz",
        "description": "This is demo quiz",
        "questions": []
    }
    await quizzes.insert_one(quiz)
    await message.answer("✅ Quiz Created!")

# ---------------- VIEW QUIZ ---------------- #

@dp.message(Command("myquiz"))
async def my_quiz(message: Message):
    user_quiz = await quizzes.find_one({"owner": message.from_user.id})
    if not user_quiz:
        await message.answer("❌ No quiz found")
        return

    await message.answer(
        f"📚 Title: {user_quiz['title']}\n"
        f"📝 Description: {user_quiz['description']}"
    )

# ---------------- READY SYSTEM ---------------- #

ready_users = set()

@dp.message(Command("ready"))
async def ready_cmd(message: Message):
    if message.chat.type == "private":
        await message.answer("❌ Use /ready in group")
        return

    ready_users.add(message.from_user.id)

    if len(ready_users) >= 2:
        await message.answer("🚀 2 Players Ready!\nQuiz Starting...")
        ready_users.clear()
    else:
        await message.answer("⏳ Waiting for 1 more player...")

# ---------------- MAIN ---------------- #

async def main():
    print("Bot Started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
