__author__ = 'Erik'

import win32gui
import win32con
import win32api
import time

time.sleep(1)

parent_handle = win32gui.WindowFromPoint((400,400))
window_rect = win32gui.GetWindowRect(parent_handle)

win32gui.SetForegroundWindow(parent_handle)
win32api.SetCursorPos((window_rect[2] - 15,
                       window_rect[3] - 250))
win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120, 0)

def all_ok(hwnd, param):
    print hwnd
    return True

#win32gui.EnumChildWindows(parent_handle, all_ok, None)

print parent_handle
print window_rect