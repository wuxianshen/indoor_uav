# -*- coding:utf-8 -*-
import sys
import time
import indoor_drone
import threading
import logging
import key_cmd_monitor
from drone_comm_handler import *
from external_pos_source.opti_track_source import opti_track_source

def initLogging(log_file):
    # Logging Config
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        filename=log_file,
                        filemode='w+')
    # define a Handler which writes INFO msgs or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)

if __name__ == '__main__':

    # 0.Init Variables
    initLogging('indoor.log')

    # Exit Event
    main_exit_event =  threading.Event()

    # External position source init
    #opti_track = opti_track_source(['172.20.111.128', 31500])
    # OptiTrack network, own IP (used for opti to send pos feedback)
    #opti_track = opti_track_source(['192.168.50.129', 31500])
    #opti_track.start()

    # UAV init
    # udp_drone = drone_udp_handler('udp', 'udp:localhost:14540') # local simulation

    # udp_drone = drone_udp_handler('udp', '192.168.2.129:14540') #
    udp_drone = drone_udp_handler('udp', '192.168.50.129:8899')  #
    #drone_fly = indoor_drone.indoor_drone(udp_drone, external_pos_source=opti_track)
    drone_fly = indoor_drone.indoor_drone(udp_drone)

    # serial_drone = drone_serial_handler('serial', 'COM15', 57600)
    # serial_drone = drone_serial_handler('serial', 'COM9', 115200) # USR Radio
    # drone_fly = indoor_drone.indoor_drone(serial_drone, external_pos_source=opti_track)

    # KEY : Start Keyboard Command Monitor
    #key_monitor = key_cmd_monitor.key_cmd_monitor(main_exit_event, drone_fly, opti_track)
    key_monitor = key_cmd_monitor.key_cmd_monitor(main_exit_event, drone_fly)
    key_monitor.start()

    main_exit_event.wait(600)

    #opti_track.stop()

    logging.info('[Main] Exit...')
    sys.exit(0)
