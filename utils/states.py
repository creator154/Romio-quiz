from aiogram.fsm.state import State, StatesGroup

class CreateQuiz(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_question = State()
    waiting_for_poll = State()
