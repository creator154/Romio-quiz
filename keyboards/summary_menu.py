from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def summary_menu(quiz_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶ Start Quiz", callback_data=f"start_{quiz_id}")],
        [InlineKeyboardButton(text="✏ Edit", callback_data=f"edit_{quiz_id}")],
        [InlineKeyboardButton(text="📊 Stats", callback_data=f"stats_{quiz_id}")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_main")]
    ])
