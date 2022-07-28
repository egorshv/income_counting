from aiogram.dispatcher.filters.state import State, StatesGroup


class AddRecord(StatesGroup):
    income = State()
    tag = State()
    description = State()
    num = State()


class AddTag(StatesGroup):
    income = State()
    name = State()


class GetStat(StatesGroup):
    time = State()
    tag = State()


class GetPlot(StatesGroup):
    income = State()
    time = State()


class GetRecordsByTag(StatesGroup):
    tag = State()


class GetRecordsByTime(StatesGroup):
    time = State()
