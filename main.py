import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from config import TOKEN
from db import DbDispatcher
from stats import get_stat, get_plot
from utils import AddTag, AddRecord, GetStat, GetPlot, GetRecordsByTag, GetRecordsByTime

logging.basicConfig(level=logging.INFO)

# TODO: get total sum by tag

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
data = DbDispatcher('data.db')
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
async def get_time(message: types.Message, state: FSMContext):
    if message.text not in lst:
        await message.answer('Неверный временной период, попробуйте ещё раз.')
        return
    else:
        await state.update_data(time=message.text)
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
        return
    else:
        async with state.proxy() as d:
            stats = get_stat(d['time'], message.text)
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
async def get_income(message: types.Message, state: FSMContext):
    if message.text == 'Доход':
        await state.update_data(income=1)
    elif message.text == 'Расход':
        await state.update_data(income=0)
    else:
        await message.answer('Неверный формат ввода, попробуйте ещё раз\n'
                             '/cancel - чтобы прервать запись')
        return
    keyboard2 = ReplyKeyboardMarkup(resize_keyboard=True)
    async with state.proxy() as d:
        tags = data.select_data({'income': d['income']}, 'tags', ['name'])
    for tag in tags:
        keyboard2.add(KeyboardButton(tag[0]))
    await AddRecord.tag.set()
    await message.answer('Укажите категорию', reply_markup=keyboard2)


@dp.message_handler(state=AddRecord.tag)
async def get_tag(message: types.Message, state: FSMContext):
    async with state.proxy() as d:
        tags = [item[0] for item in data.select_data({'income': d['income']}, 'tags', ['name'])]
    if message.text in tags:
        await state.update_data(tag_id=message.text)
    else:
        await message.answer('Такого тега не существует.\n'
                             '/add_tag - чтобы добавить тег\n'
                             '/cancel - чтобы прервать запись')
        return
    await AddRecord.description.set()
    await message.answer('Добавьте описание', reply_markup=ReplyKeyboardRemove())


