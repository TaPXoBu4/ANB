import asyncio
import sqlite3 as sq
from datetime import datetime, timedelta
from pymodbus.exceptions import ConnectionException
from scipy.signal import savgol_filter
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import variables
from mb_tools import client
from config import _logger


def convert_to_bin(num: int, zerofill: int):
    """Конвертация десятичного числа в двоичное"""
    return bin(num)[2:].zfill(zerofill)


async def reg_reading():
    """Опрос регистров ПР"""
    await asyncio.sleep(3)
    _logger.info('### Старт чтения регистров...')
    while True:
        try:
            res = client.read_holding_registers(512, 2, 16)
            if res.isError():
                variables.connection = 0
                _logger.info('### Ошибка чтения регистров')
            else:
                variables.levels = convert_to_bin(res.registers[0], 2)
                variables.violations = convert_to_bin(res.registers[1], 4)
                variables.connection = 1
        except ConnectionException:
            variables.connection = 0
            _logger.info('### Нет связи с прибором...')
        with sq.connect('ANB_DB.db', detect_types=sq.PARSE_DECLTYPES | sq.PARSE_COLNAMES) as con:
            moment = datetime.now()
            cur = con.cursor()
            cur.execute('INSERT INTO connection(cnd, dttm) values (?, ?)', (variables.connection, moment))
            con.commit()
        await asyncio.sleep(2)


def check_alarms():
    """Проверяем полученные данные на наличие инцидентов"""
    txt = ''
    for i in range(2):
        if int(variables.levels[i]) and variables.levels[i] != variables.checked_levels[i]:
            txt += f'Критический уровень емкости {i + 1}!\n'
        variables.checked_levels[i] = variables.levels[i]
    for i in range(4):
        if int(variables.violations[i]) and variables.violations[i] != variables.checked_violations[i]:
            txt += f'Обходной режим работы насоса {i + 1}!\n'
        variables.checked_violations[i] = variables.violations[i]
    return txt


def levels_info():
    """Информация по уровням емкостей"""
    txt = 'Ежедневная сводка:' + '\n'
    if variables.connection:
        for i in range(2):
            txt += f'Емкость {i + 1}: Уровень '
            match variables.levels[i]:
                case '1':
                    txt += 'КРИТИЧЕСКИЙ!\n'
                case '0':
                    txt += 'Нормальный.\n'
    else:
        txt = 'Нет связи с прибором...'
    return txt


def get_data_from_db(date: datetime):
    with sq.connect('ANB_DB.db', detect_types=sq.PARSE_DECLTYPES | sq.PARSE_COLNAMES) as con:
        cur = con.cursor()
        if date.date() == datetime.now().date():
            date = date - timedelta(days=1)
            query = 'SELECT cnd, dttm FROM connection WHERE dttm >= ? ORDER BY cnd_id'
        else:
            query = 'SELECT cnd, dttm FROM connection WHERE date(dttm) = date(?) ORDER BY cnd_id'
        cur.execute(query, (date,))
        result = cur.fetchall()
        print(result)
    return result


def build_plot(date: datetime):
    date_string = date.strftime('%Y-%m-%d')
    temp = get_data_from_db(date)
    if temp:
        filename = 'plot.png'
        data = list(zip(*temp))
        sigma = len(data[0]) if len(data[0]) < 100 else 100
        curved = savgol_filter(data[0], window_length=sigma, polyorder=1)
        plt.clf()
        plt.rcParams['figure.figsize'] = (10, 4)
        date_format = mdates.DateFormatter('%H:%M')
        plt.gca().xaxis.set_major_formatter(date_format)
        plt.plot(data[1], curved)
        plt.xlabel('Время')
        plt.ylabel('Связь')
        plt.savefig(filename)
        txt = 'График построен: '
    else:
        txt = 'Нет данных за этот день: '
        filename = ''
    txt += ' ' + date_string
    return txt, filename


def save_user(user_id, username):
    save_query = 'INSERT INTO users(user_id, username) VALUES (?, ?)'
    with sq.connect('ANB_DB.db') as con:
        cur = con.cursor()
        cur.execute(save_query, (user_id, username))
        con.commit()
    variables.users_store[user_id] = username


def users_parser():
    result = dict()
    with sq.connect('ANB_DB.db') as con:
        cur = con.cursor()
        parse_query = 'SELECT * FROM users'
        cur.execute(parse_query)
        temp = cur.fetchall()
        if temp:
            for pair in temp:
                key, value = pair
                result[key] = value
    return result
