from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from bson import ObjectId
import asyncio

from database.mongo import quizzes_collection, games_collection

router = Router()

# START QUIZ (Private → send to group instruction)
@router.callback_query(F.data.startswith("start_"))
async def start_quiz(callback: CallbackQuery):
    quiz_id = callback.data.split("_")[1]

    text = (
        "🚀 To start this quiz in a group:\n\n"
        "1. Add this bot to your group\n"
        "2. Send this command in group:\n\n"
        f"/startquiz {quiz_id}"
    )

    await callback.message.answer(text)


# GROUP COMMAND
@router.message(F.text.startswith("/startquiz"))
async def group_start(message: Message):
    if message.chat.type == "private":
        return await message.answer("❌ Use this in group.")

    parts = message.text.split()
    if len(parts) != 2:
        return await message.answer("Usage: /startquiz quiz_id")

    quiz_id = parts[1]
    quiz = await quizzes_collection.find_one({"_id": ObjectId(quiz_id)})

    if not quiz:
        return await message.answer("Quiz not found.")

    # create game session
    await games_collection.insert_one({
        "quiz_id": quiz_id,
        "chat_id": message.chat.id,
        "players": [],
        "scores": {},
        "current_q": 0,
        "started": False
    })

    await message.answer(
        "🎮 Quiz Ready!\n\n"
        "Minimum 2 players required.\n"
        "Send /ready to join."
    )


# READY SYSTEM
@router.message(F.text == "/ready")
async def player_ready(message: Message):
    game = await
