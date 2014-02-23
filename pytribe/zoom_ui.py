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


def parse_center(data_dict_list, default=None, raw=False):
    if len(data_dict_list) > 0:
        if raw:
            center_dict = data_dict_list[-1]['values']['frame']['raw']
            center = (center_dict['x'], center_dict['y'])
        else:
            center_dict = data_dict_list[-1]['values']['frame']['avg']
            center = (center_dict['x'], center_dict['y'])
    else:
        center = default
    return center


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
        center = parse_center(self.gaze_data)
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
        base_loc_x = max(0, max_loc_x) #int(self.init_center[0] - full_size[0]/2.0))
        base_loc_y = max(0, max_loc_y) #int(self.init_center[1] - full_size[1]/2.0))

        base_width = full_size[0]  # base_max_x - base_loc_x
        base_height = full_size[1]  # base_max_y - base_loc_y
        return base_loc_x, base_loc_y, base_width, base_height

    def zoom_size_px(self):
        return (self.base_size[0] * self.current_zoom_factor,
                self.base_size[1] * self.current_zoom_factor)

    def update_gaze_center(self):
        self.gaze_data.extend(pytribe.extract_queue(self.data_q))
        if self.gaze_data is not []:
            self.latest_gaze_center = parse_center(self.gaze_data)

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



class ZoomFrame(wx.Frame):

    """Main Frame holding the logic and data structures of the program.

    Must pass tick interval and data queue to be used with the tracker"""
    def __init__(self, *args,  **kwargs):
        self.tick_ms = kwargs.pop('tick_ms', 125) # Remove non-standard kwargs
        self.data_q = kwargs.pop('data_queue', Queue.Queue())
        wx.Frame.__init__(self, *args, **kwargs)

        self.raw_data_q = Queue.Queue()
        self.mod_key_now_down = False
        self.trigger_key_now_down = False
        self.now_zooming = False
        self.zoom_triggered = False

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
        self.current_zoom_map = ZoomMap(size=(400, 400),
                                        data_queue=self.data_q)
        self.canvas = ZoomCanvas(self, wx.ID_ANY,
                                 size=(400, 400),
                                 zoom_map=self.current_zoom_map)
        self.thread_shutdown_event = threading.Event()
        self.data_thread_running = False
        self.data_thread = None

    def start_data_thread(self):

        if not self.data_thread_running:
            self.thread_shutdown_event.clear()
            self.data_thread = threading.Thread(target=pytribe.queue_tracker_frames,
                                           args=(self.data_q, None, 0.02),
                                           kwargs={'event':self.thread_shutdown_event})
            self.data_thread.daemon = True
            self.data_thread.start()
            self.data_thread_running = True

    def stop_data_thread(self):
        self.thread_shutdown_event.set()
        self.data_thread_running = False

    def on_key_down_event(self, event):
        """Detects when zoom hotkey is pressed.
        """
        #TODO: Seems to be a bug: releasing alt sometimes stops zoom
        self.zoom_canceled = False

        mod_down_event = event.Key in self.mod_keys
        trigger_down_event = event.Key in self.trigger_keys

        #Wake tracker on mod key-press (or any key press?)
        if mod_down_event and not self.trigger_key_now_down:
            self.start_data_thread()

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
            self.start_zoom()

        # Do not pass through mod or trigger key events while zooming
        if (self.trigger_key_now_down or self.now_zooming and
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
            if self.data_thread_running and not self.trigger_key_now_down:
                self.stop_data_thread()
        if event.Key in self.trigger_keys:
            self.trigger_key_now_down = False
            if self.zoom_triggered and not self.zoom_canceled:
                self.stop_zoom()
        return True


    def click_target(self):
        self.current_zoom_map.click_target_center()
        pass

    def initialize_queue(self):
        with self.data_q.mutex:
            self.data_q.queue.clear()
        initial_values = pytribe.query_tracker()
        self.data_q.put(initial_values)

    def start_zoom(self):
        """Key press detected: Begin zoom sequence"""
        self.zoom_triggered = True
        self.initialize_queue()
        self.start_data_thread()
        #Initialize the ZoomMap after 0.17 seconds, to give eye-tribe a chance to wake up
        wx.CallLater(170, self.delayed_init_zm)

    def delayed_init_zm(self):
        if not self.zoom_canceled:
            self.now_zooming = True
            zm = ZoomMap(size=(400, 400),
                         data_queue=self.data_q,
                         mod_key=self.current_mod_key)
            self.current_zoom_map = zm
            self.SetSize(zm.base_size)
            self.SetPosition(zm.base_loc)
            self.canvas.reset(zm)
            self.draw_timer.Start(self.tick_ms)
            self.Show()
            if not self.zoom_triggered:  # Immediately close+click if no-longer triggered
                self.stop_zoom()

    def stop_zoom(self):
        self.zoom_triggered = False
        self.now_zooming = False
        self.stop_data_thread()
        self.Hide()
        self.draw_timer.Stop()
        if not self.zoom_canceled:
            self.click_target()

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
        dc.DrawBitmap(self.zm.update_zoom_bmp(), 0, 0)

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



    #frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()

