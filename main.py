import telebot
from telebot import types
import random
import json
import os

# Heroku ke liye environment variable use karo
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "quizzes.json"

# Data load
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        quizzes = json.load(f)  # user_id (str): list of quiz dicts
else:
    quizzes = {}

active_games = {}       # group_id (int): game state
poll_to_info = {}       # poll_id: {'group_id': int, 'q_index': int, 'correct': int}

user_states = {}        # creation ke liye temporary state

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(quizzes, f, indent=2)

# ----------------- Start & Main Menu -----------------
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type == 'private':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("➕ Create New Quiz", "📋 View Quizzes")
        bot.send_message(message.chat.id, "Welcome to NEET Quizer Bot 👑\nLet's create or play quizzes!", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Group mein quiz ke liye /ready bol do join karne ke liye!")

# ----------------- Create Quiz -----------------
@bot.message_handler(func=lambda m: m.text == "➕ Create New Quiz" and m.chat.type == 'private')
def create_quiz(message):
    uid = message.from_user.id
    user_states[uid] = {
        "step": "title",
        "title": "",
        "description": "",
        "questions": [],
        "timer": 30,
        "shuffle": False
    }
    bot.send_message(message.chat.id, "Quiz ka Title bhejo:")

@bot.message_handler(func=lambda m: m.from_user.id in user_states and m.chat.type == 'private')
def handle_creation(message):
    uid = message.from_user.id
    state = user_states[uid]

    if state["step"] == "title":
        state["title"] = message.text.strip()
        state["step"] = "description"
        bot.send_message(message.chat.id, "Description bhejo (ya /skip kar do):")

    elif state["step"] == "description":
        if message.text.strip().lower() != '/skip':
            state["description"] = message.text.strip()
        state["step"] = "question"
        bot.send_message(message.chat.id, "Question bhejo:")

    elif state["step"] == "question":
        state["current_q"] = {"question": message.text.strip(), "options": []}
        state["step"] = "options"
        bot.send_message(message.chat.id, "4 options ek-ek karke bhejo (4 messages mein):")

    elif state["step"] == "options":
        state["current_q"]["options"].append(message.text.strip())
        if len(state["current_q"]["options"]) < 4:
            bot.send_message(message.chat.id, f"Option {len(state['current_q']['options'])}/4 saved. Agla option:")
        else:
            state["step"] = "correct"
            bot.send_message(message.chat.id, "Sahi jawab ka number bhejo (1-4):")

    elif state["step"] == "correct":
        try:
            correct = int(message.text.strip()) - 1
            if 0 <= correct < 4:
                state["current_q"]["correct"] = correct
                state["questions"].append(state["current_q"])
                del state["current_q"]
                show_quiz_menu(message.chat.id, uid)
            else:
                bot.send_message(message.chat.id, "1 se 4 tak number bhejo!")
        except:
            bot.send_message(message.chat.id, "Number hi bhejo (1-4)")

def show_quiz_menu(chat_id, uid):
    state = user_states[uid]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Aur Question Add Karo", callback_data="add_more"),
        types.InlineKeyboardButton("✅ Quiz Finish Karo", callback_data="finish_quiz")
    )
    markup.add(
        types.InlineKeyboardButton(f"⏱ Timer: {state['timer']}s", callback_data="set_timer"),
        types.InlineKeyboardButton(f"🔀 Shuffle: {'ON' if state['shuffle'] else 'OFF'}", callback_data="toggle_shuffle")
    )
    bot.send_message(chat_id, f"Question add ho gaya! ({len(state['questions'])} questions abhi tak)\nKya karna hai?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.from_user.id in user_states)
def creation_callback(call):
    uid = call.from_user.id
    state = user_states[uid]

    if call.data == "add_more":
        state["step"] = "question"
        bot.send_message(call.message.chat.id, "Agla question bhejo:")

    elif call.data == "set_timer":
        state["step"] = "timer"
        bot.send_message(call.message.chat.id, "Har question ke liye timer seconds mein bhejo (0 = no timer):")

    elif call.data == "toggle_shuffle":
        state["shuffle"] = not state["shuffle"]
        bot.answer_callback_query(call.id, f"Shuffle {'ON' if state['shuffle'] else 'OFF'}")
        show_quiz_menu(call.message.chat.id, uid)

    elif call.data == "finish_quiz":
        if len(state["questions"]) == 0:
            bot.send_message(call.message.chat.id, "Kam se kam 1 question toh add karo!")
            return

        if str(uid) not in quizzes:
            quizzes[str(uid)] = []

        quiz = {
            "title": state["title"],
            "description": state.get("description", ""),
            "questions": state["questions"],
            "timer": state["timer"],
            "shuffle": state["shuffle"]
        }
        quizzes[str(uid)].append(quiz)
        save_data()
        del user_states[uid]

        bot.send_message(call.message.chat.id, f"Quiz '{quiz['title']}' ban gaya! 🎉")
        show_user_quizzes(call.message.chat.id, uid)

# Timer step handle (separate)
@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("step") == "timer")
def set_timer(message):
    uid = message.from_user.id
    try:
        t = int(message.text.strip())
        user_states[uid]["timer"] = max(0, t)
        bot.send_message(message.chat.id, f"Timer set ho gaya: {t} seconds")
        show_quiz_menu(message.chat.id, uid)
        user_states[uid]["step"] = "menu"  # back
    except:
        bot.send_message(message.chat.id, "Number bhejo seconds mein!")

