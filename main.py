import logging

from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import TOKEN
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from utils import AddTag, AddRecord, GetStat
from db import DbDispatcher
from stats import get_stat

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
data = DbDispatcher('data.db')
ADD_RECORD_FORM = {'income': 0, 'tag_id': 0, 'description': '', 'sum': 0, 'date': ''}
ADD_TAG_FORM = {'income': 0, 'name': ''}
STATS_FORM = {'time': '', 'tag': ''}
keyboard1 = ReplyKeyboardMarkup(resize_keyboard=True)
keyboard1.add(KeyboardButton('Доход'))
keyboard1.add(KeyboardButton('Расход'))
time_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
lst = ['день', 'неделя', 'месяц', 'год']
for item in lst:
    time_keyboard.add(KeyboardButton(item))


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Some greeting text")


@dp.message_handler(commands=['help'])
async def help(message: types.Message):
    await message.answer("List of available functions")


@dp.message_handler(commands=['stats'])
async def get_stats(message: types.Message):
    pattern = 'Total incoming: {}\n' \
              'Tag1 incoming: {}\n' \
              '...\n' \
              'TagN incoming: {}\n' \
              'Total spending: {}\n' \
              'Tag1 spending: {}\n' \
              '...\n' \
              'TagN spending: {}\n'
    # Also need to get stats per some time period
    await GetStat.time.set()
    await message.answer('Выберете временной период', reply_markup=time_keyboard)


@dp.message_handler(state=GetStat.time)
async def get_time(message: types.Message):
    if message.text not in lst:
        await message.answer('Неверный временной период, попробуйте ещё раз.')
        await GetStat.time.set()
    else:
        STATS_FORM['time'] = message.text
        tags_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        tags = data.select_data({}, 'tags', ['name'])
        for tag in tags:
            tags_keyboard.add(KeyboardButton(tag[0]))
        await GetStat.tag.set()
        await message.answer('Введите тег, по которому нужна статистика', reply_markup=tags_keyboard)


@dp.message_handler(state=GetStat.tag)
async def get_tag(message: types.Message, state: FSMContext):
    tags = [item[0] for item in data.select_data({}, 'tags', ['name'])]
    if message.text not in tags:
        await message.answer('Такого тега нет')
        await GetStat.tag.set()
    else:
        stats = get_stat(STATS_FORM['time'], message.text)
        pattern = '{} : {} : {}'
        line = []
        for record in stats[0]:
            line.append(pattern.format(record[0].split()[0], record[2], record[1]))
        line.append(f'Общая сумма: {stats[1]}')
        await state.finish()
        await message.answer('\n'.join(line), reply_markup=ReplyKeyboardRemove())


@dp.message_handler(commands=['add_record'])
async def add_record(message: types.Message):
    await AddRecord.income.set()
    await message.answer('Доход или расход?', reply_markup=keyboard1)


@dp.message_handler(state=AddRecord.income)
async def get_income(message: types.Message):
    if message.text == 'Доход':
        ADD_RECORD_FORM['income'] = 1
    elif message.text == 'Расход':
        ADD_RECORD_FORM['income'] = 0
    else:
        await message.answer('Неверный формат ввода, попробуйте ещё раз\n'
                             '/break_record - чтобы прервать запись')
        await AddRecord.income.set()
    keyboard2 = ReplyKeyboardMarkup(resize_keyboard=True)
    tags = data.select_data({'income': ADD_RECORD_FORM['income']}, 'tags', ['name'])
    for tag in tags:
        keyboard2.add(KeyboardButton(tag[0]))
    await AddRecord.tag.set()
    await message.answer('Укажите категорию', reply_markup=keyboard2)


@dp.message_handler(state=AddRecord.tag)
async def get_tag(message: types.Message):
    tags = [item[0] for item in data.select_data({'income': ADD_RECORD_FORM['income']}, 'tags', ['name'])]
    if message.text in tags:
        ADD_RECORD_FORM['tag_id'] = message.text
    else:
        await message.answer('Такого тега не существует.\n'
                             '/add_tag - чтобы добавить тег\n'
                             '/break_record - чтобы прервать запись')
        await AddRecord.tag.set()
    await AddRecord.description.set()
    await message.answer('Добавьте описание', reply_markup=ReplyKeyboardRemove())


@dp.message_handler(state=AddRecord.description)
async def get_description(message: types.Message):
    if message.text.isdigit():
        await message.answer('Описание не должно быть числом')
        await AddRecord.description.set()
    else:
        ADD_RECORD_FORM['description'] = message.text
        await AddRecord.num.set()
        await message.answer('Введите сумму')


@dp.message_handler(state=AddRecord.num)
async def get_num(message: types.Message, state: FSMContext):
    try:
        ADD_RECORD_FORM['sum'] = int(message.text)
        ADD_RECORD_FORM['description'] = ADD_RECORD_FORM['description'].replace('\'', '_')
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
    except ValueError:
        await message.answer('Необходимо ввести число')
        await AddRecord.num.set()


@dp.message_handler(commands=['add_tag'])
async def add_tag(message: types.Message):
    await AddTag.income.set()
    await message.answer('Доход или расход?', reply_markup=keyboard1)


@dp.message_handler(state=AddTag.income)
async def get_income(message: types.Message):
    if message.text == 'Доход':
        ADD_TAG_FORM['income'] = 1
    elif message.text == 'Расход':
        ADD_TAG_FORM['income'] = 0
    else:
        await message.answer('Неверный формат ввода, попробуйте ещё раз\n'
                             '/break_record - чтобы прервать запись')
        await AddTag.income.set()
    await AddTag.name.set()
    await message.answer('Введите название категории', reply_markup=ReplyKeyboardRemove())


@dp.message_handler(state=AddTag.name)
async def get_name(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await message.answer('Имя не может быть числом')
        await AddTag.name.set()
    else:
        ADD_TAG_FORM['name'] = message.text
        await state.finish()
        await message.answer('Категория успешно добавлена')
        await message.answer(f'income: {ADD_TAG_FORM["income"]}\n'
                             f'name: {ADD_TAG_FORM["name"]}')
        data.write_data(ADD_TAG_FORM, 'tags')


@dp.message_handler(commands=['/break_record'])
async def break_record(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer('Запись прервана')


async def shutdown(dispatcher: Dispatcher):
    data.close_connection()
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_shutdown=shutdown)
