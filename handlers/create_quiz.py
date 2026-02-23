from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bson import ObjectId

from database.mongo import quizzes_collection
from keyboards.main_menu import main_menu
from keyboards.summary_menu import summary_menu
from keyboards.edit_menu import edit_menu
from utils.states import QuizBuilder

router = Router()

# START CREATE
@router.message(F.text == "➕ Create Quiz")
async def create_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(QuizBuilder.waiting_title)
    await message.answer("📝 Send Quiz Title")

# TITLE
@router.message(QuizBuilder.waiting_title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(
        title=message.text,
        description="",
        questions=[]
    )
    await state.set_state(QuizBuilder.waiting_description)
    await message.answer("📄 Send Description or type /skip")

# DESCRIPTION
@router.message(QuizBuilder.waiting_description)
async def set_description(message: Message, state: FSMContext):
    if message.text.lower() != "/skip":
        await state.update_data(description=message.text)

    await state.set_state(QuizBuilder.waiting_poll)
    await message.answer(
        "Now send a Quiz type Poll (not regular poll)\n"
        "Anonymous must be OFF."
    )

# RECEIVE POLL
@router.message(F.poll)
async def receive_poll(message: Message, state: FSMContext):
    if message.poll.type != "quiz":
        return await message.answer("❌ Send Quiz type poll only")

    data = await state.get_data()
    questions = data.get("questions", [])

    questions.append({
        "question": message.poll.question,
        "options": [o.text for o in message.poll.options],
        "correct_option_id": message.poll.correct_option_id
    })

    await state.update_data(questions=questions)

    await message.answer(
        f"✅ Question Added ({len(questions)})\n"
        "Send another poll or type /done\n"
        "Type /undo to remove last."
    )

# UNDO
@router.message(F.text == "/undo")
async def undo_question(message: Message, state: FSMContext):
    data = await state.get_data()
    questions = data.get("questions", [])

    if not questions:
        return await message.answer("No questions to remove.")

    questions.pop()
    await state.update_data(questions=questions)

    await message.answer(f"❌ Removed. Total: {len(questions)}")

# DONE
@router.message(F.text == "/done")
async def finish_quiz(message: Message, state: FSMContext):
    data = await state.get_data()
    questions = data.get("questions", [])

    if not questions:
        return await message.answer("❌ Add at least 1 question.")

    quiz_data = {
        "user_id": message.from_user.id,
        "title": data["title"],
        "description": data["description"],
        "questions": questions,
        "timer": 30,
        "shuffle": False,
        "negative": 0.0
    }

    result = await quizzes_collection.insert_one(quiz_data)
    quiz_id = str(result.inserted_id)

    text = (
        f"📘 {data['title']}\n\n"
        f"{data['description']}\n\n"
        f"Questions: {len(questions)}\n"
        f"Timer: 30 sec\n"
        f"Shuffle: ❌\n"
        f"Negative: 0"
    )

    await message.answer(text, reply_markup=summary_menu(quiz_id))
    await state.clear()

# OPEN EDIT MENU
@router.callback_query(F.data.startswith("edit_"))
async def open_edit(callback: CallbackQuery):
    quiz_id = callback.data.split("_")[1]
    await callback.message.edit_reply_markup(reply_markup=edit_menu(quiz_id))

# BACK TO SUMMARY
@router.callback_query(F.data.startswith("back_summary_"))
async def back_summary(callback: CallbackQuery):
    quiz_id = callback.data.split("_")[2]
    quiz = await quizzes_collection.find_one({"_id": ObjectId(quiz_id)})

    text = (
        f"📘 {quiz['title']}\n\n"
        f"{quiz['description']}\n\n"
        f"Questions: {len(quiz['questions'])}\n"
        f"Timer: {quiz['timer']} sec\n"
        f"Shuffle: {'✅' if quiz['shuffle'] else '❌'}\n"
        f"Negative: {quiz['negative']}"
    )

    await callback.message.edit_text(text, reply_markup=summary_menu(quiz_id))
