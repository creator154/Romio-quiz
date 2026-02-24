from aiogram.fsm.state import State, StatesGroup

class QuizBuilder(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_poll = State()
    editing_title = State()
    editing_description = State()
