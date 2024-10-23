from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException
from threading import Thread
import serial.tools.list_ports
import socket
import json
import os
import time

_HOST = '127.0.0.1'
_PORT = 8888
_DEVICE = ''
tcp_server = None
modbus_client = None
ue_client = None

def create_socket():
    global tcp_server
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_server.bind((_HOST, _PORT))
    tcp_server.listen(1)
    print(f'Start Listening on {_HOST} {_PORT}')
    accept()

def accept():
    global tcp_server
    while True:
        connect, address = tcp_server.accept()
        thread = Thread(target=handle,args=(connect, address))
        thread.daemon = True
        thread.start()

def handle(connect, address):
    connection = can_connect(address)
    if connection is not True:
        connect.close()
    global ue_client
    ue_client = connect
    data = None
    while connection:
        try:
            data = connect.recv(65535)
        except Exception as e:
            print(f"recv error message : {str(e)}")
        if len(data) == 0:
            connect.close()
            ue_client = None
            connection = False
    print('close Thread')
    cleanup()
    os._exit(0)

def can_connect(address):
    return address[0] == _HOST

def cleanup():
    print('clean up')
    global modbus_client
    if modbus_client != None:
        modbus_client.close()
    global ue_client
    if ue_client != None:
        ue_client.close()

def create_modbus_client():
    if _DEVICE == '':
        return
    global modbus_client
    com = None
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.description.__contains__(_DEVICE):
            com = port.device
            break
    if com is None:
        return
    try:
        modbus_client = ModbusSerialClient(port=com, baudrate=19200, timeout=1)
    except Exception as e:
        print(f"Set modbus_client error message : {str(e)}")
    finally:
        if not modbus_client.connect():
            print("Can't connect to device")
        else:
                request_modbus_data()

def request_modbus_data():
    global modbus_client
    while True:
        try:
            result = modbus_client.read_holding_registers(address=0, count=1, slave=1)
            if not isinstance(result, ModbusIOException):
                print(f"The data read from device 1 : {result.registers}")
            else:
                print("read failure")
            data = {"data": result.registers}
            json_data = json.dumps(data)
            global ue_client
            if ue_client != None:
                ue_client.sendall((str(json_data) + '##').encode('utf-8'))
                time.sleep(0.2)
        except Exception as e :
            print(f"request data error message : {str(e)}")

if __name__ == '__main__':
    thread = Thread(target=create_modbus_client)
    thread.daemon = True
    thread.start()
    create_socket()