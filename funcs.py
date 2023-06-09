import asyncio

import variables
from mb_tools import client
from config import _logger


def convert_to_bin(num: int, zerofill: int):
    """Конвертация десятичного числа в двоичное"""
    return bin(num)[2:].zfill(zerofill)


async def get_registers():
    """Опрос регистров ПР"""
    await asyncio.sleep(3)
    _logger.info('### Старт чтения регистров...')
    while True:
        res = client.read_holding_registers(512, 2)
        if res.isError():
            variables.connection = False
            await asyncio.sleep(60)
        else:
            variables.levels = convert_to_bin(res.registers[0], 2)
            variables.violations = convert_to_bin(res.registers[1], 4)
            variables.connection = True
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
            txt += f'Насос {i + 1} запущен в аварийном режиме!\n'
        variables.checked_violations[i] = variables.violations[i]
    return txt


def levels_info():
    """Информация по уровням емкостей"""
    txt = 'Ежедневная сводка:' + '\n'
    if variables.connection:
        for i in range(2):
            txt += f'Емкость {i+1}: Уровень '
            match variables.levels[i]:
                case '1':
                    txt += 'КРИТИЧЕСКИЙ!\n'
                case '0':
                    txt += 'Нормальный.\n'
    else:
        txt = 'Нет связи с прибором...'
    return txt
