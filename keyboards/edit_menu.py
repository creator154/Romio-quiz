from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def edit_menu(quiz_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏ Edit Title", callback_data=f"edit_title_{quiz_id}")],
        [InlineKeyboardButton(text="📝 Edit Description", callback_data=f"edit_desc_{quiz_id}")],
        [InlineKeyboardButton(text="⏱ Timer 30s", callback_data=f"edit_timer_{quiz_id}")],
        [InlineKeyboardButton(text="🔀 Toggle Shuffle", callback_data=f"edit_shuffle_{quiz_id}")],
        [InlineKeyboardButton(text="➖ Negative 0.0", callback_data=f"edit_negative_{quiz_id}")],
        [InlineKeyboardButton(text="🔙 Back", callback_data=f"back_summary_{quiz_id}")]
    ])
