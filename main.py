import telebot
from telebot import types
import random
import json
import os

TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(TOKEN)

DATA_FILE = "quizzes.json"

# ----------------- Storage -----------------

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        quizzes = json.load(f)
else:
    quizzes = {}

active_games = {}   # group_id -> game state


def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(quizzes, f)


# ----------------- Start Menu -----------------

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Create New Quiz", "📋 View Quizzes")
    bot.send_message(message.chat.id, "Welcome to Quiz Bot 👑", reply_markup=markup)


# ----------------- Create Quiz -----------------

user_states = {}

@bot.message_handler(func=lambda m: m.text == "➕ Create New Quiz")
def create_quiz(message):
    user_states[message.from_user.id] = {"step": "title"}
    bot.send_message(message.chat.id, "Send Quiz Title:")


@bot.message_handler(func=lambda m: m.from_user.id in user_states)
def quiz_creation(message):
    state = user_states[message.from_user.id]

    if state["step"] == "title":
        state["title"] = message.text
        state["questions"] = []
        state["timer"] = 15
        state["shuffle"] = False
        state["step"] = "description"
        bot.send_message(message.chat.id, "Send Description or type /skip")

    elif state["step"] == "description":
        state["description"] = message.text
        state["step"] = "question"
        bot.send_message(message.chat.id, "Send Question:")

    elif state["step"] == "question":
        state["current_question"] = {"question": message.text}
        state["step"] = "options"
        state["options"] = []
        bot.send_message(message.chat.id, "Send 4 options one by one:")

    elif state["step"] == "options":
        state["options"].append(message.text)
        if len(state["options"]) == 4:
            state["current_question"]["options"] = state["options"]
            state["step"] = "correct"
            bot.send_message(message.chat.id, "Send correct option number (1-4):")
        else:
            bot.send_message(message.chat.id, f"Option {len(state['options'])}/4 saved")

    elif state["step"] == "correct":
        correct = int(message.text) - 1
        state["current_question"]["correct"] = correct
        state["questions"].append(state["current_question"])

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Add More", callback_data="add_more"))
        markup.add(types.InlineKeyboardButton("⏱ Set Timer", callback_data="set_timer"))
        markup.add(types.InlineKeyboardButton("🔀 Toggle Shuffle", callback_data="toggle_shuffle"))
        markup.add(types.InlineKeyboardButton("✅ Finish Quiz", callback_data="finish_quiz"))

        bot.send_message(message.chat.id, "Question added 👌", reply_markup=markup)


# ----------------- Quiz Settings -----------------

@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    uid = call.from_user.id

    if call.data == "add_more":
        user_states[uid]["step"] = "question"
        bot.send_message(call.message.chat.id, "Send Next Question:")

    elif call.data == "set_timer":
        user_states[uid]["step"] = "timer"
        bot.send_message(call.message.chat.id, "Send timer in seconds:")

    elif call.data == "toggle_shuffle":
        user_states[uid]["shuffle"] = not user_states[uid]["shuffle"]
        bot.answer_callback_query(call.id, "Shuffle toggled")

    elif call.data == "finish_quiz":
        quiz_id = str(uid) + "_" + str(len(quizzes))
        quizzes[quiz_id] = user_states[uid]
        save_data()
        del user_states[uid]

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚀 Start This Quiz", callback_data=f"start_{quiz_id}"))

        bot.send_message(call.message.chat.id, "Quiz Saved 🎉", reply_markup=markup)

    elif call.data.startswith("start_"):
        quiz_id = call.data.split("_")[1]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Start Quiz In Group", switch_inline_query=quiz_id))
        bot.send_message(call.message.chat.id, "Choose group to start 👇", reply_markup=markup)


# ----------------- Inline Mode -----------------

@bot.inline_handler(lambda query: True)
def inline_query(query):
    quiz_id = query.query
    if quiz_id in quizzes:
        result = types.InlineQueryResultArticle(
            id="1",
            title="Start Quiz",
            input_message_content=types.InputTextMessageContent(
                f"📢 Quiz: {quizzes[quiz_id]['title']}\n\nType /ready to join!"
            )
        )
        bot.answer_inline_query(query.id, [result])


# ----------------- Join Game -----------------

@bot.message_handler(commands=['ready'])
def ready(message):
    group_id = str(message.chat.id)
    if group_id not in active_games:
        active_games[group_id] = {
            "players": {},
            "started": False,
            "index": 0
        }

    active_games[group_id]["players"][message.from_user.id] = 0
    bot.send_message(group_id, f"{message.from_user.first_name} joined!")


@bot.message_handler(commands=['go'])
def start_game(message):
    group_id = str(message.chat.id)

    if group_id not in active_games:
        return

    if len(active_games[group_id]["players"]) < 2:
        bot.send_message(group_id, "Need at least 2 players.")
        return

    active_games[group_id]["started"] = True
    send_next_question(group_id)


# ----------------- Send Question -----------------

def send_next_question(group_id):
    game = active_games[group_id]
    quiz = list(quizzes.values())[0]   # simple demo

    if game["index"] >= len(quiz["questions"]):
        show_leaderboard(group_id)
        return

    q = quiz["questions"][game["index"]]
    options = q["options"]

    if quiz["shuffle"]:
        combined = list(zip(options, range(len(options))))
        random.shuffle(combined)
        options, indexes = zip(*combined)
        correct = indexes.index(q["correct"])
    else:
        correct = q["correct"]

    bot.send_poll(
        int(group_id),
        q["question"],
        options,
        type="quiz",
        correct_option_id=correct,
        is_anonymous=False,
        open_period=quiz["timer"]
    )

    game["index"] += 1


# ----------------- Poll Answer -----------------

@bot.poll_answer_handler()
def handle_poll_answer(poll):
    user = poll.user.id
    option = poll.option_ids[0]

    for group_id, game in active_games.items():
        if user in game["players"]:
            quiz = list(quizzes.values())[0]
            q = quiz["questions"][game["index"] - 1]
            correct = q["correct"]

            if option == correct:
                game["players"][user] += 4
            else:
                game["players"][user] -= 1

            break


# ----------------- Leaderboard -----------------

def show_leaderboard(group_id):
    game = active_games[group_id]
    scores = sorted(game["players"].items(), key=lambda x: x[1], reverse=True)

    text = "🏆 Leaderboard:\n\n"
    for i, (uid, score) in enumerate(scores, 1):
        text += f"{i}. {uid} — {score} pts\n"

    bot.send_message(int(group_id), text)


# -----------------

bot.infinity_polling()
