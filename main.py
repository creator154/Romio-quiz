import telebot
from telebot import types
import random
import json
import os

TOKEN = os.environ.get('BOT_TOKEN')  # Heroku ke liye better
bot = telebot.TeleBot(TOKEN)

DATA_FILE = "quizzes.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        quizzes = json.load(f)
else:
    quizzes = {}  # user_id: list of quiz dicts

active_games = {}  # group_id (int): {'quiz': dict, 'players': {user_id: score}, 'current_q': 0, 'started': False, ...}

poll_to_info = {}  # poll_id: {'group_id': int, 'q_index': int, 'correct': int}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(quizzes, f)

# Start
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type == 'private':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Create New Quiz", "📋 View Quizzes")
        bot.send_message(message.chat.id, "Welcome to NEET Quizer Bot 👑", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Use /ready to join the quiz!")

# Creation flow same rakha, lekin finish pe user ke quizzes list mein add karo
user_states = {}

@bot.message_handler(func=lambda m: m.text == "➕ Create New Quiz")
def create_quiz(message):
    uid = message.from_user.id
    user_states[uid] = {"step": "title", "questions": [], "timer": 30, "shuffle": False}
    bot.send_message(message.chat.id, "📝 Send Quiz Title:")

@bot.message_handler(func=lambda m: m.from_user.id in user_states)
def quiz_creation(message):
    uid = message.from_user.id
    state = user_states[uid]

    if state["step"] == "title":
        state["title"] = message.text
        state["step"] = "description"
        bot.send_message(message.chat.id, "📄 Send Description (or /skip):")

    elif state["step"] == "description":
        if message.text != '/skip':
            state["description"] = message.text
        state["step"] = "question"
        bot.send_message(message.chat.id, "❓ Send Question:")

    elif state["step"] == "question":
        state["current_q"] = {"question": message.text, "options": [], "correct": None}
        state["step"] = "options"
        bot.send_message(message.chat.id, "Send 4 options one by one (send 4 messages):")

    elif state["step"] == "options":
        state["current_q"]["options"].append(message.text)
        if len(state["current_q"]["options"]) < 4:
            bot.send_message(message.chat.id, f"Option {len(state['current_q']['options'])}/4 saved. Next:")
        else:
            state["current_q"]["options"] = state["current_q"]["options"][:4]  # max 4 for poll
            state["step"] = "correct"
            bot.send_message(message.chat.id, "Send correct option number (1-4):")

    elif state["step"] == "correct":
        try:
            correct = int(message.text) - 1
            if 0 <= correct < 4:
                state["current_q"]["correct"] = correct
                state["questions"].append(state["current_q"])
                del state["current_q"]
                show_quiz_options(message.chat.id, uid)
            else:
                bot.send_message(message.chat.id, "Invalid number! Send 1-4:")
        except:
            bot.send_message(message.chat.id, "Send number 1-4 only!")

def show_quiz_options(chat_id, uid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add More Question", callback_data="add_more"),
        types.InlineKeyboardButton("✅ Finish Quiz", callback_data="finish_quiz")
    )
    markup.add(
        types.InlineKeyboardButton(f"⏱ Timer: {user_states[uid]['timer']}s", callback_data="set_timer"),
        types.InlineKeyboardButton(f"🔀 Shuffle: {'ON' if user_states[uid]['shuffle'] else 'OFF'}", callback_data="toggle_shuffle")
    )
    bot.send_message(chat_id, "Question added! What next?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id
    if uid not in user_states:
        return

    state = user_states[uid]

    if call.data == "add_more":
        state["step"] = "question"
        bot.send_message(call.message.chat.id, "❓ Send Next Question:")

    elif call.data == "set_timer":
        bot.send_message(call.message.chat.id, "Send global timer in seconds (per question):")
        state["step"] = "timer_global"

    elif call.data == "toggle_shuffle":
        state["shuffle"] = not state["shuffle"]
        bot.answer_callback_query(call.id, f"Shuffle {'ON' if state['shuffle'] else 'OFF'}")
        show_quiz_options(call.message.chat.id, uid)

    elif call.data == "finish_quiz":
        if uid not in quizzes:
            quizzes[uid] = []
        quiz = {
            "title": state["title"],
            "description": state.get("description", ""),
            "questions": state["questions"],
            "timer": state["timer"],
            "shuffle": state["shuffle"]
        }
        quizzes[uid].append(quiz)
        save_data()
        del user_states[uid]

        bot.send_message(call.message.chat.id, f"Quiz '{quiz['title']}' saved! 🎉")
        show_user_quizzes(call.message.chat.id, uid)

    # Timer set (extra step)
    # Note: Agar timer set kar rahe ho toh alag handler banao ya state use karo

# View Quizzes
@bot.message_handler(func=lambda m: m.text == "📋 View Quizzes")
def view_quizzes(message):
    show_user_quizzes(message.chat.id, message.from_user.id)

def show_user_quizzes(chat_id, uid):
    if uid not in quizzes or not quizzes[uid]:
        bot.send_message(chat_id, "You have no quizzes yet.")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, quiz in enumerate(quizzes[uid]):
        markup.add(types.InlineKeyboardButton(quiz["title"], callback_data=f"select_quiz_{uid}_{i}"))
    bot.send_message(chat_id, "Your Quizzes:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_quiz_"))
def select_quiz(call):
    _, uid_str, i_str = call.data.split("_")
    uid = int(uid_str)
    i = int(i_str)
    quiz = quizzes[uid][i]

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚀 Start in Group", switch_inline_query_current_chat=f"{uid}_{i}"))
    bot.send_message(call.message.chat.id, f"Quiz: {quiz['title']}\n{quiz['description']}\nQuestions: {len(quiz['questions'])}", reply_markup=markup)

# Inline Query for starting quiz
@bot.inline_handler(lambda query: True)
def inline_query(query):
    if not query.query:
        return

    try:
        uid_str, i_str = query.query.split("_")
        uid = int(uid_str)
        i = int(i_str)
        if uid in quizzes and i < len(quizzes[uid]):
            quiz = quizzes[uid][i]
            r = types.InlineQueryResultArticle(
                id="quiz_start",
                title=f"Start: {quiz['title']}",
                description="Type /ready to join",
                input_message_content=types.InputTextMessageContent(
                    f"🧠 Quiz started: {quiz['title']}\nDescription: {quiz.get('description', '')}\n\nPlayers: type /ready to join!\nAdmin: type /go to begin"
                )
            )
            bot.answer_inline_query(query.id, [r], cache_time=0)
    except:
        pass

# Ready & Start
@bot.message_handler(commands=['ready'])
def ready(message):
    if message.chat.type in ['group', 'supergroup']:
        group_id = message.chat.id
        if group_id not in active_games:
            active_games[group_id] = {"players": {}, "current_q": 0, "started": False, "quiz": None}

        active_games[group_id]["players"][message.from_user.id] = 0
        bot.reply_to(message, f"{message.from_user.first_name} is ready! ({len(active_games[group_id]['players'])} players)")

@bot.message_handler(commands=['go'])
def go(message):
    if message.chat.type not in ['group', 'supergroup']:
        return

    group_id = message.chat.id
    if group_id not in active_games or active_games[group_id]["started"]:
        return

    if len(active_games[group_id]["players"]) < 2:
        bot.send_message(group_id, "At least 2 players needed!")
        return

    # Quiz set karna padega – abhi assume inline se set hua, lekin better way chahiye
    # For now, last quiz use kar rahe (improve later)
    if not active_games[group_id]["quiz"]:
        # Dummy – real mein inline se quiz set karo
        active_games[group_id]["quiz"] = list(quizzes.values())[0][0]  # fix later

    active_games[group_id]["started"] = True
    bot.send_message(group_id, "Quiz Starting Now! 🔥")
    send_next_question(group_id)

def send_next_question(group_id):
    game = active_games[group_id]
    quiz = game["quiz"]
    idx = game["current_q"]

    if idx >= len(quiz["questions"]):
        show_leaderboard(group_id)
        del active_games[group_id]
        return

    q = quiz["questions"][idx]
    options = q["options"][:]

    correct = q["correct"]
    if quiz["shuffle"]:
        random.shuffle(options)
        correct = options.index(q["options"][q["correct"]])  # new index after shuffle

    sent = bot.send_poll(
        group_id,
        q["question"],
        options,
        type="quiz",
        correct_option_id=correct,
        is_anonymous=False,
        open_period=quiz["timer"]
    )

    poll_id = sent.poll.id
    poll_to_info[poll_id] = {
        "group_id": group_id,
        "q_index": idx,
        "correct": correct
    }

    game["current_q"] += 1

@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    poll_id = poll_answer.poll_id
    if poll_id not in poll_to_info:
        return

    info = poll_to_info[poll_id]
    group_id = info["group_id"]
    if group_id not in active_games:
        del poll_to_info[poll_id]
        return

    game = active_games[group_id]
    user_id = poll_answer.user.id

    if user_id not in game["players"]:
        return

    chosen = poll_answer.option_ids[0] if poll_answer.option_ids else None
    if chosen == info["correct"]:
        game["players"][user_id] += 4  # example points
    else:
        game["players"][user_id] -= 1  # negative

    # Optional: if all answered, next (but poll timer pe depend)
    # Better rely on poll update for full results

@bot.poll_handler()
def handle_poll(poll):
    poll_id = poll.id
    if poll_id not in poll_to_info:
        return

    info = poll_to_info[poll_id]
    group_id = info["group_id"]
    if group_id not in active_games:
        del poll_to_info[poll_id]
        return

    # Poll closed (timer up or manual) - send results & next
    text = "Question Over!\n"
    for opt in poll.options:
        text += f"{opt.text}: {opt.voter_count} votes\n"

    bot.send_message(group_id, text)

    send_next_question(group_id)  # auto next
    del poll_to_info[poll_id]

def show_leaderboard(group_id):
    game = active_games[group_id]
    sorted_scores = sorted(game["players"].items(), key=lambda x: x[1], reverse=True)

    text = "🏆 Leaderboard 🏆\n\n"
    for rank, (uid, score) in enumerate(sorted_scores, 1):
        user = bot.get_chat_member(group_id, uid).user
        name = user.first_name
        text += f"{rank}. {name} - {score} pts\n"

    bot.send_message(group_id, text)

bot.infinity_polling()
