import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from motor.motor_asyncio import AsyncIOMotorClient

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Mongo
client = AsyncIOMotorClient(MONGO_URI)
db = client["quizbot"]
quiz_collection = db["quizzes"]

# Runtime memory
active_games = {}
ready_players = {}

# ---------------- START ---------------- #

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "📚 Quiz Bot\n\n"
        "/create - Create new quiz\n"
        "/myquiz - View my quiz"
    )

# ---------------- CREATE QUIZ ---------------- #

@dp.message(Command("create"))
async def create_quiz(message: Message):
    await quiz_collection.insert_one({
        "owner": message.from_user.id,
        "questions": [],
        "timer": 20
    })
    await message.answer("Send me quiz polls one by one.\nWhen done send /done")

# Capture quiz poll
@dp.message(F.poll)
async def capture_poll(message: Message):
    if message.poll.type != "quiz":
        return

    quiz = await quiz_collection.find_one({"owner": message.from_user.id})
    if not quiz:
        return

    question_data = {
        "question": message.poll.question,
        "options": [opt.text for opt in message.poll.options],
        "correct": message.poll.correct_option_id
    }

    await quiz_collection.update_one(
        {"_id": quiz["_id"]},
        {"$push": {"questions": question_data}}
    )

    await message.answer("✅ Question added. Send next or /done")

# Finish quiz
@dp.message(Command("done"))
async def finish_quiz(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 sec", callback_data="timer_10")],
        [InlineKeyboardButton(text="20 sec", callback_data="timer_20")],
        [InlineKeyboardButton(text="30 sec", callback_data="timer_30")],
        [InlineKeyboardButton(text="60 sec", callback_data="timer_60")]
    ])
    await message.answer("Select timer:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("timer_"))
async def set_timer(callback: CallbackQuery):
    timer = int(callback.data.split("_")[1])
    quiz = await quiz_collection.find_one({"owner": callback.from_user.id})

    await quiz_collection.update_one(
        {"_id": quiz["_id"]},
        {"$set": {"timer": timer}}
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Start in Group", callback_data=f"startquiz_{quiz['_id']}")]
    ])

    await callback.message.answer("Quiz saved!", reply_markup=keyboard)
    await callback.answer()

# ---------------- START IN GROUP ---------------- #

@dp.callback_query(F.data.startswith("startquiz_"))
async def start_in_group(callback: CallbackQuery):
    quiz_id = callback.data.split("_")[1]

    ready_players[quiz_id] = set()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="I'm Ready", callback_data=f"ready_{quiz_id}")]
    ])

    await callback.message.answer("Click Ready to join quiz", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("ready_"))
async def ready(callback: CallbackQuery):
    quiz_id = callback.data.split("_")[1]

    ready_players[quiz_id].add(callback.from_user.id)

    if len(ready_players[quiz_id]) >= 2:
        await callback.message.answer("🚀 Starting Quiz...")
        await start_game(callback.message.chat.id, quiz_id)
    else:
        await callback.answer("Waiting for more players...")

async def start_game(chat_id, quiz_id):
    quiz = await quiz_collection.find_one({"_id": quiz_collection.codec_options.document_class(quiz_id)})
    if not quiz:
        return

    active_games[chat_id] = {
        "quiz_id": quiz_id,
        "scores": {},
        "current_q": 0
    }

    await send_question(chat_id)

async def send_question(chat_id):
    game = active_games[chat_id]
    quiz = await quiz_collection.find_one({"_id": quiz_collection.codec_options.document_class(game["quiz_id"])})

    if game["current_q"] >= len(quiz["questions"]):
        await end_game(chat_id)
        return

    q = quiz["questions"][game["current_q"]]

    await bot.send_poll(
        chat_id,
        question=q["question"],
        options=q["options"],
        type="quiz",
        correct_option_id=q["correct"],
        is_anonymous=False,
        open_period=quiz["timer"]
    )

    game["current_q"] += 1

@dp.poll_answer()
async def handle_answer(poll_answer):
    user_id = poll_answer.user.id
    option = poll_answer.option_ids[0]

    for chat_id, game in active_games.items():
        quiz = await quiz_collection.find_one({"_id": quiz_collection.codec_options.document_class(game["quiz_id"])})
        q = quiz["questions"][game["current_q"] - 1]

        if user_id not in game["scores"]:
            game["scores"][user_id] = 0

        if option == q["correct"]:
            game["scores"][user_id] += 4
        else:
            game["scores"][user_id] -= 1

async def end_game(chat_id):
    game = active_games[chat_id]
    scores = game["scores"]

    leaderboard = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    text = "🏁 Quiz Finished!\n\n"

    medals = ["🥇", "🥈", "🥉"]

    for i, (user, score) in enumerate(leaderboard):
        medal = medals[i] if i < 3 else "🏅"
        text += f"{medal} {user} — {score} pts\n"

    await bot.send_message(chat_id, text)
    del active_games[chat_id]

# ---------------- RUN ---------------- #

async def main():
    print("Bot running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
