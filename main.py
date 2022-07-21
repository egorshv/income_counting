import logging

from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import TOKEN
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from utils import AddTag, AddRecord
from db import DbDispatcher

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
data = DbDispatcher('data.db')
ADD_RECORD_FORM = {'income': 0, 'tag_id': 0, 'description': '', 'sum': 0, 'date': ''}
ADD_TAG_FORM = {'income': 0, 'name': ''}


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Some greeting text")


@dp.message_handler(commands=['help'])
async def help(message: types.Message):
    await message.answer("List of available functions")


@dp.message_handler(commands=['add_record'])
async def add_record(message: types.Message):
    await AddRecord.income.set()
    await message.answer('Доход или расход?')


@dp.message_handler(state=AddRecord.income)
async def get_income(message: types.Message):
    ADD_RECORD_FORM['income'] = int(message.text)
    await AddRecord.tag.set()
    await message.answer('Укажите категорию')


@dp.message_handler(state=AddRecord.tag)
async def get_tag(message: types.Message):
    ADD_RECORD_FORM['tag_id'] = message.text
    await AddRecord.description.set()
    await message.answer('Добавьте описание')


@dp.message_handler(state=AddRecord.description)
async def get_description(message: types.Message):
    ADD_RECORD_FORM['description'] = message.text
    await AddRecord.num.set()
    await message.answer('Введите сумму')


@dp.message_handler(state=AddRecord.num)
async def get_num(message: types.Message, state: FSMContext):
    ADD_RECORD_FORM['sum'] = int(message.text)
    await state.finish()
    await message.answer('Запись успешно добавлена')
    await message.answer(f'income: {ADD_RECORD_FORM["income"]}\n'
                         f'tag: {ADD_RECORD_FORM["tag_id"]}\n'
                         f'description: {ADD_RECORD_FORM["description"]}\n'
                         f'sum: {ADD_RECORD_FORM["sum"]}')
    tag_id = data.select_data({'name': ADD_RECORD_FORM['tag_id']}, 'tags', ['id'])[0][0]
    ADD_RECORD_FORM['tag_id'] = tag_id
    ADD_RECORD_FORM['date'] = str(datetime.now())
    data.write_data(ADD_RECORD_FORM, 'records')


@dp.message_handler(commands=['add_tag'])
async def add_tag(message: types.Message):
    await AddTag.income.set()
    await message.answer('Доход или расход?')


@dp.message_handler(state=AddTag.income)
async def get_income(message: types.Message):
    ADD_TAG_FORM['income'] = int(message.text)
    await AddTag.name.set()
    await message.answer('Введите название категории')


@dp.message_handler(state=AddTag.name)
async def get_name(message: types.Message, state: FSMContext):
    ADD_TAG_FORM['name'] = message.text
    await state.finish()
    await message.answer('Категория успешно добавлена')
    await message.answer(f'income: {ADD_TAG_FORM["income"]}\n'
                         f'name: {ADD_TAG_FORM["name"]}')
    data.write_data(ADD_TAG_FORM, 'tags')


async def shutdown(dispatcher: Dispatcher):
    data.close_connection()
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_shutdown=shutdown)
