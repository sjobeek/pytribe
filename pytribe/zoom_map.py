__author__ = 'Erik'

import wx
import pytribe
from .ScreenShotWX import screencapture
import win32con
import win32api


# Constants:
single_monitor_only = True


def trim_coordinate(trim_tuple, rectangle=None):
    """Trim a tuple to stay on the screen, or within a provided rectangle

    Rectangles are defined (x, y, w, h)"""
    if single_monitor_only and rectangle is None:
        display_x, display_y = wx.GetDisplaySize()
        trimmed_center_x = max(0, min(trim_tuple[0], display_x))
        trimmed_center_y = max(0, min(trim_tuple[1], display_y))
    elif rectangle is not None:
        trimmed_center_x = max(rectangle[0],
                               min(trim_tuple[0], rectangle[0] + rectangle[2]))
        trimmed_center_y = max(rectangle[1],
                               min(trim_tuple[1], rectangle[1] + rectangle[3]))
    else:
        raise NotImplementedError
        #TODO: Implement trimming for two-monitor setup
    return trimmed_center_x, trimmed_center_y


def center_of_rect(rectangle):
    center_x = int(round((rectangle[0] + rectangle[2]/2.0)))
    center_y = int(round((rectangle[1] + rectangle[3]/2.0)))
    return center_x, center_y


