import asyncio
import os
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())

quizzes = {}
active_games = {}
ready_players = {}

# ================= STATES =================
class QuizBuild(StatesGroup):
    title = State()
    description = State()
    collecting = State()
    timer = State()
    shuffle = State()

# ================= START MENU =================
@dp.message(Command("start"))
async def start(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🆕 Create New Quiz")],
            [KeyboardButton(text="📂 View My Quizzes")]
        ],
        resize_keyboard=True
    )
    await message.answer("🏠 Welcome to Quiz Bot", reply_markup=kb)

# ================= CREATE =================
@dp.message(F.text == "🆕 Create New Quiz")
async def create_quiz(message: Message, state: FSMContext):
    await state.set_state(QuizBuild.title)
    await message.answer("Send Quiz Title:", reply_markup=ReplyKeyboardRemove())

@dp.message(QuizBuild.title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text, questions=[])
    await state.set_state(QuizBuild.description)
    await message.answer("Send Description or type /skip")

@dp.message(Command("skip"), QuizBuild.description)
async def skip_desc(message: Message, state: FSMContext):
    await state.update_data(description="")
    await ask_add_question(message, state)

@dp.message(QuizBuild.description)
async def set_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await ask_add_question(message, state)

async def ask_add_question(message: Message, state: FSMContext):
    await state.set_state(QuizBuild.collecting)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Add Question")],
            [KeyboardButton(text="✅ Done")]
        ],
        resize_keyboard=True
    )
    await message.answer("Add quiz questions:", reply_markup=kb)

# ================= ADD QUESTION =================
@dp.message(QuizBuild.collecting, F.text == "➕ Add Question")
async def add_question(message: Message):
    await message.answer("Send a QUIZ type poll now.")

@dp.message(QuizBuild.collecting, F.poll)
async def capture_poll(message: Message, state: FSMContext):
    if message.poll.type != "quiz":
        await message.answer("Only QUIZ poll allowed.")
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
@dp.message(QuizBuild.collecting, F.text == "✅ Done")
async def done_questions(message: Message, state: FSMContext):
    await state.set_state(QuizBuild.timer)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="10 sec"), KeyboardButton(text="20 sec")],
            [KeyboardButton(text="30 sec")]
        ],
        resize_keyboard=True
    )
    await message.answer("Select Timer:", reply_markup=kb)

# ================= TIMER =================
@dp.message(QuizBuild.timer)
async def set_timer(message: Message, state: FSMContext):
    timer = int(message.text.split()[0])
    await state.update_data(timer=timer)
    await state.set_state(QuizBuild.shuffle)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Shuffle ON")],
            [KeyboardButton(text="Shuffle OFF")]
        ],
        resize_keyboard=True
    )
    await message.answer("Shuffle questions?", reply_markup=kb)

# ================= SHUFFLE =================
@dp.message(QuizBuild.shuffle)
async def set_shuffle(message: Message, state: FSMContext):
    shuffle = message.text == "Shuffle ON"
    data = await state.get_data()

    if shuffle:
        random.shuffle(data["questions"])

    data["shuffle"] = shuffle
    user_id = message.from_user.id
    quizzes[user_id] = data

    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Start The Quiz", callback_data=f"start_{user_id}")]
    ])

    await message.answer("Quiz Saved!", reply_markup=kb)

# ================= START QUIZ =================
@dp.callback_query(F.data.startswith("start_"))
async def start_quiz(call: CallbackQuery):
    owner = int(call.data.split("_")[1])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Start in Group", callback_data=f"group_{owner}")]
    ])

    await call.message.answer("Where do you want to start?", reply_markup=kb)
    await call.answer()

# ================= GROUP START =================
@dp.callback_query(F.data.startswith("group_"))
async def group_start(call: CallbackQuery):
    owner = int(call.data.split("_")[1])
    chat_id = call.message.chat.id

    ready_players[chat_id] = set()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="I'm Ready", callback_data=f"ready_{owner}")]
    ])

    active_games[chat_id] = {
        "owner": owner,
        "current": 0,
        "scores": {}
    }

    await call.message.answer("Click Ready (Min 2 players)", reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data.startswith("ready_"))
async def ready(call: CallbackQuery):
    chat_id = call.message.chat.id
    ready_players[chat_id].add(call.from_user.id)

    if len(ready_players[chat_id]) >= 2:
        await call.message.answer("🚀 Quiz Starting...")
        await send_question(chat_id)
    else:
        await call.answer("Waiting for more players...")

# ================= SEND QUESTION =================
async def send_question(chat_id):
    game = active_games[chat_id]
    quiz = quizzes[game["owner"]]

    if game["current"] >= len(quiz["questions"]):
        await finish_game(chat_id)
        return

    q = quiz["questions"][game["current"]]

    await bot.send_poll(
        chat_id,
        q["question"],
        q["options"],
        type="quiz",
        correct_option_id=q["correct"],
        is_anonymous=False,
        open_period=quiz["timer"]
    )

    game["current"] += 1

# ================= ANSWERS =================
@dp.poll_answer()
async def handle_answer(poll_answer):
    user = poll_answer.user

    for chat_id, game in active_games.items():
        idx = game["current"] - 1
        if idx < 0:
            continue

        correct = quizzes[game["owner"]]["questions"][idx]["correct"]
        selected = poll_answer.option_ids[0]

        if user.id not in game["scores"]:
            game["scores"][user.id] = 0

        if selected == correct:
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