@dp.message_handler(state=AddRecord.description)
async def get_description(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await message.answer('Описание не должно быть числом')
        return
    else:
        await state.update_data(description=message.text)
        await AddRecord.num.set()
        await message.answer('Введите сумму')


@dp.message_handler(state=AddRecord.num)
async def get_num(message: types.Message, state: FSMContext):
    try:
        await state.update_data(sum=int(message.text))
        async with state.proxy() as d:
            dct = dict(d)
        dct['description'] = dct['description'].replace('\'', '_')
        await message.answer('Запись успешно добавлена')
        await message.answer(f'income: {dct["income"]}\n'
                             f'tag: {dct["tag_id"]}\n'
                             f'description: {dct["description"]}\n'
                             f'sum: {dct["sum"]}')
        tag_id = data.select_data({'name': dct['tag_id']}, 'tags', ['id'])[0][0]
        dct['tag_id'] = tag_id
        dct['date'] = str(datetime.now())
        data.write_data(dct, 'records')
        await state.finish()
    except ValueError:
        await message.answer('Необходимо ввести число')
        return


@dp.message_handler(commands=['add_tag'])
async def add_tag(message: types.Message):
    await AddTag.income.set()
    await message.answer('Доход или расход?', reply_markup=keyboard1)


@dp.message_handler(state=AddTag.income)
async def get_income(message: types.Message, state: FSMContext):
    if message.text == 'Доход':
        await state.update_data(income=1)
    elif message.text == 'Расход':
        await state.update_data(income=0)
    else:
        await message.answer('Неверный формат ввода, попробуйте ещё раз\n'
                             '/cancel - чтобы прервать запись')
        return
    await AddTag.name.set()
    await message.answer('Введите название категории', reply_markup=ReplyKeyboardRemove())


@dp.message_handler(state=AddTag.name)
async def get_name(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await message.answer('Имя не может быть числом')
        return
    else:
        await state.update_data(name=message.text)
        async with state.proxy() as d:
            dct = dict(d)
        await message.answer('Категория успешно добавлена')
        await message.answer(f'income: {dct["income"]}\n'
                             f'name: {dct["name"]}')
        data.write_data(dct, 'tags')
        await state.finish()


@dp.message_handler(commands=['get_plot'])
async def get_plt(message: types.Message):
    await message.answer('Доход или расход?', reply_markup=keyboard1)
    await GetPlot.income.set()


@dp.message_handler(state=GetPlot.income)
async def get_inc(message: types.Message, state: FSMContext):
    if message.text == 'Доход':
        await state.update_data(income=1)
    elif message.text == 'Расход':
        await state.update_data(income=0)
    else:
        await message.answer('Неверный формат ввода, попробуйте ещё раз\n'
                             '/cancel - чтобы прервать запись')
        return
    await message.answer('Выберете временной период', reply_markup=time_keyboard)
    await GetPlot.time.set()


@dp.message_handler(state=GetPlot.time)
async def get_tm(message: types.Message, state: FSMContext):
    if message.text not in lst:
        await message.answer('Неверный временной период, попробуйте ещё раз.')
        return
    else:
        await state.update_data(time=message.text)
        async with state.proxy() as d:
            get_plot('plot1.png', d['time'], d['income'])
        chat_id = message.chat.id
        await bot.send_photo(chat_id=chat_id, photo=open('plot1.png', 'rb'), reply_markup=ReplyKeyboardRemove())
        await state.finish()


@dp.message_handler(commands=['get_records_by_tag'])
async def get_records_by_tag(message: types.Message):
    tags = data.select_data({}, 'tags', ['name'])
    tag_keyboard = ReplyKeyboardMarkup()
    for tag in tags:
        tag_keyboard.add(KeyboardButton(tag[0]))
    await GetRecordsByTag.tag.set()
    await message.answer('Введите необходимый тег', reply_markup=tag_keyboard)


@dp.message_handler(state=GetRecordsByTag.tag)
async def gt_tag(message: types.Message, state: FSMContext):
    tags = [item[0] for item in data.select_data({}, 'tags', ['name'])]
    if message.text in tags:
        await state.update_data(tag=message.text)
        async with state.proxy() as d:
            tag_id = data.select_data({'name': d['tag']}, 'tags', ['id'])[0][0]
        records = data.select_data({'tag_id': tag_id}, 'records', ['description', 'date', 'sum'])
        res = []
        for record in records:
            res.append(f'{record[1]} : {record[0]} : {record[2]}')
        await message.answer('\n'.join(res), reply_markup=ReplyKeyboardRemove())
        await state.finish()
    else:
        await message.answer('Такого тега не существует.\n'
                             '/add_tag - чтобы добавить тег\n'
                             '/cancel - чтобы прервать запись')
        return


@dp.message_handler(commands=['get_records_by_time'])
async def get_records_by_time(message: types.Message):
    await GetRecordsByTime.time.set()
    await message.answer('Выберете временной период', reply_markup=time_keyboard)


@dp.message_handler(state=GetRecordsByTime.time)
async def gt_time(message: types.Message, state: FSMContext):
    if message.text in lst:
        await state.update_data(time=message.text)
        async with state.proxy() as dct:
            time = dct['time']
        all_data = data.select_data({}, 'records', ['description', 'date', 'sum'])
        d = {'день': 2, 'неделя': 2, 'месяц': 1, 'год': 0}
        k = d[time]
        n = 1
        now = str(datetime.now()).split('-')
        now[2] = now[2].split()[0]
        now = now[k]
        if time == 'неделя':
            n = 7
        result = []
        for item in all_data:
            time_data = item[1].split('-')
            time_data[2] = time_data[2].split()[0]
            time_data = time_data[k]
            if int(now) - int(time_data) <= n:
                result.append(item)
        res = []
        for record in result:
            res.append(f'{record[1]} : {record[0]} : {record[2]}')
        if len(res) > 0:
            await message.answer('\n'.join(res), reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer('За указанный период записи не найдены')
        await state.finish()
    else:
        await message.answer('Неверный временной период, попробуйте ещё раз.')
        return


async def shutdown(dispatcher: Dispatcher):
    data.close_connection()
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_shutdown=shutdown)
