import time
import threading
import Queue
import wx
from bufferedcanvas import BufferedCanvas
import pytribe
import pyHook
from ScreenShotWX import screencapture




def current_bitmap(zoom_map):

    zm = zoom_map
    bitmap = zm.base_bitmap
    gaze_avg = zm.base_center
    yield bitmap
    x = 1.0
    while True:
        x *= 1.05
        gaze_data = pytribe.query_tracker()
        if gaze_data is not None:
            gaze_avg_dict = gaze_data['values']['frame']['avg']
            gaze_avg = (gaze_avg_dict['x'],gaze_avg_dict['y'])
        zm.zoom_base(center=gaze_avg, factor=x)
        bitmap = zm.zoom_bitmap #  scale_bitmap(bitmap, 400*x, 400*x)
        yield bitmap


class ZoomMap(object):
    """Contains original bitmap, plus transformed zoom coordinates.

    Methods allow for translation between "base" coordinates and "zoom" coordinates"""
    def __init__(self, center=(400,400), size=(400,400)):

        self.base_center = center
        self.base_size = size
        self.base_loc = (int(center[0] - size[0]/2.0),
                         int(center[1] - size[1]/2.0))
        #TODO: Handle case where base_loc +size includes areas outside of the screen?
        if self.base_loc[0] < 0: self.base_loc = (0, self.base_loc[1])
        if self.base_loc[1] < 0: self.base_loc = (self.base_loc[0], 0)

        self.base_bitmap = screencapture(self.base_loc, self.base_size)
        self.zoom_bitmap = self.base_bitmap
        self.base_image = wx.ImageFromBitmap(self.base_bitmap)


    def zoom_base(self, center=(0, 0), factor=1.0):


        #width/height to crop new image to before scaling up
        _width = self.base_size[0] / factor
        _height = self.base_size[1] / factor
        #Amount to shift new image down/right before scaling up
        _x = center[0] - self.base_center[0]
        _y = center[1] - self.base_center[1]

        #Prevent zooming in to sub-pixel range
        if _width <1: _width = 1
        if _height <=1: _height = 1

        #Prevent zooming outside of original box
        if _x < 0: _x = 0
        if _y < 0: _y = 0
        if _x + _width > self.base_size[0]: _x = self.base_size[0] - _width
        if _y + _height > self.base_size[1]: _y = self.base_size[1] - _height

        #Rect can be replaced by x,y,width,height tuple
        sub_image = self.base_image.GetSubImage((_x, _y, _width, _height))
        #Changes image in-place to
        #sub_image = self.base_image
        #sub_image.Resize(size=(_width, _height), pos=(-2, -2))

        zoomed_image = sub_image.Scale(self.base_size[0],
                                       self.base_size[1],
                                       wx.IMAGE_QUALITY_HIGH)
        self.zoom_bitmap = wx.BitmapFromImage(zoomed_image)

    def zoom_transformed(self, center, factor):
        pass


class ZoomCanvas(BufferedCanvas):

    def __init__(self, *args, **kwargs):
        #Initialization of bitmap_gen MUST come first
        self.bitmap_gen = current_bitmap(kwargs.pop('zoom_map'))
        BufferedCanvas.__init__(self, *args, **kwargs)

    def draw(self, dc):
        dc.DrawBitmap(next(self.bitmap_gen), 0, 0)

    def reset(self, zoom_map):
        self.bitmap_gen = current_bitmap(zoom_map)
        self.update()


class ZoomFrame(wx.Frame):

    """Main Frame holding the Panel."""
    def __init__(self, *args,  **kwargs):
        self.tick_ms = kwargs.pop('tick_ms', 25) # Remove non-standard kwargs
        wx.Frame.__init__(self, *args, **kwargs)

        self.raw_data_q = Queue.Queue()
        self.key_now_down = False

        #First argument is "parent" (ZoomFrame here), second is "ID"
        #self.canvas = ZoomCanvas(self, wx.ID_ANY,
        #                         size=kwargs['size'])
        #self.canvas.bitmap = wx.Bitmap('400x400_test.bmp')
        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_zoom, self.timer)
        self.canvas = ZoomCanvas(self, wx.ID_ANY,
                                 size=(400,400),
                                 zoom_map=ZoomMap(center=(400,400),
                                                  size=(400,400)))



        #self.timer.Start(self.tick_ms)


    def on_key_down_event(self, event):
        if event.Key == 'Numlock' and not self.key_now_down:  # \ key = Oem_5

            gaze_data = pytribe.query_tracker()
            if gaze_data is not None:
                gaze_avg_dict = gaze_data['values']['frame']['avg']
                gaze_avg = (gaze_avg_dict['x'],gaze_avg_dict['y'])
                zm = ZoomMap(center=gaze_avg, size=(400, 400))
                self.SetSize(zm.base_size)
                self.SetPosition(zm.base_loc)
                self.key_now_down = True
                self.canvas.reset(zm)
                self.timer.Start(self.tick_ms)
                self.Show()

        return True  # for pass through key events, False to eat Keys

    def update_zoom(self, event):  # This "event" is required...
        self.canvas.update()

    def on_key_up_event(self, event):

        self.key_now_down = False
        self.Hide()
        self.timer.Stop()
        return True

    def onClose(self, event):
        self.timer.Stop()
        self.query_thread.stop()
        self.Show(False)
        self.Destroy()


def main():




    app = wx.App(False)
    frame = ZoomFrame(None,
                      wx.ID_ANY,
                      title="Zoom Frame",
                      style=wx.BORDER_NONE | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR,
                      tick_ms=25)


    hm = pyHook.HookManager()
    hm.KeyDown = frame.on_key_down_event
    hm.KeyUp = frame.on_key_up_event
    hm.HookKeyboard()


    heartbeat_thread = threading.Thread(target=pytribe.heartbeat_loop, args=(100,))
    heartbeat_thread.daemon = True
    heartbeat_thread.start()

    #frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()

