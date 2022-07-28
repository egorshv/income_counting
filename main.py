import logging

from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text

from config import TOKEN
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from utils import AddTag, AddRecord, GetStat, GetPlot
from db import DbDispatcher
from stats import get_stat, get_plot

logging.basicConfig(level=logging.INFO)

# state.update_data(some_name=message.text.lower())
# Таким способом можно переписать сохранение данных и избавиться от словарей


# Регистрация команд, отображаемых в интерфейсе Telegram
# async def set_commands(bot: Bot):
#     commands = [
#         BotCommand(command="/drinks", description="Заказать напитки"),
#         BotCommand(command="/food", description="Заказать блюда"),
#         BotCommand(command="/cancel", description="Отменить текущее действие")
#     ]
#     await bot.set_my_commands(commands)

# В if main ... : await set_commands(bot)


bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
data = DbDispatcher('data.db')
ADD_RECORD_FORM = {'income': 0, 'tag_id': 0, 'description': '', 'sum': 0, 'date': ''}
ADD_TAG_FORM = {'income': 0, 'name': ''}
STATS_FORM = {'time': '', 'tag': ''}
GET_PLOT_FORM = {'time': '', 'income': 0}
keyboard1 = ReplyKeyboardMarkup(resize_keyboard=True)
keyboard1.add(KeyboardButton('Доход'))
keyboard1.add(KeyboardButton('Расход'))
time_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
lst = ['день', 'неделя', 'месяц', 'год']
for item in lst:
    time_keyboard.add(KeyboardButton(item))


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer('Привет, это бот для учёта доходов/расходов.\n'
                         '/help - чтобы посмотреть все функции')


@dp.message_handler(commands=['help'])
async def help(message: types.Message):
    await message.answer('/add_record - добавить новую запись\n'
                         '/add_tag - добавить новую категорию\n'
                         '/stats - получить статистику\n'
                         '/get_plot - получить круговую диаграмму\n'
                         '/cancel - прервать запись\n'
                         '/get_records_by_tag - получить все записи по опр. категории\n'
                         '/get_records_by_time - получить все записи за опр. период времени')


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Отменено', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(commands=['stats'])
async def get_stats(message: types.Message):
    await GetStat.time.set()
    await message.answer('Выберете временной период', reply_markup=time_keyboard)


@dp.message_handler(state=GetStat.time)
async def get_time(message: types.Message):
    if message.text not in lst:
        await message.answer('Неверный временной период, попробуйте ещё раз.')
        # await GetStat.time.set()
        return
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
        # await GetStat.tag.set()
        return
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
        # await AddRecord.income.set()
        return
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
        # await AddRecord.tag.set()
        return
    await AddRecord.description.set()
    await message.answer('Добавьте описание', reply_markup=ReplyKeyboardRemove())


@dp.message_handler(state=AddRecord.description)
async def get_description(message: types.Message):
    if message.text.isdigit():
        await message.answer('Описание не должно быть числом')
        # await AddRecord.description.set()
        return
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
        # await AddRecord.num.set()
        return


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
        # await AddTag.income.set()
        return
    await AddTag.name.set()
    await message.answer('Введите название категории', reply_markup=ReplyKeyboardRemove())


@dp.message_handler(state=AddTag.name)
async def get_name(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await message.answer('Имя не может быть числом')
        # await AddTag.name.set()
        return
    else:
        ADD_TAG_FORM['name'] = message.text
        await state.finish()
        await message.answer('Категория успешно добавлена')
        await message.answer(f'income: {ADD_TAG_FORM["income"]}\n'
                             f'name: {ADD_TAG_FORM["name"]}')
        data.write_data(ADD_TAG_FORM, 'tags')


@dp.message_handler(commands=['get_plot'])
async def get_plt(message: types.Message):
    await message.answer('Доход или расход?', reply_markup=keyboard1)
    await GetPlot.income.set()


@dp.message_handler(state=GetPlot.income)
async def get_inc(message: types.Message):
    if message.text == 'Доход':
        GET_PLOT_FORM['income'] = 1
    elif message.text == 'Расход':
        GET_PLOT_FORM['income'] = 0
    else:
        await message.answer('Неверный формат ввода, попробуйте ещё раз\n'
                             '/break_record - чтобы прервать запись')
        # await GetPlot.income.set()
        return
    await message.answer('Выберете временной период', reply_markup=time_keyboard)
    await GetPlot.time.set()


@dp.message_handler(state=GetPlot.time)
async def get_tm(message: types.Message, state: FSMContext):
    if message.text not in lst:
        await message.answer('Неверный временной период, попробуйте ещё раз.')
        # await GetPlot.time.set()
        return
    else:
        GET_PLOT_FORM['time'] = message.text
        get_plot('plot1.png', GET_PLOT_FORM['time'], GET_PLOT_FORM['income'])
        chat_id = message.chat.id
        await bot.send_photo(chat_id=chat_id, photo=open('plot1.png', 'rb'), reply_markup=ReplyKeyboardRemove())
        await state.finish()


async def shutdown(dispatcher: Dispatcher):
    data.close_connection()
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_shutdown=shutdown)
