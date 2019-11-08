# -*- coding:utf-8 -*-
from external_pos_source.ext_pos_source import ext_pos_source
import socket
import math
import threading
import time
import logging

class opti_track_source(ext_pos_source):

    def __init__(self, param):
        super(opti_track_source, self).__init__(param)
        self.addr = param[0]
        self.port = param[1]

        self.position = [0, 0, 0, 0, 0, 0]
        self.lock_position = threading.Lock()

        self.update_external_pos_switch = False
        self.update_external_pos_thread = threading.Thread(target=self.update_external_position_loop)

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.addr, self.port))

        self.update_external_pos_switch = True
        self.update_external_pos_thread.start()

    def stop(self):
        self.update_external_pos_switch = False
        time.sleep(0.5)
        self.socket.close()

    def update_position(self, pos_ext):
        '''
        @ update_position: update external position
        :param pos_ext: the pos_ext to be updated
        :return: updated pos_ext
        '''
        # for local test
        #'''
        pos_ext[0] = 1
        pos_ext[1] = 1
        pos_ext[2] = -0.2
        #'''
        # optitrack
        '''
        self.lock_position.acquire()
        pos_ext = self.position
        self.lock_position.release()
        '''
        return pos_ext

    def update_external_position_loop(self):
        logging.info('Start update optitrack position thread...')
        while self.update_external_pos_switch:
            self.optitrack_data, self.optitrack_addr = self.socket.recvfrom(2048)
            if not self.optitrack_data:
                logging.error('no data!')
            new_position = self.optitrack_data.split(',')
            for idx in range(6):
                new_position[idx] = float(new_position[idx])

            self.lock_position.acquire()
            self.position = new_position
            self.lock_position.release()
        logging.info('Stop update optitrack position thread...')