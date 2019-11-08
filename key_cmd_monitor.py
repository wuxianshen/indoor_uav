import threading
import logging

class key_cmd_monitor:
    def __init__(self, exit_event, uav):
        self.exit_event = exit_event
        self.uav = uav
        self.monitor_thread = threading.Thread(target = self.key_cmd_monitor_loop)

    def start(self):
        self.monitor_thread.start()

    def key_cmd_monitor_loop(self):
        while True:
            keyboard_cmd = input()
            if keyboard_cmd == 'uav':
                logging.info('[CMD] Connect uav...')
                self.uav.connect_uav()
            if keyboard_cmd == 'arm':
                logging.info('[CMD] Arm uav...')
                self.uav.arm()
            if keyboard_cmd == 'dis':
                logging.info('[CMD] Disarm uav...')
                self.uav.disarm()
            if keyboard_cmd == 'offboard':
                logging.info('[CMD] Switch uav to offboard...')
                self.uav.set_mode_to_offboard()
            if keyboard_cmd == 'land':
                logging.info('[CMD] Land uav...')
                self.uav.land()
            if keyboard_cmd == 'height':
                logging.info('[CMD] Please input target height...')
                height = input()
                self.uav.offboard_to_certain_height(float(height))
            if keyboard_cmd == 'ned':
                logging.info('[CMD] Acquire uav local ned pos...')
                self.uav.get_current_local_ned_position()
            if keyboard_cmd == 'require':
                logging.info('[CMD] Offboard position control...')
                self.uav.request_data_stream()
            if keyboard_cmd == 'pos':
                logging.info('[CMD] Offboard position control...')
                self.uav.set_offboard_position_continuously([5, 3, -2, 0, 0, 0])
            if keyboard_cmd == 'exit':
                self.exit_event.set()
                break

