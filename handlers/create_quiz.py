from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from utils.states import CreateQuiz
from keyboards.quiz_builder import question_keyboard, poll_instruction_keyboard
from database.mongo import quizzes_collection
from keyboards.main_menu import main_menu

router = Router()

@router.message(F.text == "➕ Create Quiz")
async def create_quiz_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CreateQuiz.waiting_for_title)
    await message.answer("📝 Send Quiz Title")

@router.message(CreateQuiz.waiting_for_title)
async def get_title(message: Message, state: FSMContext):
    await state.update_data(
        title=message.text,
        description="",
        questions=[]
    )
    await state.set_state(CreateQuiz.waiting_for_description)
    await message.answer("📄 Send Description or type /skip")

@router.message(CreateQuiz.waiting_for_description)
async def get_description(message: Message, state: FSMContext):
    if message.text.lower() != "/skip":
        await state.update_data(description=message.text)

    await state.set_state(CreateQuiz.waiting_for_question)
    await message.answer(
        "Now add questions 👇",
        reply_markup=question_keyboard()
    )

@router.message(F.text == "➕ Add Question")
async def add_question_instruction(message: Message):
    await message.answer(
        "Send a Telegram Quiz Poll now.\n"
        "Must be anonymous=False and type=quiz",
        reply_markup=poll_instruction_keyboard()
    )

@router.message(F.poll)
async def receive_poll(message: Message, state: FSMContext):
    if message.poll.type != "quiz":
        return await message.answer("❌ Send Quiz type poll only")

    data = await state.get_data()
    questions = data.get("questions", [])

    questions.append({
        "question": message.poll.question,
        "options": message.poll.options,
        "correct_option_id": message.poll.correct_option_id
    })

    await state.update_data(questions=questions)

    await message.answer(
        f"✅ Question Added\nTotal: {len(questions)}",
        reply_markup=question_keyboard()
    )

@router.message(F.text == "/undo")
async def undo_question(message: Message, state: FSMContext):
    data = await state.get_data()
    questions = data.get("questions", [])

    if not questions:
        return await message.answer("No questions to remove.")

    questions.pop()
    await state.update_data(questions=questions)

    await message.answer(
        f"❌ Last question removed\nRemaining: {len(questions)}",
        reply_markup=question_keyboard()
    )

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
        "questions": questions
    }

    await quizzes_collection.insert_one(quiz_data)

    summary = (
        f"✅ Quiz Created Successfully!\n\n"
        f"Title: {data['title']}\n"
        f"Description: {data['description']}\n"
        f"Questions: {len(questions)}"
    )

    await message.answer(summary, reply_markup=main_menu())
    await state.clear()