# ----------------- View Quizzes -----------------
@bot.message_handler(func=lambda m: m.text == "📋 View Quizzes" and m.chat.type == 'private')
def view_quizzes(message):
    show_user_quizzes(message.chat.id, message.from_user.id)

def show_user_quizzes(chat_id, uid):
    uid_str = str(uid)
    if uid_str not in quizzes or not quizzes[uid_str]:
        bot.send_message(chat_id, "Aapke paas abhi koi quiz nahi hai.")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, quiz in enumerate(quizzes[uid_str]):
        markup.add(types.InlineKeyboardButton(quiz["title"], callback_data=f"quiz_{uid}_{i}"))
    bot.send_message(chat_id, "Aapke quizzes:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("quiz_"))
def select_quiz(call):
    _, uid_str, i_str = call.data.split("_")
    uid = int(uid_str)
    i = int(i_str)
    quiz = quizzes[str(uid)][i]

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Group mein Start Karo", switch_inline_query_current_chat=f"{uid}_{i}"))
    bot.send_message(call.message.chat.id, f"**{quiz['title']}**\n{quiz.get('description', '')}\nQuestions: {len(quiz['questions'])}\nTimer: {quiz['timer']}s", reply_markup=markup, parse_mode='Markdown')

# ----------------- Group Play -----------------
@bot.message_handler(commands=['ready'])
def ready(message):
    if message.chat.type not in ['group', 'supergroup']:
        return

    group_id = message.chat.id
    if group_id not in active_games:
        active_games[group_id] = {
            "quiz": None,
            "players": {},
            "current_q": 0,
            "started": False
        }

    active_games[group_id]["players"][message.from_user.id] = 0
    bot.reply_to(message, f"{message.from_user.first_name} ready hai! ({len(active_games[group_id]['players'])} players abhi tak)")

@bot.message_handler(commands=['go'])
def start_quiz(message):
    if message.chat.type not in ['group', 'supergroup']:
        return

    group_id = message.chat.id
    if group_id not in active_games or active_games[group_id]["started"]:
        bot.send_message(group_id, "Quiz already chal raha hai ya nahi set hua.")
        return

    game = active_games[group_id]
    if len(game["players"]) < 2:
        bot.send_message(group_id, "Kam se kam 2 players chahiye!")
        return

    if not game["quiz"]:
        bot.send_message(group_id, "Quiz set nahi hua. Admin inline se quiz share kare.")
        return

    game["started"] = True
    bot.send_message(group_id, "Quiz shuru ho raha hai! 🔥 Good luck!")
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
        correct = options.index(q["options"][q["correct"]])

    sent_poll = bot.send_poll(
        chat_id=group_id,
        question=q["question"],
        options=options,
        type="quiz",
        correct_option_id=correct,
        is_anonymous=False,
        open_period=quiz["timer"] if quiz["timer"] > 0 else None
    )

    poll_to_info[sent_poll.poll.id] = {
        "group_id": group_id,
        "q_index": idx,
        "correct": correct
    }

    game["current_q"] += 1

# Poll Answer (live score update)
def on_poll_answer(poll_answer):
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
    if chosen is not None:
        if chosen == info["correct"]:
            game["players"][user_id] += 4
        else:
            game["players"][user_id] -= 1

bot.register_poll_answer_handler(on_poll_answer)

# Poll Update (timer end ya close pe results + next)
def on_poll_update(poll):
    poll_id = poll.id
    if poll_id not in poll_to_info:
        return

    info = poll_to_info[poll_id]
    group_id = info["group_id"]
    if group_id not in active_games:
        del poll_to_info[poll_id]
        return

    text = "Question khatam!\nResults:\n"
    for opt in poll.options:
        text += f"• {opt.text}: {opt.voter_count} votes\n"

    bot.send_message(group_id, text)

    send_next_question(group_id)
    del poll_to_info[poll_id]

bot.register_poll_handler(on_poll_update)

def show_leaderboard(group_id):
    game = active_games[group_id]
    sorted_players = sorted(game["players"].items(), key=lambda x: x[1], reverse=True)

    text = "🏆 Leaderboard 🏆\n\n"
    for rank, (uid, score) in enumerate(sorted_players, 1):
        try:
            member = bot.get_chat_member(group_id, uid)
            name = member.user.first_name
        except:
            name = f"User {uid}"
        text += f"{rank}. {name} — {score} points\n"

    bot.send_message(group_id, text)

# ----------------- Run -----------------
if __name__ == '__main__':
    print("Bot starting...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
