from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def question_keyboard():
    kb = [
        [KeyboardButton(text="➕ Add Question")],
        [KeyboardButton(text="/done"), KeyboardButton(text="/undo")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def poll_instruction_keyboard():
    kb = [
        [KeyboardButton(text="/done"), KeyboardButton(text="/undo")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
