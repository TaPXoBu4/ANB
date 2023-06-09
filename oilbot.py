import asyncio

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import Text
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import Token, GroupID, _logger
from funcs import get_registers, check_alarms, levels_info

# Создание экземпляров бота и планировщика
bot = Bot(token=Token)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()


@dp.message_handler(commands=['showid'])
async def get_id(message: types.Message):
    """Получаем ID группы"""
    _logger.info('### Был запрошен ID группы')
    await message.reply(message.chat.id)


# Кнопки
keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
buttons = ['Данные']
keyboard.add(*buttons)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """Обработка команд /start и /help с показом кнопочек"""
    txt = 'Привет, я твой инфобот. Для получениия данных нажми на кнопку "Данные".'
    await message.reply(text=txt, reply_markup=keyboard)


@dp.message_handler(Text(equals='Данные'))
async def reply_data(message: types.Message):
    """Обработчик кнопки 'Данные'"""
    await message.reply(text=levels_info())


@dp.message_handler()
async def echo(message: types.Message):
    """Ответ на любое сообщение"""
    await message.answer(
        text='Нажми на кнопку или введи команду "/start"', reply_markup=keyboard
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
    asyncio.create_task(get_registers())  # Опрос ПР
    asyncio.create_task(alarms_monitoring())  # Мониторинг уровней емкостей


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)  # Запуск непосредственно бота
