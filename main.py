import os
import uuid
import random
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PollAnswerHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN not set!")

TITLE, DESCRIPTION, QUESTION, OPTION1, OPTION2, OPTION3, OPTION4, CORRECT, ADD_MORE, TIMER, SHUFFLE = range(11)

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if args:
        quiz_id = args[0]
        if quiz_id in context.bot_data.get("quizzes", {}):
            await show_quiz_panel(update.message, context, quiz_id)
            return

    keyboard = [
        [InlineKeyboardButton("➕ Create Quiz", callback_data="create")]
    ]
    await update.message.reply_text(
        "🎯 Welcome to Quiz Bot",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- CREATE FLOW ----------------

async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        "scores": {},
        "current_index": 0
    }
    await update.message.reply_text("Send Description or /skip")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["quiz"]["description"] = update.message.text
    await update.message.reply_text("Send Question:")
    return QUESTION

async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text("Correct option number (1-4):")
    return CORRECT

async def correct(update, context):
    context.user_data["current_q"]["correct"] = int(update.message.text) - 1
    context.user_data["quiz"]["questions"].append(context.user_data["current_q"])

    keyboard = [
        [InlineKeyboardButton("➕ Add More", callback_data="more")],
        [InlineKeyboardButton("✅ Done", callback_data="done")]
    ]
    await update.message.reply_text(
        "Add more questions?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADD_MORE

async def add_more(update, context):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Send Question:")
    return QUESTION

async def done_questions(update, context):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Set timer (seconds):")
    return TIMER

async def set_timer(update, context):
    context.user_data["quiz"]["timer"] = int(update.message.text)
    keyboard = [
        [InlineKeyboardButton("🔀 Shuffle", callback_data="shuffle_yes")],
        [InlineKeyboardButton("➡ No Shuffle", callback_data="shuffle_no")]
    ]
    await update.message.reply_text(
        "Shuffle questions?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SHUFFLE

async def set_shuffle(update, context):
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
        f"🖊 {len(quiz['questions'])} Questions\n"
        f"⏱ {quiz['timer']} sec\n"
        f"{'🔀 Shuffle' if quiz['shuffle'] else '➡ No Shuffle'}"
    )

    keyboard = [
        [InlineKeyboardButton("▶ Start Quiz (Group)", callback_data=f"start_{quiz_id}")]
    ]

    await message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- QUIZ ENGINE ----------------

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.message.chat.type == "private":
        await query.message.reply_text("❌ Start this quiz inside a group.")
        return

    quiz_id = query.data.split("_")[1]
    quiz = context.bot_data["quizzes"][quiz_id]

    if quiz["shuffle"]:
        random.shuffle(quiz["questions"])

    quiz["scores"] = {}
    quiz["current_index"] = 0

    await send_next_question(context, query.message.chat_id, quiz_id)

async def send_next_question(context, chat_id, quiz_id):
    quiz = context.bot_data["quizzes"][quiz_id]
    index = quiz["current_index"]

    if index >= len(quiz["questions"]):
        await send_leaderboard(context, chat_id, quiz_id)
        return

    q = quiz["questions"][index]

    message = await context.bot.send_poll(
        chat_id=chat_id,
        question=q["question"],
        options=q["options"],
        type="quiz",
        correct_option_id=q["correct"],
        is_anonymous=False,
        open_period=quiz["timer"]
    )

    quiz["current_poll"] = message.poll.id

async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer

    for quiz_id, quiz in context.bot_data["quizzes"].items():
        if quiz.get("current_poll") == answer.poll_id:
            user = answer.user.id
            selected = answer.option_ids[0]
            correct = quiz["questions"][quiz["current_index"]]["correct"]

            quiz["scores"].setdefault(user, 0)

            if selected == correct:
                quiz["scores"][user] += 4
            else:
                quiz["scores"][user] -= 1

            break

async def send_leaderboard(context, chat_id, quiz_id):
    quiz = context.bot_data["quizzes"][quiz_id]
    scores = sorted(quiz["scores"].items(), key=lambda x: x[1], reverse=True)

    text = "🏆 Final Leaderboard\n\n"
    for i, (_, score) in enumerate(scores, 1):
        text += f"{i}. {score} pts\n"

    await context.bot.send_message(chat_id, text)

# ---------------- MAIN ----------------

app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(create, pattern="create")],
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
        ADD_MORE: [
            CallbackQueryHandler(add_more, pattern="more"),
            CallbackQueryHandler(done_questions, pattern="done")
        ],
        TIMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_timer)],
        SHUFFLE: [CallbackQueryHandler(set_shuffle)]
    },
    fallbacks=[]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv)
app.add_handler(CallbackQueryHandler(start_quiz, pattern="start_"))
app.add_handler(PollAnswerHandler(handle_poll))

app.run_polling()