class ZoomMap(object):
    """Contains original bitmap, plus transformed zoom coordinates.

    Methods allow for translation between "base" coordinates and "zoom" coordinates"""
    def __init__(self, size=(400, 400), data_queue=None,
                 mod_key=None, zoom_factor=1.05, init_gaze_data=pytribe.query_tracker()):

        self.gaze_data = [init_gaze_data]
        self.data_q = data_queue
        #time.sleep(0.17)  # Allow eye-tracker time to warm up: 0.17 sec gives ~ 4-5 points
        self.update_gaze_center()
        center = pytribe.parse_center(self.gaze_data)
        self.init_center = trim_coordinate(center)
        self.base_rectangle = self.calc_base_rectangle(size)
        self.base_center = center_of_rect(self.base_rectangle)
        self.base_loc = (self.base_rectangle[0], self.base_rectangle[1])
        self.base_size = (self.base_rectangle[2], self.base_rectangle[3])

        self.latest_gaze_center = center               # Latest reported gaze center
        self.current_target_center = self.init_center  # Inferred point to click
        #May confuse user if zoom_center doesn't start at base_center...  hmmm
        self.current_zoom_center = self.init_center    # Center of current zoom

        self.zoom_factor = zoom_factor
        self.mod_key = mod_key

        self.current_zoom_factor = 1.0
        self.zoom_center_offset_x = 0.0
        self.zoom_center_offset_y = 0.0

        self.previous_center = center


        #TODO: Handle case where base_loc +size includes areas outside of the screen?

        self.base_bitmap = screencapture(self.base_loc, self.base_size)  # , debug=True)
        self.zoom_bitmap = self.base_bitmap
        self.base_image = wx.ImageFromBitmap(self.base_bitmap)

    def calc_base_rectangle(self, full_size=(400,400)):
        """Return a rectangle (x, y, width, height) for the base bitmap"""
        display_x, display_y = wx.GetDisplaySize()
        max_loc_x = min(display_x - full_size[0],
                        int(self.init_center[0] - full_size[0]/2.0))
        max_loc_y = min(display_y - full_size[1],
                        int(self.init_center[1] - full_size[1]/2.0))
        base_loc_x = max(0, max_loc_x)
        base_loc_y = max(0, max_loc_y)
        base_width = full_size[0]
        base_height = full_size[1]
        return base_loc_x, base_loc_y, base_width, base_height

    def zoom_size_px(self):
        return (self.base_size[0] * self.current_zoom_factor,
                self.base_size[1] * self.current_zoom_factor)

    def update_gaze_center(self):
        self.gaze_data.extend(pytribe.extract_queue(self.data_q))
        if self.gaze_data is not []:
            self.latest_gaze_center = pytribe.parse_center(self.gaze_data)

    def update_zoom_center(self):
        prev_zoom_center = self.current_zoom_center
        zoom_pan_speed = 0.3
        #Alternative update strategies..  hmm
        #Currently adjusts zoom center relative to prev. zoom center: Initially from init_center
        zoom_center_offset_x = (zoom_pan_speed *
                                (self.latest_gaze_center[0] - prev_zoom_center[0]) /
                                self.current_zoom_factor)
        zoom_center_offset_y = (zoom_pan_speed *
                                (self.latest_gaze_center[1] - prev_zoom_center[1]) /
                                self.current_zoom_factor)
        trimmed_result = trim_coordinate((prev_zoom_center[0] + zoom_center_offset_x,
                                          prev_zoom_center[1] + zoom_center_offset_y),
                                         self.base_rectangle)
        self.current_zoom_center = trimmed_result

    def update_target_center(self):
        x_int = int(round(self.current_zoom_center[0]))
        y_int = int(round(self.current_zoom_center[1]))
        self.current_target_center = (x_int, y_int)
        pass

    def rel_zoom_loc(self):
        """Zoom center relative to upper-left corner of zoom box"""
        #TODO: This code seems a bit opaque and possibly wrong?  Simplify...
        zsp = self.zoom_size_px()
        zoom_center_offset_x = self.current_zoom_center[0] - self.base_center[0]
        zoom_center_offset_y = self.current_zoom_center[1] - self.base_center[1]
        return (zoom_center_offset_x * self.current_zoom_factor +
                (zsp[0] - self.base_size[0])/2.0,
                zoom_center_offset_y * self.current_zoom_factor +
                (zsp[1] - self.base_size[0])/2.0)

    def abs_zoom_loc(self):
        return (int(self.init_center[0] + self.zoom_center_offset_x),
                int(self.init_center[1] + self.zoom_center_offset_y))

    def update_zoom_bmp(self, zoom_factor=1.07, zoomed_coords=True):

        if self.current_zoom_factor <= 10:  # Don't zoom in beyond all reason...
            self.current_zoom_factor *= zoom_factor

        # Update order: gaze -> zoom -> target
        self.update_gaze_center()
        self.update_zoom_center()
        self.update_target_center()

        #TODO: Refactor zoom_in, abs_zoom_loc, and update_zoom_center
        #width/height to scale new image to
        scaled_width, scaled_height = self.zoom_size_px()
        #Amount to shift new image down/right before scaling up
        _x_offset, _y_offset = self.rel_zoom_loc()
        #Prevent zooming outside of original box
        if _x_offset < 0:  _x_offset = 0
        if _y_offset < 0:  _y_offset = 0
        if _x_offset + self.base_size[0] > scaled_width:
            _x_offset = scaled_width - self.base_size[0]
        if _y_offset + self.base_size[1] > scaled_height:
            _y_offset = scaled_height - self.base_size[1]

        #TODO: Trim or otherwise reduce computation for high-zoom levels...
        zoomed_image = self.base_image.Scale(scaled_width, scaled_height,
                                             wx.IMAGE_QUALITY_NORMAL)
        sub_image = zoomed_image.GetSubImage((_x_offset, _y_offset,
                                              self.base_size[0], self.base_size[1]))

        self.zoom_bitmap = wx.BitmapFromImage(sub_image)
        return self.zoom_bitmap

    def click_target_center(self):
        """Clicks once on zoom target"""
        prev_x, prev_y = win32api.GetCursorPos()
        click_x, click_y = self.current_target_center
        win32api.SetCursorPos((click_x, click_y))
        if self.mod_key == 'ChangeMeToEnable':  # Set mod-key for right-click if desired
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, click_x, click_y, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, click_x, click_y, 0, 0)
        else:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, click_x, click_y, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, click_x, click_y, 0, 0)
        win32api.SetCursorPos((prev_x, prev_y))



