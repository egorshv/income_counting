from aiogram.dispatcher.filters.state import State, StatesGroup


class AddRecord(StatesGroup):
    income = State()
    tag = State()
    description = State()
    num = State()


class AddTag(StatesGroup):
    income = State()
    name = State()
