from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    kb = [
        [KeyboardButton(text="➕ Create Quiz")],
        [KeyboardButton(text="📚 View My Quizzes")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
