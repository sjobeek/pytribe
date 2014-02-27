__author__ = 'Erik'

import threading
import Queue
import wx
from .bufferedcanvas import BufferedCanvas
import pytribe
from .zoom_map import ZoomMap
from .scroll_ui import WindowScroller
import time
import scroll_ui


class ZoomFrame(wx.Frame):

    """Main Frame holding the logic and data structures of the program.

    Must pass tick interval and data queue to be used with the tracker"""
    def __init__(self, *args,  **kwargs):
        self.zoom_tick_ms = kwargs.pop('tick_ms', 125) # Remove non-standard kwargs
        self.data_q = kwargs.pop('data_queue', Queue.Queue())
        wx.Frame.__init__(self, *args, **kwargs)

        self.now_scrolling = False
        self.scroll_tick_ms = 50
        self.scroll_trigger_key_now_down = False

        self.raw_data_q = Queue.Queue()
        self.mod_key_now_down = False
        self.trigger_key_now_down = False
        self.now_zooming = False
        self.zoom_triggered = False
        self.cancel_scroll_with_gaze = True
        self.stop_scroll_on_space = True

        #Define zoom trigger keys:
        self.mod_required = True
        self.cancel_on_mod_down = False  # TODO: Not working...
        self.mod_keys = ['Rmenu', 'Lmenu']
        self.trigger_keys = ['Space']
        self.scroll_trigger_keys = ['Oem_2'] #back-slash key
        self.current_mod_key = None
        self.zoom_canceled = False
        self.cancel_zoom_with_gaze = True

        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.scroll_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_scroll, self.scroll_timer)

        self.draw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_zoom, self.draw_timer)
        #Initialize canvas with dummy zoom_map (just to start program)
        self.current_zoom_map = ZoomMap(size=(400, 400),
                                        data_queue=self.data_q)
        self.current_scroller = WindowScroller(data_queue=self.data_q)
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
        #TODO: Use built in "alt" detection in event class
        self.zoom_canceled = False

        mod_down_event = event.Key in self.mod_keys
        trigger_down_event = event.Key in self.trigger_keys
        scroll_trigger_down_event = event.Key in self.scroll_trigger_keys

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

        #Start scrolling if alt-Scroll key pressed
        if (event.Key in self.scroll_trigger_keys and
                self.mod_key_now_down and not
                self.scroll_trigger_key_now_down):
            self.scroll_trigger_key_now_down = True
            self.start_scroll()

        # Do not pass through mod or trigger key events while zooming
        if (self.trigger_key_now_down or self.now_zooming and
            (mod_down_event or trigger_down_event)):
            return False

        # Do not pass through mod or trigger key events while scrolling
        if (self.scroll_trigger_key_now_down or self.now_scrolling and
            (mod_down_event or scroll_trigger_down_event)):
            return False

        #Use Escape key as backup zoom cancel
        if event.Key == "Escape" and self.trigger_key_now_down:
            self.zoom_canceled = True
            self.stop_zoom()
            return False  # Do not pass this cancel escape command

        #Cancel scroll on space if now scrolling
        if event.Key == "Space" and self.now_scrolling and self.stop_scroll_on_space:
            self.stop_scroll()
            return False  # Don't pass this key

        return True  # for pass through key events, False to eat Keys


    def on_key_up_event(self, event):
        if event.Key in self.mod_keys:
            self.mod_key_now_down = False
            if self.data_thread_running and not self.now_zooming and not self.now_scrolling:
                self.stop_data_thread()


        if event.Key in self.trigger_keys:
            self.trigger_key_now_down = False
            if self.zoom_triggered and not self.zoom_canceled:
                self.stop_zoom()

        if event.Key in self.scroll_trigger_keys:
            self.scroll_trigger_key_now_down = False
            if self.now_scrolling and not self.stop_scroll_on_space:
                self.stop_scroll()

        return True


    def click_target(self):
        self.current_zoom_map.click_target_center()
        pass

    def initialize_queue(self):
        with self.data_q.mutex:
            self.data_q.queue.clear()
        initial_values = pytribe.query_tracker()
        self.data_q.put(initial_values)

    def start_scroll(self):
        self.now_scrolling = True
        self.initialize_queue()
        self.start_data_thread()
        self.current_scroller = WindowScroller(data_queue=self.data_q)
        self.scroll_timer.Start(self.scroll_tick_ms)

        pass

    def update_scroll(self, event):
        self.current_scroller.update()

        if self.cancel_scroll_with_gaze:
            latest_center = self.current_scroller.latest_gaze_center
            window_rect = self.current_scroller.window_rect
            if ((latest_center[0] - window_rect[0] < -400 or  # gaze outside window left
                 latest_center[0] - window_rect[2] > 400)):  # gaze outside window right
                self.stop_scroll()
            elif self.current_scroller.latest_gaze_data_null:
                if pytribe.confirm_null_data():
                    self.stop_scroll()

    def stop_scroll(self):
        self.now_scrolling = False
        self.stop_data_thread()
        self.current_scroller.shutdown()
        self.scroll_timer.Stop()
        pass

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
            self.draw_timer.Start(self.zoom_tick_ms)
            self.Show()
            if not self.zoom_triggered:  # Immediately close+click if no-longer triggered
                self.stop_zoom()

    def stop_zoom(self):
        #TODO: Log data collected during each zoom
        self.zoom_triggered = False
        self.now_zooming = False
        self.stop_data_thread()
        self.Hide()
        self.draw_timer.Stop()
        if not self.zoom_canceled:
            self.click_target()

    def update_zoom(self, event):  # This "event" is required...
        self.canvas.update()

        if self.cancel_zoom_with_gaze and self.current_zoom_map.latest_gaze_data_null:
            if pytribe.confirm_null_data():
                self.zoom_canceled = True
                self.stop_zoom()

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

