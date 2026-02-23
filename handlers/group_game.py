from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from bson import ObjectId
import asyncio
import random

from database.mongo import quizzes_collection, games_collection
from config import BOT_TOKEN

router = Router()
bot = Bot(BOT_TOKEN)

# START QUIZ BUTTON
@router.callback_query(F.data.startswith("start_"))
async def start_quiz(callback: CallbackQuery):
    quiz_id = callback.data.split("_")[1]

    await callback.message.answer(
        "Add bot to group and run:\n"
        f"/startquiz {quiz_id}"
    )

# GROUP START
@router.message(F.text.startswith("/startquiz"))
async def group_start(message: Message):
    if message.chat.type == "private":
        return await message.answer("Use in group.")

    quiz_id = message.text.split()[1]
    quiz = await quizzes_collection.find_one({"_id": ObjectId(quiz_id)})

    if not quiz:
        return await message.answer("Quiz not found.")

    await games_collection.insert_one({
        "quiz_id": quiz_id,
        "chat_id": message.chat.id,
        "players": [],
        "scores": {},
        "current_q": 0,
        "started": False
    })

    await message.answer(
        "🎮 Quiz Ready!\n"
        "Minimum 2 players required.\n"
        "Type /ready"
    )

# READY
@router.message(F.text == "/ready
