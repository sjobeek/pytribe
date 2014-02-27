__author__ = 'Erik'

import pytribe
import win32gui
import win32api
import win32con
import time
from .zoom_map import trim_coordinate

def start_scroll():
    print "Starting Scroll!"


class WindowScroller(object):

    def __init__(self, data_queue=None,
                 init_gaze_data=pytribe.query_tracker()):
        self.data_q = data_queue
        self.gaze_data = [init_gaze_data]
        self.update_gaze_center()
        self.latest_gaze_data_null = False

        self.init_center = trim_coordinate(pytribe.parse_center(self.gaze_data, round_int=True))
        self.latest_gaze_center = self.init_center
        self.window_handle = win32gui.WindowFromPoint(self.latest_gaze_center)
        while self.window_handle == 0:
            time.sleep(0.05)
            self.update_gaze_center()
            self.window_handle = win32gui.WindowFromPoint(self.latest_gaze_center)

        self.window_rect = win32gui.GetWindowRect(self.window_handle)
        self.initial_cursor_pos = win32api.GetCursorPos()
        self.window_center_y = int((self.window_rect[3] - self.window_rect[1]) / 2.0)

        #Sleep required here to avoid bugs...
        time.sleep(0.01)
        #Focus window to be screencapture
        win32gui.SetForegroundWindow(self.window_handle)

        #Move mouse to lower-right area of window to scroll
        win32api.SetCursorPos((self.window_rect[2] - 15,
                               self.window_rect[3] - 300))

    def update_gaze_center(self):
        self.gaze_data.extend(pytribe.extract_queue(self.data_q))
        if self.gaze_data is not []:
            updated_center = pytribe.parse_center(self.gaze_data, round_int=True)

            if updated_center == (0, 0):
                self.latest_gaze_data_null = True
            else:
                self.latest_gaze_data_null = False
                self.latest_gaze_center = updated_center

    def shutdown(self):
        win32api.SetCursorPos(self.initial_cursor_pos)

    def update(self):
        self.update_gaze_center()

        #Positive if looking at top of screen, 200 pixel offset up
        y_delta = (self.window_center_y - 200) - self.latest_gaze_center[1]
        if y_delta < -100:
            self.scroll(-1)
            if y_delta < -300:
                self.scroll(-1)
        if y_delta > 100:
            self.scroll(1)
            if y_delta > 300:
                self.scroll(1)

    def scroll(self, counts):
        """Scroll the mouse wheel count times (positive = up, negative = down)"""
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, counts*120, 0)
        pass
