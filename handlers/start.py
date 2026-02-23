from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from keyboards.main_menu import main_menu

router = Router()

@router.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer("🏠 Main Menu", reply_markup=main_menu())

@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    await callback.message.edit_text("🏠 Main Menu")
    await callback.message.answer("Choose option:", reply_markup=main_menu())
