from aiogram import Router, F
from aiogram.types import Message
from database.mongo import quizzes_collection

router = Router()

@router.message(F.text == "📚 View My Quizzes")
async def view_quizzes(message: Message):
    quizzes = quizzes_collection.find({"user_id": message.from_user.id})

    text = "📚 Your Quizzes:\n\n"
    count = 0

    async for quiz in quizzes:
        count += 1
        text += f"{count}. {quiz['title']}\n"

    if count == 0:
        text = "You have no quizzes."

    await message.answer(text)
