# -*- coding:utf-8 -*-
from pymavlink import mavutil
import re
import time
import threading
import logging
import sys
from external_pos_source.opti_track_source import opti_track_source

class indoor_drone:

    def __init__(self, drone_comm_handler, system_id = 1, external_pos_source = None):
        '''
        @ __init__: init object of indoor drone class
        :param drone_comm_handler: The drone communication handler, such as serial port or udp link
        :param system_id: UAV id for control
        :param external_pos_source: The external position source, such as vision position based on OptiTrack
        '''
        self.drone_comm_handler = drone_comm_handler
        self.system_id = system_id

        self.lock_position = threading.Lock()
        self.position = [0, 0, 0, 0, 0, 0]
        self.position_external = [0, 0, 0, 0, 0, 0] # pos from external position source

        # offboard control
        self.offboard_position_control_onoff = False
        self.offboard_position_rate = 40
        self.offboard_target_position = [0, 0, 0, 0, 0, 0]
        self.offboard_position_thread = threading.Thread(target=self.offboard_position_control_loop)

        # external position
        self.push_external_pos_cnt = 0
        self.external_pos_source = external_pos_source
        self.pos_push_thread = threading.Thread(target=self.push_external_position_loop)

        #self.opti_handler = opti_track_source(['192.168.50.129', 31500])

    def offboard_position_control_loop(self):
        '''
        @  offboard_position_control_loop: loop function for offboard position control thread
        '''
        logging.info('[UAV] Auto Offboard Position Control Thread Start...')
        while self.offboard_position_control_onoff:
            self.offboard_set_target_position(self.offboard_target_position[0],
                                              self.offboard_target_position[1],
                                              self.offboard_target_position[2])
            time.sleep(1 / (self.offboard_position_rate - 1) )
        logging.info('[UAV] Auto Offboard Position Control Thread Exit...')

    def connect_uav(self):
        logging.info('[UAV] Waiting for uav connect...')
        while True:
            if self.drone_comm_handler.type == 'serial':
                self.the_connection = mavutil.mavlink_connection(self.drone_comm_handler.port, self.drone_comm_handler.baud)
            elif self.drone_comm_handler.type == 'udp':
                self.the_connection = mavutil.mavlink_connection(self.drone_comm_handler.url)
            else:
                logging.error('Wrong drone communication type {0}'.format(self.drone_comm_handler.type))

            self.the_connection.wait_heartbeat()
            if self.the_connection.target_system == self.system_id:
                logging.info('Connection established, system id : {0}, component id : {1}.' \
                      .format(self.the_connection.target_system, self.the_connection.target_component))
                break

        if self.external_pos_source != None:
            self.pos_push_thread.start()

    def arm(self):
        self.the_connection.mav.command_long_send(
            self.the_connection.target_system,  # 1# autopilot system id
            self.the_connection.target_component,  # 1# autopilot component id
            400,  # command id, ARM/DISARM
            0,  # confirmation
            1,  # arm!
            0,
            0.0, 0.0, 0.0, 0.0, 0.0,  # unused parameters for this command,
            force_mavlink1=True)
        time.sleep(0.5)
        logging.info('Indoor Drone Armed!!')

    def disarm(self):
        self.the_connection.mav.command_long_send(
            self.the_connection.target_system,  # 1# autopilot system id
            self.the_connection.target_component,  # 1# autopilot component id
            400,  # command id, ARM/DISARM
            0,  # confirmation
            0,  # disarm!
            0,
            0.0, 0.0, 0.0, 0.0, 0.0,  # unused parameters for this command,
            force_mavlink1=True)
        logging.info("Indoor Drone Disarmed!!")

    def land(self):
        if self.offboard_position_control_onoff:
            self.offboard_position_control_onoff = False
            self.offboard_position_thread.join()

        timeBegin = time.time()
        landing_position_x = self.position[0]
        landing_position_y = self.position[1]
        while True:
            timeNow = time.time()
            timeFromBegin = timeNow - timeBegin
            self.offboard_set_target_position(landing_position_x, landing_position_y, self.position[2] + 0.1 * timeFromBegin)
            if(self.position[2] > -0.01):
                logging.info('[UAV] Land finished...')
                #break

    def set_offboard_position_continuously(self, position):
        '''
        @ set_offboard_position_continuously: set a target position, and the position control thread will
                                               push the target position automatically
        :param position: [x, y, z, r, p, y]
        '''
        self.offboard_target_position = position

        logging.info('[UAV] === Target === x,y,z : {0}, {1}, {2}'.format(
                     self.offboard_target_position[0],
                     self.offboard_target_position[1],
                     self.offboard_target_position[2]))

        # if position control thread is not running, pull it up
        if self.offboard_position_control_onoff == False:
            self.offboard_position_control_onoff = True
            self.offboard_position_thread.start()

    def offboard_set_target_position(self, x, y, z):
        '''
        @ offboard_set_target_position: send one target position to UAV
        @ Note: you need send target position continuously to lead the UAV to the target
        :param x:
        :param y:
        :param z:
        '''
        self.the_connection.mav.set_position_target_local_ned_send(0, self.the_connection.target_system,
                                                                   self.the_connection.target_component,
                                                                   mavutil.mavlink.MAV_FRAME_LOCAL_NED, 0b110111111000,
                                                                   x, y, z, 0, 0, 0, 0, 0, 0, 0, 0, force_mavlink1=True)
    def set_mode_to_offboard(self):
        '''
        @ set_mode_to_offboard: switch UAV's mode to offboard, so that we can conduct position and velocity control
        '''
        logging.info('[UAV] Switch to Offboard Mode...')
        for i in range(100):
            self.offboard_set_target_position(0, 0, -0.5)

        self.the_connection.mav.command_long_send(
            self.the_connection.target_system,  # 1# autopilot system id
            self.the_connection.target_component,  # 1# autopilot component id
            176,  # MAV_CMD_DO_SET_MODE (176 )
            0,  # confirmation
            129,
            6,
            0,
            0.0, 0.0, 0.0, 0.0,  # unused parameters for this command,
            force_mavlink1=True)

    def offboard_to_certain_height(self, height):
        '''
        @ offboard_to_certain_height: Lead the UAV to a certain height (with current x, y)
        :param height: target height in m
        '''
        logging.info('[UAV] Hovering at certain height...')
        cur_ned_pos = self.get_current_local_ned_position()
        cur_ned_pos[0] = 0
        cur_ned_pos[1] = 0
        cur_ned_pos[2] = -1 * height
        self.set_offboard_position_continuously(cur_ned_pos)

    def get_current_local_ned_position(self):
        '''
        @ get_current_local_ned_position: get current LOCAL_POSITION_NED
        :return: LOCAL_POSITION_NED [x, y, z, Vx, Vy, Vz]
        '''
        # Update LOCAL_POSITION_NED
        self.the_connection.recv_match(type='LOCAL_POSITION_NED', blocking=True)
        '''
        logging.info('[TELEMETRY] Local NED pos {0} {1} {2}'.format(self.the_connection.messages['LOCAL_POSITION_NED'].x,
               self.the_connection.messages['LOCAL_POSITION_NED'].y,
               self.the_connection.messages['LOCAL_POSITION_NED'].z))
        '''
        return [self.the_connection.messages['LOCAL_POSITION_NED'].x,
                self.the_connection.messages['LOCAL_POSITION_NED'].y,
                self.the_connection.messages['LOCAL_POSITION_NED'].z,
                self.the_connection.messages['LOCAL_POSITION_NED'].vx,
                self.the_connection.messages['LOCAL_POSITION_NED'].vy,
                self.the_connection.messages['LOCAL_POSITION_NED'].vz]

    def request_data_stream(self):
        logging.info('[UAV] Request data streams...')
        '''
        self.the_connection.mav.command_long_send(
            self.the_connection.target_system,  # 1# autopilot system id
            self.the_connection.target_component,  # 1# autopilot component id
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,  # command id
            0,
            mavutil.mavlink.MAVLINK_MSG_ID_LOCAL_POSITION_NED,
            10,
            0.0, 0.0, 0.0, 0.0, 0.0,  # unused parameters for this command,
            force_mavlink1=True)
        
        self.the_connection.mav.request_data_stream_send(
            self.the_connection.target_system,  # 1# autopilot system id
            self.the_connection.target_component,  # 1# autopilot component id
            mavutil.mavlink.MAV_DATA_STREAM_ALL,  # command id
            1,
            1
        )
        '''
        time.sleep(1)

        # self.the_connection.recv_match(type='LOCAL_POSITION_NED', blocking=True)
        while True:
            time.sleep(0.1)
            msg = self.the_connection.recv_match(blocking=True)
            # logging.info('[UAV] Msg type {0}'.format(msg.get_type()))
            if msg.get_type() == 'LOCAL_POSITION_NED':
                logging.info('[UAV] Ned {0} {1} {2}'.format(msg.x, msg.y, msg.z))

                logging.info('[UAV] Local NED pos {0} {1} {2}'.format(self.the_connection.messages['LOCAL_POSITION_NED'].x,
                                                                   self.the_connection.messages['LOCAL_POSITION_NED'].y,
                                                                   self.the_connection.messages[
                                                                   'LOCAL_POSITION_NED'].z))
                break
        logging.info('[UAV] After request data streams...')

    def push_external_position_loop(self):
        logging.info('[UAV] Start pushing external position to UAV...')
        while True:
            self.update_external_postion()
            self.mav_send_external_position()
            time.sleep(0.0005)

    def update_external_postion(self):
        '''
        @ update_external_postion: update external position
        '''
        # cur_ned_pos = self.get_current_local_ned_position()
        self.lock_position.acquire()
        # external_pos_source should realize the update_position method
        self.position_external = self.external_pos_source.update_position(self.position_external)
        # print(self.position_external)
        self.lock_position.release()

    def mav_send_external_position(self):
        self.the_connection.mav.vision_position_estimate_send(self.system_id, self.position_external[0], self.position_external[1],
                                                              self.position_external[2], self.position_external[3], self.position_external[4],
                                                              self.position_external[5])
        self.push_external_pos_cnt = self.push_external_pos_cnt + 1
        '''
        if self.push_external_pos_cnt % 100 == 0:
            logging.info('[UAV] Send Mav Pos {0} {1} {2} {3} {4} {5}'.format(
                self.position_external[0], self.position_external[1],
                self.position_external[2], self.position_external[3],
                self.position_external[4], self.position_external[5]))
        '''