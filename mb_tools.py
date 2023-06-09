from pymodbus.client import ModbusTcpClient
from pymodbus.framer.rtu_framer import ModbusRtuFramer

from config import NetData

net_data = NetData()

client = ModbusTcpClient(
    host=net_data.remotehost,
    port=net_data.remoteport,
    framer=ModbusRtuFramer
)
