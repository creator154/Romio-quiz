import asyncio
import os
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= STORAGE =================
quizzes = {}          # saved quizzes
active_games = {}     # running games

# ================= STATES =================
class CreateQuiz(StatesGroup):
    title = State()
    description = State()
    collecting = State()
    timer = State()
    shuffle = State()

# ================= START =================
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("📚 Advanced Quiz Bot\n\n/create - Create Quiz")

# ================= CREATE =================
@dp.message(Command("create"))
async def create(message: Message, state: FSMContext):
    await state.set_state(CreateQuiz.title)
    await message.answer("Send Quiz Title:")

@dp.message(CreateQuiz.title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text, questions=[])
    await state.set_state(CreateQuiz.description)
    await message.answer("Send Description:")

@dp.message(CreateQuiz.description)
async def set_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(CreateQuiz.collecting)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Question (Send Quiz Poll)", callback_data="info")]
    ])

    await message.answer(
        "Now send QUIZ type polls.\nWhen finished press /done",
        reply_markup=kb
    )

# ================= CAPTURE QUIZ POLL =================
@dp.message(CreateQuiz.collecting, F.poll)
async def capture_poll(message: Message, state: FSMContext):
    if message.poll.type != "quiz":
        await message.answer("❌ Only QUIZ type poll allowed.")
        return

    data = await state.get_data()

    data["questions"].append({
        "question": message.poll.question,
        "options": [o.text for o in message.poll.options],
        "correct": message.poll.correct_option_id
    })

    await state.update_data(questions=data["questions"])
    await message.answer("✅ Question added.")

# ================= DONE QUESTIONS =================
@dp.message(Command("done"))
async def done_questions(message: Message, state: FSMContext):
    await state.set_state(CreateQuiz.timer)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="10s", callback_data="timer_10"),
            InlineKeyboardButton(text="20s", callback_data="timer_20"),
            InlineKeyboardButton(text="30s", callback_data="timer_30")
        ]
    ])

    await message.answer("Select Timer:", reply_markup=kb)

# ================= TIMER =================
@dp.callback_query(F.data.startswith("timer_"))
async def set_timer(call: CallbackQuery, state: FSMContext):
    timer = int(call.data.split("_")[1])
    await state.update_data(timer=timer)
    await state.set_state(CreateQuiz.shuffle)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Shuffle ON 🔀", callback_data="shuffle_on"),
            InlineKeyboardButton(text="Shuffle OFF", callback_data="shuffle_off")
        ]
    ])

    await call.message.answer("Shuffle Questions?", reply_markup=kb)
    await call.answer()

# ================= SHUFFLE =================
@dp.callback_query(F.data.startswith("shuffle_"))
async def set_shuffle(call: CallbackQuery, state: FSMContext):
    shuffle = call.data.split("_")[1] == "on"

    data = await state.get_data()
    user_id = call.from_user.id

    if shuffle:
        random.shuffle(data["questions"])

    data["shuffle"] = shuffle
    quizzes[user_id] = data

    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Start in Group", callback_data=f"start_{user_id}")]
    ])

    await call.message.answer(
        f"🎉 Quiz Saved!\n"
        f"Questions: {len(data['questions'])}\n"
        f"Timer: {data['timer']} sec\n"
        f"Shuffle: {'ON' if shuffle else 'OFF'}",
        reply_markup=kb
    )

    await call.answer()

# ================= START GAME =================
@dp.callback_query(F.data.startswith("start_"))
async def start_game(call: CallbackQuery):
    owner = int(call.data.split("_")[1])

    if owner not in quizzes:
        await call.answer("Quiz not found.")
        return

    chat_id = call.message.chat.id
    quiz = quizzes[owner]

    active_games[chat_id] = {
        "questions": quiz["questions"],
        "timer": quiz["timer"],
        "current": 0,
        "scores": {}
    }

    await call.message.answer("🚀 Quiz Started!")
    await send_question(chat_id)
    await call.answer()

# ================= SEND QUESTION =================
async def send_question(chat_id):
    game = active_games[chat_id]

    if game["current"] >= len(game["questions"]):
        await finish_game(chat_id)
        return

    q = game["questions"][game["current"]]

    await bot.send_poll(
        chat_id=chat_id,
        question=q["question"],
        options=q["options"],
        type="quiz",
        correct_option_id=q["correct"],
        is_anonymous=False,
        open_period=game["timer"]
    )

    game["current"] += 1

# ================= HANDLE ANSWERS =================
@dp.poll_answer()
async def handle_answer(poll_answer):
    user = poll_answer.user
    option = poll_answer.option_ids[0]

    for chat_id, game in active_games.items():
        current_index = game["current"] - 1
        if current_index < 0:
            continue

        correct = game["questions"][current_index]["correct"]

        if user.id not in game["scores"]:
            game["scores"][user.id] = 0

        if option == correct:
            game["scores"][user.id] += 4
        else:
            game["scores"][user.id] -= 1

# ================= FINISH =================
async def finish_game(chat_id):
    game = active_games[chat_id]
    leaderboard = sorted(game["scores"].items(), key=lambda x: x[1], reverse=True)

    text = "🏁 Quiz Finished!\n\n"

    medals = ["🥇", "🥈", "🥉"]

    for i, (uid, score) in enumerate(leaderboard):
        medal = medals[i] if i < 3 else "🏅"
        text += f"{medal} {uid} — {score} pts\n"

    await bot.send_message(chat_id, text)
    del active_games[chat_id]

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
