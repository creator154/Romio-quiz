from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from keyboards.main_menu import main_menu

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "👋 Welcome to Quiz Bot\n\nSelect an option:",
        reply_markup=main_menu()
    )
