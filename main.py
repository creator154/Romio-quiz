import telebot
from telebot import types
import random
import json
import os

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("BOT_TOKEN not set in environment variables!")

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "quizzes.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        quizzes = json.load(f)
else:
    quizzes = {}

active_games = {}       # group_id (int) → game dict
poll_to_info = {}       # poll_id → {'group_id':, 'q_index':, 'correct':}

user_states = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(quizzes, f, indent=2)

# Start
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type == 'private':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("➕ Create New Quiz", "📋 View Quizzes")
        bot.send_message(message.chat.id, "Welcome to NEET Quizer Bot 👑", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Quiz join karne ke liye /ready bol do!")

# Create Quiz (same as before, thoda clean kiya)
@bot.message_handler(func=lambda m: m.text == "➕ Create New Quiz" and m.chat.type == 'private')
def create_quiz(message):
    uid = message.from_user.id
    user_states[uid] = {"step": "title", "questions": [], "timer": 30, "shuffle": False}
    bot.send_message(message.chat.id, "Quiz Title bhejo:")

@bot.message_handler(func=lambda m: m.from_user.id in user_states)
def handle_creation(message):
    uid = message.from_user.id
    state = user_states[uid]

    if state["step"] == "title":
        state["title"] = message.text.strip()
        state["step"] = "description"
        bot.send_message(message.chat.id, "Description bhejo ya /skip:")

    elif state["step"] == "description":
        if message.text.strip() != '/skip':
            state["description"] = message.text.strip()
        state["step"] = "question"
        bot.send_message(message.chat.id, "Question bhejo:")

    elif state["step"] == "question":
        state["current_q"] = {"question": message.text.strip(), "options": []}
        state["step"] = "options"
        bot.send_message(message.chat.id, "4 options ek-ek karke bhejo:")

    elif state["step"] == "options":
        state["current_q"]["options"].append(message.text.strip())
        if len(state["current_q"]["options"]) < 4:
            bot.send_message(message.chat.id, f"Option {len(state['current_q']['options'])}/4")
        else:
            state["step"] = "correct"
            bot.send_message(message.chat.id, "Correct option number (1-4):")

    elif state["step"] == "correct":
        try:
            correct = int(message.text.strip()) - 1
            if 0 <= correct < 4:
                state["current_q"]["correct"] = correct
                state["questions"].append(state["current_q"])
                del state["current_q"]
                show_quiz_menu(message.chat.id, uid)
            else:
                bot.send_message(message.chat.id, "1-4 ke beech number bhejo")
        except:
            bot.send_message(message.chat.id, "Number bhejo")

def show_quiz_menu(chat_id, uid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add More", callback_data="add_more"),
        types.InlineKeyboardButton("✅ Finish", callback_data="finish_quiz")
    )
    markup.add(
        types.InlineKeyboardButton("⏱ Timer", callback_data="set_timer"),
        types.InlineKeyboardButton("🔀 Shuffle", callback_data="toggle_shuffle")
    )
    bot.send_message(chat_id, "Question added! Next?", reply_markup=markup)

# Callback handlers for creation (same, thoda short)
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id
    if uid not in user_states:
        return

    state = user_states[uid]

    if call.data == "add_more":
        state["step"] = "question"
        bot.send_message(call.message.chat.id, "Next question:")

    elif call.data == "set_timer":
        bot.send_message(call.message.chat.id, "Timer seconds (0 = none):")
        state["step"] = "timer"

    elif call.data == "toggle_shuffle":
        state["shuffle"] = not state["shuffle"]
        bot.answer_callback_query(call.id, f"Shuffle {'ON' if state['shuffle'] else 'OFF'}")
        show_quiz_menu(call.message.chat.id, uid)

    elif call.data == "finish_quiz":
        if not state["questions"]:
            bot.send_message(call.message.chat.id, "At least 1 question add karo!")
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
        bot.send_message(call.message.chat.id, f"Quiz saved: {quiz['title']}")
        # View quizzes call kar sakte ho

# Poll handlers - DECORATOR STYLE (crash fix)
@bot.poll_answer_handler()
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

@bot.poll_handler()
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
        text += f"• {opt.text}: {opt.voter_count}\n"
    bot.send_message(group_id, text)

    send_next_question(group_id)
    del poll_to_info[poll_id]

# Rest of the code (send_next_question, leaderboard, etc.) same as before
# ... (copy from previous version)

if __name__ == '__main__':
    print("Bot starting...")
    bot.infinity_polling(timeout=20)
