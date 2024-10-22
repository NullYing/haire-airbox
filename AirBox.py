#!/usr/bin/python
import socket
import threading
import time
import select
import logging

_LOGGER = logging.getLogger(__name__)


class device(object):
    def __init__(self, host):
        self.host = host
        self.port = 56800
        self.cs = None
        self.mac = self.connect()
        self.lock = threading.Lock()
        self.learning_packet = [
            0x00, 0x00, 0x27, 0x14, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0D, 0xFF, 0xFF, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01,
            0x4D, 0x02, 0x5A]
        self.ir_packet = [
            0x00, 0x00, 0x65, 0xfc, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x6c, 0x00, 0x00, 0x00, 0x55, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA,
            0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0x00, 0x00, 0x00, 0x00]
        self.req_packet = [
            0x00, 0x00, 0x27, 0x14, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0D, 0xFF, 0xFF, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01,
            0x4D, 0x01, 0x59]

    def get_mac(self):
        return self.mac

    def send_packet(self, data):
        try:
            is_tx_cpl = self.cs.sendall(data)
        except Exception as err:
            _LOGGER.error(f'Wrong {err}')
            self.cs.close()
            self.connect()
            is_tx_cpl = self.cs.sendall(data)
        finally:
            pass
        if is_tx_cpl is not None:
            return None
        response = []
        with self.lock:
            while True:
                ready_to_read, ready_to_write, in_error = \
                    select.select([self.cs], [], [], 0.4)
                if ready_to_read:
                    _data = self.cs.recv(512)
                    if _data:
                        response.append(_data)
                else:
                    break
        return response

    def check_sensor(self):
        if not self.mac:
            self.connect()
        if not self.mac:
            _LOGGER.error("HaierAirBox enter_learning connect fail")
            return False
        self.req_packet[40:52] = self.mac
        response = self.send_packet(bytes(self.req_packet))
        if response:
            return response
        return False

    def send_ir(self, data):
        if not self.mac:
            self.connect()
        if not self.mac:
            _LOGGER.error("HaierAirBox enter_learning connect fail")
            return False
        self.ir_packet[48:60] = self.mac
        data_len = len(data) + 48
        self.ir_packet[15] = (data_len % 256)
        self.ir_packet[14] = (data_len // 256)
        response = self.send_packet(bytes(self.ir_packet) + data)
        if response:
            return response
        return False

    def find_ir_packet(self):
        # with self.lock:
        while True:
            ready_to_read, ready_to_write, in_error = \
                select.select([self.cs], [], [], 0.9)
            if ready_to_read:
                _data = self.cs.recv(1024)
                if _data:
                    if _data[2] == 0x65 and _data[3] == 0xFE:
                        return _data
            else:
                break
        return False

    def enter_learning(self):
        if not self.mac:
            self.connect()
        if not self.mac:
            _LOGGER.error("HaierAirBox enter_learning connect fail")
            return False
        self.learning_packet[40:52] = self.mac
        response = self.send_packet(bytes(self.learning_packet))
        if response:
            return response
        return False

    def connect(self):
        try:
            self.cs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.cs.settimeout(5)
            self.cs.connect((self.host, self.port))
            mac_packet = self.cs.recv(512)
            mac = None
            if len(mac_packet) == 95:
                mac = list(mac_packet[40:52])
            self.cs.recv(512)  # 每当建立连接时服务器会直接回复2帧数据，先过滤掉
            return mac
        except Exception as erro:
            _LOGGER.error("HaierAirBox connect error: %s", erro)
            return False
