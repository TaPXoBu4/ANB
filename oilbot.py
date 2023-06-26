import asyncio
import sqlite3 as sq
import datetime

import config
import variables

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram_calendar import simple_cal_callback, SimpleCalendar

from config import Token, GroupID, _logger
from funcs import reg_reading, check_alarms, levels_info, build_plot, users_parser, save_user

# Создание экземпляров бота, планировщика, БД
bot = Bot(token=Token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
scheduler = AsyncIOScheduler()

with sq.connect('ANB_DB.db', detect_types=sq.PARSE_DECLTYPES | sq.PARSE_COLNAMES) as con:
    cur = con.cursor()
    create_connection_table = """CREATE TABLE IF NOT EXISTS connection (
        cnd_id INTEGER PRIMARY KEY AUTOINCREMENT,
        cnd INTEGER,
        dttm TIMESTAMP)"""
    create_id_store = 'CREATE TABLE IF NOT EXISTS users (user_id INTEGER, username TEXT UNIQUE)'
    cur.execute(create_connection_table)
    cur.execute(create_id_store)

variables.users_store = users_parser()


# Состояния для автомата состояний
class Access(StatesGroup):
    verification = State()
    username = State()


# Кнопки
keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
buttons = ['Данные', 'График']
keyboard.add(*buttons)
subkeyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
subbuttons = ['Дата', 'Сутки']
subkeyboard.add(*subbuttons)


# Начало автомата состояний верификации и регистрации
@dp.message_handler(lambda message: message.from_user.id not in list(variables.users_store.keys()))
async def anything_without_access(message: types.Message):
    await Access.verification.set()
    await message.reply('Привет, новенький! А введи-ка ты пароль!')


@dp.message_handler(lambda message: message.from_user.id not in list(variables.users_store.keys()),
                    commands=['start'], state='*')
async def start_without_access(message: types.Message, state: FSMContext):
    await state.finish()
    await Access.verification.set()
    await message.reply('Привет, новенький! А введи-ка ты пароль!')

@dp.message_handler(lambda message: message.from_user.id in list(variables.users_store.keys()), commands=['start'])
async def cmd_start_with_access(message: types.Message):
    await message.reply('И снова здравстсвуйте!', reply_markup=keyboard)


@dp.message_handler(lambda message: message.text != config.password, state=Access.verification)
async def wrong_password(message: types.Message):
    await message.answer('Неправильно, попробуйте еще раз.')


@dp.message_handler(lambda message: message.text == config.password, state=Access.verification)
async def right_password(message: types.Message):
    await Access.next()
    await message.reply('Введите свое имя. Оно должно быть уникальным.')


@dp.message_handler(lambda message: message.text in list(variables.users_store.values()), state=Access.username)
async def ununique_username(message: types.Message):
    await message.reply('Такое имя уже есть в базе.')


@dp.message_handler(lambda message: message.text not in list(variables.users_store.values()), state=Access.username)
async def unique_username(message: types.Message, state: FSMContext):
    save_user(message.from_user.id, message.text)
    await message.answer('Отлично! Вот вам кнопки.', reply_markup=keyboard)
    await state.finish()


# Конец автомата состояний верификации и регистрации

@dp.message_handler(Text(equals='Данные'))
async def reply_data(message: types.Message):
    """Обработчик кнопки 'Данные'"""
    await message.reply(text=levels_info())


@dp.message_handler(Text(equals=['График'], ignore_case=True))
async def plot_request(message: types.Message):
    await message.answer('За какой период?', reply_markup=subkeyboard)


@dp.message_handler(Text(equals=['Дата'], ignore_case=True))
async def take_calendar(message: types.Message):
    await message.answer('Выберите дату', reply_markup=await SimpleCalendar().start_calendar())


@dp.message_handler(Text(equals=['Сутки'], ignore_case=True))
async def echo(message: types.Message):
    date = datetime.datetime.now()
    txt, filename = build_plot(date)
    await message.answer(txt, reply_markup=keyboard)
    if filename:
        photo = types.InputFile(filename)
        await message.answer_photo(photo, reply_markup=keyboard)


@dp.callback_query_handler(simple_cal_callback.filter())
async def process_simple_calendar(callback_query: types.CallbackQuery, callback_data: dict):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if selected:
        txt, filename = build_plot(date)
        await callback_query.message.answer(txt, reply_markup=keyboard)
        if filename:
            photo = types.InputFile(filename)
            await callback_query.message.answer_photo(photo=photo, reply_markup=keyboard)


@dp.message_handler(commands=['userid'])
async def get_user_id(message: types.Message):
    _logger.info('### Запрошен ID пользователя')
    await message.reply(message.from_user.id)


@dp.message_handler(commands=['showid'])
async def get_chat_id(message: types.Message):
    """Получаем ID группы"""
    _logger.info('### Был запрошен ID группы')
    await message.reply(message.chat.id)


@dp.message_handler()
async def echo(message: types.Message):
    """Ответ на любое сообщение"""
    await message.answer(
        text='Нажми на "/start"', reply_markup=keyboard
    )


async def morning_report():
    """Функция для отправки сообщений по расписанию"""
    txt = levels_info()
    await bot.send_message(chat_id=GroupID, text=txt)


async def alarms_monitoring():
    """Мониторинг уровней и насосов"""
    await asyncio.sleep(3)
    _logger.info('### Старт мониторинга событий...')
    while True:
        txt = check_alarms()
        if txt:
            await bot.send_message(chat_id=GroupID, text=txt)
        await asyncio.sleep(2)


# Добавляем функцию рассылки в планировщик
scheduler.add_job(morning_report, 'cron', day_of_week='mon-sun',
                  hour=9, minute=0)


# Добавление  задач в рабочий цикл бота
async def on_startup(_):
    scheduler.start()  # рассылка по расписанию
    asyncio.create_task(reg_reading())  # Опрос ПР
    asyncio.create_task(alarms_monitoring())  # Мониторинг событий


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)  # Запуск непосредственно бота
