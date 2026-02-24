import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

TOKEN = os.getenv("BOT_TOKEN")  # Heroku config me set karo

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# =========================
# TEMP STORAGE
# =========================
quizzes = {}

# =========================
# STATES
# =========================
class CreateQuiz(StatesGroup):
    title = State()
    description = State()
    adding_question = State()

# =========================
# START
# =========================
@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(
        "📚 Quiz Bot\n\n"
        "/create - Create new quiz\n"
        "/myquiz - View my quiz"
    )

# =========================
# CREATE QUIZ
# =========================
@dp.message(Command("create"))
async def create_quiz(message: Message, state: FSMContext):
    await state.set_state(CreateQuiz.title)
    await message.answer("Send Quiz Title:")

# TITLE
@dp.message(CreateQuiz.title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(CreateQuiz.description)
    await message.answer("Send Quiz Description:")

# DESCRIPTION
@dp.message(CreateQuiz.description)
async def set_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(CreateQuiz.adding_question)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Question", callback_data="add_q")],
        [InlineKeyboardButton(text="✅ Done", callback_data="done_q")]
    ])

    await message.answer(
        "Title & Description saved ✅\n\n"
        "Now add questions:",
        reply_markup=keyboard
    )

# =========================
# ADD QUESTION BUTTON
# =========================
@dp.callback_query(F.data == "add_q")
async def add_question_button(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
        "Send question in this format:\n\n"
        "Question?\n"
        "Option1\n"
        "Option2\n"
        "Option3\n"
        "Option4\n"
        "Correct option number (1-4)"
    )
    await call.answer()

# =========================
# RECEIVE QUESTION
# =========================
@dp.message(CreateQuiz.adding_question)
async def receive_question(message: Message, state: FSMContext):
    lines = message.text.split("\n")

    if len(lines) < 6:
        await message.answer("❌ Format wrong. Send properly.")
        return

    question = lines[0]
    options = lines[1:5]
    correct = int(lines[5]) - 1

    data = await state.get_data()

    if "questions" not in data:
        data["questions"] = []

    data["questions"].append({
        "question": question,
        "options": options,
        "correct": correct
    })

    await state.update_data(questions=data["questions"])

    await message.answer("✅ Question added successfully!")

# =========================
# DONE BUTTON
# =========================
@dp.callback_query(F.data == "done_q")
async def finish_quiz(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = call.from_user.id

    quizzes[user_id] = data

    await state.clear()

    await call.message.answer(
        f"🎉 Quiz Saved!\n\n"
        f"Title: {data.get('title')}\n"
        f"Questions: {len(data.get('questions', []))}"
    )

    await call.answer()

# =========================
# VIEW QUIZ
# =========================
@dp.message(Command("myquiz"))
async def my_quiz(message: Message):
    user_id = message.from_user.id

    if user_id not in quizzes:
        await message.answer("❌ No quiz found.")
        return

    quiz = quizzes[user_id]

    await message.answer(
        f"📚 Your Quiz\n\n"
        f"Title: {quiz.get('title')}\n"
        f"Description: {quiz.get('description')}\n"
        f"Questions: {len(quiz.get('questions', []))}"
    )

# =========================
# RUN
# =========================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
