import os
import uuid
import random
from telegram import (
    Update, InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler,
    ContextTypes, ConversationHandler,
    filters
)

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN not set!")

# STATES
TITLE, DESCRIPTION, QUESTION, OPTION1, OPTION2, OPTION3, OPTION4, CORRECT, TIMER, SHUFFLE = range(10)

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Create New Quiz", callback_data="create")],
        [InlineKeyboardButton("📚 View Quizzes", callback_data="view")]
    ]
    await update.message.reply_text(
        "Welcome to Quiz Bot 🎯",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- CREATE FLOW ----------------

async def create_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Send Quiz Title:")
    return TITLE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["quiz"] = {
        "id": str(uuid.uuid4())[:8],
        "title": update.message.text,
        "description": "",
        "questions": [],
        "timer": 15,
        "shuffle": False,
        "players": {},
    }
    await update.message.reply_text("Send Description or type /skip")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["quiz"]["description"] = update.message.text
    return await ask_question(update)

async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await ask_question(update)

async def ask_question(update):
    await update.message.reply_text("Send Question:")
    return QUESTION

async def get_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["current_q"] = {
        "question": update.message.text,
        "options": []
    }
    await update.message.reply_text("Option 1:")
    return OPTION1

async def option1(update, context):
    context.user_data["current_q"]["options"].append(update.message.text)
    await update.message.reply_text("Option 2:")
    return OPTION2

async def option2(update, context):
    context.user_data["current_q"]["options"].append(update.message.text)
    await update.message.reply_text("Option 3:")
    return OPTION3

async def option3(update, context):
    context.user_data["current_q"]["options"].append(update.message.text)
    await update.message.reply_text("Option 4:")
    return OPTION4

async def option4(update, context):
    context.user_data["current_q"]["options"].append(update.message.text)
    await update.message.reply_text("Send correct option number (1-4):")
    return CORRECT

async def correct(update, context):
    context.user_data["current_q"]["correct"] = int(update.message.text) - 1
    context.user_data["quiz"]["questions"].append(context.user_data["current_q"])

    await update.message.reply_text("Set Timer (seconds):")
    return TIMER

async def timer(update, context):
    context.user_data["quiz"]["timer"] = int(update.message.text)

    keyboard = [
        [InlineKeyboardButton("🔀 Shuffle Yes", callback_data="shuffle_yes")],
        [InlineKeyboardButton("➡ No Shuffle", callback_data="shuffle_no")]
    ]
    await update.message.reply_text(
        "Shuffle Questions?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SHUFFLE

async def shuffle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["quiz"]["shuffle"] = "yes" in update.callback_query.data

    quiz = context.user_data["quiz"]
    context.bot_data.setdefault("quizzes", {})
    context.bot_data["quizzes"][quiz["id"]] = quiz

    await show_quiz_panel(update.callback_query.message, context, quiz["id"])
    return ConversationHandler.END

# ---------------- PANEL ----------------

async def show_quiz_panel(message, context, quiz_id):
    quiz = context.bot_data["quizzes"][quiz_id]

    text = (
        f"<b>{quiz['title']}</b>\n"
        f"{quiz['description'] or 'No description'}\n\n"
        f"🖊 {len(quiz['questions'])} question · "
        f"⏱ {quiz['timer']} sec · "
        f"{'🔀 shuffle' if quiz['shuffle'] else '⬇ no shuffle'}\n\n"
        f"External link:\n"
        f"https://t.me/{context.bot.username}?start={quiz_id}"
    )

    keyboard = [
        [InlineKeyboardButton("▶ Start this quiz", callback_data=f"start_{quiz_id}")],
        [InlineKeyboardButton("➕ Start quiz in group", switch_inline_query=quiz_id)],
        [InlineKeyboardButton("📤 Share quiz", switch_inline_query=quiz_id)],
        [InlineKeyboardButton("✏ Edit quiz", callback_data=f"edit_{quiz_id}")],
        [InlineKeyboardButton("📊 Quiz stats", callback_data=f"stats_{quiz_id}")]
    ]

    await message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- START QUIZ ----------------

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    quiz_id = query.data.split("_")[1]
    quiz = context.bot_data["quizzes"][quiz_id]

    if len(quiz["players"]) < 2:
        await query.message.reply_text("❌ Need at least 2 players to start!")
        return

    if quiz["shuffle"]:
        random.shuffle(quiz["questions"])

    await send_question(query.message, context, quiz_id, 0)

async def send_question(message, context, quiz_id, index):
    quiz = context.bot_data["quizzes"][quiz_id]
    q = quiz["questions"][index]

    options = q["options"]
    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"ans_{quiz_id}_{index}_{i}")]
        for i, opt in enumerate(options)
    ]

    await message.reply_text(
        q["question"],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, quiz_id, q_index, selected = query.data.split("_")
    quiz = context.bot_data["quizzes"][quiz_id]

    q = quiz["questions"][int(q_index)]
    user = query.from_user.id

    quiz["players"].setdefault(user, 0)

    if int(selected) == q["correct"]:
        quiz["players"][user] += 4
        await query.message.reply_text("✅ Correct +4")
    else:
        quiz["players"][user] -= 1
        await query.message.reply_text("❌ Wrong -1")

    leaderboard = "\n".join(
        [f"{i+1}. {score}" for i, score in enumerate(sorted(quiz["players"].values(), reverse=True))]
    )

    await query.message.reply_text(f"🏆 Leaderboard:\n{leaderboard}")

# ---------------- MAIN ----------------

app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(create_quiz, pattern="create")],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
        DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_description),
            CommandHandler("skip", skip_description)
        ],
        QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_question)],
        OPTION1: [MessageHandler(filters.TEXT & ~filters.COMMAND, option1)],
        OPTION2: [MessageHandler(filters.TEXT & ~filters.COMMAND, option2)],
        OPTION3: [MessageHandler(filters.TEXT & ~filters.COMMAND, option3)],
        OPTION4: [MessageHandler(filters.TEXT & ~filters.COMMAND, option4)],
        CORRECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, correct)],
        TIMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, timer)],
        SHUFFLE: [CallbackQueryHandler(shuffle)],
    },
    fallbacks=[]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv)
app.add_handler(CallbackQueryHandler(start_quiz, pattern="start_"))
app.add_handler(CallbackQueryHandler(answer, pattern="ans_"))

app.run_polling()
