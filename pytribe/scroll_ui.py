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
        print "init"
        self.data_q = data_queue
        self.gaze_data = [init_gaze_data]
        self.update_gaze_center()

        self.init_center = trim_coordinate(pytribe.parse_center(self.gaze_data, round_int=True))
        self.latest_gaze_center = self.init_center
        print "init center: ", self.init_center
        self.window_handle = win32gui.WindowFromPoint(self.latest_gaze_center)
        while self.window_handle == 0:
            time.sleep(0.05)
            self.update_gaze_center()
            self.window_handle = win32gui.WindowFromPoint(self.latest_gaze_center)

        self.window_rect = win32gui.GetWindowRect(self.window_handle)
        self.initial_cursor_pos = win32api.GetCursorPos()
        print self.initial_cursor_pos
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
            self.latest_gaze_center = pytribe.parse_center(self.gaze_data, round_int=True)

    def shutdown(self):
        print "returning mouse to previous position: ", self.initial_cursor_pos
        win32api.SetCursorPos(self.initial_cursor_pos)

    def update(self):
        self.update_gaze_center()
        print self.window_center_y, self.latest_gaze_center[1]

        #Positive if looking at top of screen
        y_delta = self.window_center_y - self.latest_gaze_center[1]
        print y_delta
        if y_delta < -100:
            self.scroll(-1)
            if y_delta < -200:
                self.scroll(-1)
        if y_delta > 100:
            self.scroll(1)
            if y_delta > 200:
                self.scroll(1)

        pass

    def scroll(self, counts):
        """Scroll the mouse wheel count times (positive = up, negative = down)"""
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, counts*120, 0)
        pass
