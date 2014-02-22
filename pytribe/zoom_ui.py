import time
import threading
import Queue
import wx
from bufferedcanvas import BufferedCanvas
import pytribe
import pyHook
from ScreenShotWX import screencapture
import win32con
import win32api


def current_tracking_center():
    pass


def get_tracking_data():
    pass


def calc_next_zoom_center():
    pass


def log_zm():
    pass


def parse_center(data_queue, default=None):
    gaze_data_update = pytribe.extract_queue(data_queue)
    if len(gaze_data_update) > 0:
        center_dict = gaze_data_update[-1]['values']['frame']['avg']
        center = (center_dict['x'], center_dict['y'])
    else:
        center = default
    return center


class ZoomMap(object):
    """Contains original bitmap, plus transformed zoom coordinates.

    Methods allow for translation between "base" coordinates and "zoom" coordinates"""
    def __init__(self, center=(400, 400), size=(400, 400), data_queue=None,
                 mod_key=None, zoom_factor=1.05):

        self.base_center = center
        self.base_size = size
        self.base_width = size[0]*1.0
        self.base_height = size[1]*1.0
        self.data_q = data_queue
        self.zoom_factor = zoom_factor
        self.mod_key = mod_key

        self.current_zoom_factor = 1.0
        self.zoom_center_offset_x = 0.0
        self.zoom_center_offset_y = 0.0

        self.base_loc = (int(center[0] - size[0]/2.0),
                         int(center[1] - size[1]/2.0))
        self.previous_center = center

        #TODO: Handle case where base_loc +size includes areas outside of the screen?
        if self.base_loc[0] < 0:
            self.base_loc = (0, self.base_loc[1])
        if self.base_loc[1] < 0:
            self.base_loc = (self.base_loc[0], 0)

        self.base_bitmap = screencapture(self.base_loc, self.base_size)
        self.zoom_bitmap = self.base_bitmap
        self.base_image = wx.ImageFromBitmap(self.base_bitmap)

    def zoom_size_px(self):
        return (self.base_width * self.current_zoom_factor,
                self.base_height * self.current_zoom_factor)

    def rel_zoom_loc(self):
        zsp = self.zoom_size_px()
        return (self.zoom_center_offset_x * self.current_zoom_factor +
                (zsp[0] - self.base_width)/2.0,
                self.zoom_center_offset_y * self.current_zoom_factor +
                (zsp[1] - self.base_width)/2.0)

    def abs_zoom_loc(self):
        return (int(self.base_center[0] + self.zoom_center_offset_x),
                int(self.base_center[1] + self.zoom_center_offset_y))

    def zoom_in(self, zoom_factor=1.05, zoomed_coords=True):
        #TODO: Clean and refactor this entire method...  it's a mess
        gaze_data_update = parse_center(self.data_q)
        if gaze_data_update not in [None, (0, 0)]:
            self.previous_center = gaze_data_update

        center = self.previous_center

        self.current_zoom_factor *= zoom_factor

        zoom_pan_speed = 0.2

        self.zoom_center_offset_x += (zoom_pan_speed *
                                      (center[0] - self.base_center[0]) /
                                      self.current_zoom_factor)
        self.zoom_center_offset_y += (zoom_pan_speed *
                                      (center[1] - self.base_center[1]) /
                                      self.current_zoom_factor)

        #width/height to scale new image to
        _width, _height = self.zoom_size_px()

        #Amount to shift new image down/right before scaling up
        _x_offset, _y_offset = self.rel_zoom_loc()

        #Prevent zooming outside of original box
        if _x_offset < 0:  x_offset = 0
        if _y_offset < 0:  _y_offset = 0
        if _x_offset + self.base_size[0] > _width:
            _x_offset = _width - self.base_size[0]
        if _y_offset + self.base_size[1] > _height:
            _y_offset = _height - self.base_size[1]

        #TODO: Trim or otherwise reduce computation for high-zoom levels...
        zoomed_image = self.base_image.Scale(_width, _height,
                                             wx.IMAGE_QUALITY_NORMAL)
        sub_image = zoomed_image.GetSubImage((_x_offset, _y_offset,
                                              self.base_size[0], self.base_size[1]))

        self.zoom_bitmap = wx.BitmapFromImage(sub_image)

    def next_zoom_bitmap(self):
        """Returns the next bitmap to be displayed on screen"""
        self.zoom_in(zoom_factor=self.zoom_factor)
        return self.zoom_bitmap

    def click_zoom_target(self):
        """Clicks once on zoom target"""
        prev_x, prev_y = win32api.GetCursorPos()
        click_x, click_y = self.abs_zoom_loc()
        print "Final Click Location: ", (click_x, click_y)
        win32api.SetCursorPos((click_x, click_y))
        if self.mod_key == 'NotCurrentlyUsed':  # Set mod-key for right-click if desired
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, click_x, click_y, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, click_x, click_y, 0, 0)
        else:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, click_x, click_y, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, click_x, click_y, 0, 0)
        win32api.SetCursorPos((prev_x, prev_y))



