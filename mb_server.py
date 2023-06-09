import asyncio
import logging
from types import SimpleNamespace

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext
)
from pymodbus.framer.rtu_framer import ModbusRtuFramer
from pymodbus.server import StartAsyncTcpServer


_logger = logging.getLogger()
# # Добавить в logging для записи лога в файл: filemode='a', filename='mb_server.log'
logging.basicConfig(level=logging.INFO)


def setup_server():
    """Установщик сервера"""
    args = SimpleNamespace()
    args.host = 'localhost'
    args.port = 5020
    args.framer = ModbusRtuFramer

    _logger.info('### Create datastore')

    datablock = ModbusSequentialDataBlock(1, [1] * 10)
    context = ModbusSlaveContext(
        di=datablock,
        co=datablock,
        hr=datablock,
        ir=datablock
    )

    single = True

    # Собираем воедино хранилище
    args.context = ModbusServerContext(
        slaves=context, single=single
    )

    return args


async def run_async_server(args):
    """ Запуск сервера"""
    txt = f'### start ASYNC server, listening on {args.host}:{args.port}'
    _logger.info(txt)
    address = (args.host, args.port)
    server = await StartAsyncTcpServer(
        context=args.context,
        address=address,
        framer=args.framer,
        allow_reuse_address=True
    )
    return server


if __name__ == "__main__":
    run_args = setup_server()
    asyncio.run(run_async_server(run_args))
