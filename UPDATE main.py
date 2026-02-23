import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import start, create_quiz, view_quiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start.router)
dp.include_router(create_quiz.router)
dp.include_router(view_quiz.router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
