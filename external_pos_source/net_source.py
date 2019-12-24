# -*- coding:utf-8 -*-
from external_pos_source.ext_pos_source import ext_pos_source
import socket
import math
import threading
import time
import logging

class net_source(ext_pos_source):

    def __init__(self, param):
        super(net_source, self).__init__(param)
        self.addr = param[0]
        self.port = param[1]

        self.origin_gps = [0, 0, 0]

        self.position = [0, 0, 0, 0, 0, 0]
        self.lock_position = threading.Lock()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.addr, self.port))

        self.update_external_pos_switch = False
        self.update_external_pos_thread = threading.Thread(target=self.update_external_position_loop)

    def start(self):
        #For isolated test
        self.set_origin_gps()
        self.update_external_pos_switch = True
        self.update_external_pos_thread.start()

    def stop(self):
        self.update_external_pos_switch = False
        time.sleep(0.5)
        self.socket.close()

    def set_origin_gps(self):
        gps_data, gps_addr = self.socket.recvfrom(256)
        gps_data = gps_data.split(b' ')
        cur_gps = [0, 0, 0]
        for idx in range(3):
            cur_gps[idx] = float(gps_data[idx])
        self.origin_gps = cur_gps

    def get_ned_pos(self, cur_gps):
        delat_lat = cur_gps[0] - self.origin_gps[0]
        delat_lon = cur_gps[1] - self.origin_gps[1]
        delat_alt = cur_gps[2] - self.origin_gps[2]
        C_EARTH = 6378137.0
        x = delat_lat * C_EARTH
        y = delat_lon * C_EARTH * math.cos(cur_gps[0])
        z = delat_alt
        return [x, y, z]

    def update_position(self, pos_ext):
        '''
        @ update_position: update external position one time
        :param pos_ext: the pos_ext to be updated
        :return: updated pos_ext
        '''
        gps_data, gps_addr = self.socket.recvfrom(256)
        gps_data = gps_data.split(b' ')
        cur_gps = [0, 0, 0]
        for idx in range(3):
            cur_gps[idx] = float(gps_data[idx])

        return self.get_ned_pos(cur_gps) + [0, 0, 0]

    def update_external_position_loop(self):
        logging.info('Start update optitrack position thread...')
        pos_cnt = 0
        while self.update_external_pos_switch:
            gps_data, gps_addr = self.socket.recvfrom(256)
            gps_data = gps_data.split(b' ')
            cur_gps = [0, 0, 0]
            for idx in range(3):
                cur_gps[idx] = float(gps_data[idx])

            #print(self.get_ned_pos(cur_gps))
            #continue

            self.lock_position.acquire()
            self.position = self.get_ned_pos(cur_gps) + [0, 0, 0]
            self.lock_position.release()

            pos_cnt = pos_cnt + 1
            if pos_cnt < 10:
                logging.info('[MOCAP] {0} {1} {2} {3} {4} {5}'.format(
                             self.position[0], self.position[1],
                             self.position[2], self.position[3],
                             self.position[4], self.position[5]))
        logging.info('Stop update optitrack position thread...')


if __name__ == '__main__':
    # OptiTrack network, own IP (used for opti to send pos feedback)
    net_src_handler = net_source(['127.0.0.1', 13245])
    net_src_handler.start()
    while True:
        net_src_handler.lock_position.acquire()
        print(net_src_handler.position)
        net_src_handler.lock_position.release()
        time.sleep(0.5)
    # time.sleep(2000)