class ZoomFrame(wx.Frame):

    """Main Frame holding the logic and data structures of the program.

    Must pass tick interval and data queue to be used with the tracker"""
    def __init__(self, *args,  **kwargs):
        self.tick_ms = kwargs.pop('tick_ms', 125) # Remove non-standard kwargs
        self.data_q = kwargs.pop('data_queue', None)
        wx.Frame.__init__(self, *args, **kwargs)

        self.raw_data_q = Queue.Queue()
        self.mod_key_now_down = False
        self.trigger_key_now_down = False
        self.now_zooming = False

        #Define zoom trigger keys:
        self.mod_required = True
        self.cancel_on_mod_down = False
        self.mod_keys = ['Rmenu', 'Lmenu']
        self.trigger_keys = ['Space']
        self.current_mod_key = None
        self.zoom_canceled = False

        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.draw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_zoom, self.draw_timer)
        #Initialize canvas with dummy zoom_map (just to start program)
        self.current_zoom_map = ZoomMap(center=(400, 400), size=(400, 400),
                                        data_queue=self.data_q)
        self.canvas = ZoomCanvas(self, wx.ID_ANY,
                                 size=(400, 400),
                                 zoom_map=self.current_zoom_map)


    def on_key_down_event(self, event):
        """Detects when zoom hotkey is pressed.
        """
        #TODO: Seems to be a bug: releasing alt sometimes stops zoom
        self.zoom_canceled = False

        mod_down_event = event.Key in self.mod_keys
        trigger_down_event = event.Key in self.trigger_keys

        if mod_down_event:
            self.mod_key_now_down = True
            self.current_mod_key = event.Key
            # Cancel zoom early if mod key pressed down while zooming
            if self.trigger_key_now_down and self.cancel_on_mod_down:
                self.zoom_canceled = True
                self.stop_zoom()

        #Start zooming if trigger key pressed while mod_key is down
        if (trigger_down_event and
            (self.mod_key_now_down or not self.mod_required) and not
            self.trigger_key_now_down):

            self.trigger_key_now_down = True
            self.start_zoom(self.current_mod_key)

        # Do not pass through mod or trigger key events while zooming
        if (self.trigger_key_now_down and
            (mod_down_event or trigger_down_event)):
            return False

        #Use Escape key as backup zoom cancel
        if event.Key == "Escape" and self.trigger_key_now_down:
            self.zoom_canceled = True
            self.stop_zoom()
            return False  # Do not pass this cancel escape command

        return True  # for pass through key events, False to eat Keys


    def on_key_up_event(self, event):
        if event.Key in self.mod_keys:
            self.mod_key_now_down = False
        if event.Key in self.trigger_keys:
            self.trigger_key_now_down = False
            if self.now_zooming and not self.zoom_canceled:
                self.stop_zoom()
                self.click_target()
        return True


    def click_target(self):
        self.current_zoom_map.click_zoom_target()
        pass


    def start_zoom(self, mod_key):
        """Key press detected: Begin zoom sequence"""
        self.now_zooming = True
        gaze_avg = parse_center(self.data_q)
        print "Initial Base Target:  ", (int(gaze_avg[0]), int(gaze_avg[1]))
        if gaze_avg is not None:
            zm = ZoomMap(center=gaze_avg, size=(400, 400),
                         data_queue=self.data_q,
                         mod_key=mod_key)
            self.current_zoom_map = zm
            self.SetSize(zm.base_size)
            self.SetPosition(zm.base_loc)
            self.canvas.reset(zm)
            self.draw_timer.Start(self.tick_ms)
            self.Show()

    def stop_zoom(self):
        self.now_zooming = False
        self.Hide()
        self.draw_timer.Stop()

    def update_zoom(self, event):  # This "event" is required...
        self.canvas.update()

    def onClose(self, event):
        self.draw_timer.Stop()
        self.Show(False)
        self.Destroy()


class ZoomCanvas(BufferedCanvas):

    def __init__(self, *args, **kwargs):
        #Initialization of bitmap_gen MUST come first
        self.zm = kwargs.pop('zoom_map')
        BufferedCanvas.__init__(self, *args, **kwargs)

    def draw(self, dc):
        dc.DrawBitmap(self.zm.next_zoom_bitmap(), 0, 0)

    def reset(self, zoom_map):
        self.zm = zoom_map
        self.update()


def main():

    data_q = Queue.Queue()

    app = wx.App(False)
    frame = ZoomFrame(None,
                      wx.ID_ANY,
                      title="Zoom Frame",
                      style=wx.BORDER_NONE | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR,
                      tick_ms=40,
                      data_queue=data_q)

    hm = pyHook.HookManager()
    hm.KeyDown = frame.on_key_down_event
    hm.KeyUp = frame.on_key_up_event
    hm.HookKeyboard()

    #TODO: modify this code so tracker only collects data when zooming/scrolling
    data_thread = threading.Thread(target=pytribe.queue_tracker_frames,
                                   args=(data_q, None, 0.02))
    data_thread.daemon = True
    data_thread.start()

    #frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()

