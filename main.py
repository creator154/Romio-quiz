# main.py - Advanced Telegram Quiz Bot (Official Style Like @QuizBot)

import logging
import os
import uuid
import random
from telegram import (
    Update,
    Poll,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonPollType,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    PollAnswerHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TITLE, DESC, QUESTION, TIMER, SHUFFLE, NEGATIVE = range(6)
DEFAULT_TIMER = 30

TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN not set!")

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("➕ Create New Quiz")],
        [KeyboardButton("📂 View My Quizzes")]
    ]
    await update.message.reply_text(
        "Welcome! Choose option:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ---------------- CREATE FLOW ----------------

async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send Quiz Title:", reply_markup=ReplyKeyboardRemove())
    return TITLE

async def save_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("Send Description or /skip")
    return DESC

async def save_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "/skip":
        context.user_data["desc"] = update.message.text
    else:
        context.user_data["desc"] = ""

    context.user_data["questions"] = []

    keyboard = [[KeyboardButton("➕ Add Question", request_poll=KeyboardButtonPollType(type="quiz"))]]
    await update.message.reply_text(
        "Add your first question:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return QUESTION

# ---------------- SAVE QUESTIONS ----------------

async def save_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = update.message.poll
    if poll.type != Poll.QUIZ:
        await update.message.reply_text("Send Quiz Mode Poll only!")
        return QUESTION

    context.user_data["questions"].append({
        "question": poll.question,
        "options": [o.text for o in poll.options],
        "correct": poll.correct_option_id,
        "explanation": poll.explanation or ""
    })

    keyboard = [
        [KeyboardButton("➕ Add Next Question", request_poll=KeyboardButtonPollType(type="quiz"))],
        [KeyboardButton("/done")]
    ]

    await update.message.reply_text(
        f"✅ Saved ({len(context.user_data['questions'])}) questions\nAdd more or /done",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return QUESTION

# ---------------- TIMER ----------------

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data["questions"]:
        await update.message.reply_text("No questions added!")
        return ConversationHandler.END

    keyboard = [
        ["10", "15", "20"],
        ["30", "45", "60"]
    ]

    await update.message.reply_text(
        "Select Timer (seconds):",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return TIMER

async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["timer"] = int(update.message.text)
    keyboard = [
        ["No Shuffle"],
        ["Shuffle Questions"],
        ["Shuffle Answers"],
        ["Shuffle Both"]
    ]
    await update.message.reply_text(
        "Select Shuffle Mode:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return SHUFFLE

# ---------------- SHUFFLE ----------------

async def set_shuffle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["shuffle"] = update.message.text

    keyboard = [
        ["+4 / 0"],
        ["+4 / -0.5"],
        ["+4 / -1"]
    ]
    await update.message.reply_text(
        "Select Marking Scheme:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return NEGATIVE

# ---------------- NEGATIVE MARKING ----------------

async def set_negative(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scheme = update.message.text

    if scheme == "+4 / -1":
        negative = 1
    elif scheme == "+4 / -0.5":
        negative = 0.5
    else:
        negative = 0

    quiz_id = str(uuid.uuid4())[:8]

    context.bot_data.setdefault("quizzes", {})[quiz_id] = {
        "title": context.user_data["title"],
        "desc": context.user_data["desc"],
        "questions": context.user_data["questions"],
        "timer": context.user_data["timer"],
        "shuffle": context.user_data["shuffle"],
        "negative": negative,
    }

    keyboard = [[InlineKeyboardButton("▶️ Start Quiz in Group", callback_data=f"start_{quiz_id}")]]
    await update.message.reply_text(
        "✅ Quiz Saved Successfully!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    context.user_data.clear()
    return ConversationHandler.END

# ---------------- START QUIZ ----------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    quiz_id = query.data.split("_")[1]
    quiz = context.bot_data["quizzes"].get(quiz_id)

    context.chat_data["active"] = {
        "quiz": quiz,
        "index": 0,
        "scores": {},
        "players": set()
    }

    await query.edit_message_text("Quiz Started! Waiting for 2 players...")

    await send_next(context, query.message.chat.id)

# ---------------- SEND QUESTION ----------------

async def send_next(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    active = context.chat_data.get("active")
    if not active:
        return

    quiz = active["quiz"]

    if active["index"] >= len(quiz["questions"]):
        leaderboard = sorted(active["scores"].items(), key=lambda x: x[1], reverse=True)
        text = "🏆 Leaderboard:\n"
        for uid, score in leaderboard:
            text += f"{uid} : {score}\n"

        await context.bot.send_message(chat_id, text)
        context.chat_data.pop("active")
        return

    q = quiz["questions"][active["index"]]

    await context.bot.send_poll(
        chat_id=chat_id,
        question=q["question"],
        options=q["options"],
        type=Poll.QUIZ,
        correct_option_id=q["correct"],
        explanation=q["explanation"],
        is_anonymous=False,
        open_period=quiz["timer"],
    )

    active["index"] += 1

# ---------------- ANSWERS ----------------

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    active = context.chat_data.get("active")
    if not active:
        return

    quiz = active["quiz"]
    index = active["index"] - 1
    question = quiz["questions"][index]

    user_id = answer.user.id
    active["players"].add(user_id)

    selected = answer.option_ids[0] if answer.option_ids else None

    if selected == question["correct"]:
        active["scores"][user_id] = active["scores"].get(user_id, 0) + 4
    else:
        active["scores"][user_id] = active["scores"].get(user_id, 0) - quiz["negative"]

# ---------------- MAIN ----------------

def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("➕ Create New Quiz"), create)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_title)],
            DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_desc)],
            QUESTION: [
                MessageHandler(filters.POLL, save_question),
                CommandHandler("done", done)
            ],
            TIMER: [MessageHandler(filters.TEXT, set_timer)],
            SHUFFLE: [MessageHandler(filters.TEXT, set_shuffle)],
            NEGATIVE: [MessageHandler(filters.TEXT, set_negative)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PollAnswerHandler(handle_answer))

    app.run_polling()

if __name__ == "__main__":
    main()
