import time
import threading
import Queue
import wx
from bufferedcanvas import BufferedCanvas
import pytribe
import pyHook





def scale_bitmap(bitmap, width, height):
    image = wx.ImageFromBitmap(bitmap)
    image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
    image = image.Resize(size=(400, 400), pos=(-10,-10))
    result = wx.BitmapFromImage(image)
    return result


def current_bitmap():
    bitmap = wx.Bitmap('400x400_test.bmp')
    yield bitmap
    x = 1.1
    while True:
        bitmap = scale_bitmap(bitmap, 400*x, 400*x)
        yield bitmap


class ZoomCanvas(BufferedCanvas):

    def __init__(self, *args, **kwargs):
        #Initialization of bitmap_gen MUST come first
        self.bitmap_gen = current_bitmap()
        BufferedCanvas.__init__(self, *args, **kwargs)

    def draw(self, dc):
        dc.DrawBitmap(next(self.bitmap_gen), 0, 0)


class ZoomFrame(wx.Frame):

    """Main Frame holding the Panel."""
    def __init__(self, *args,  **kwargs):
        self.tick_ms = kwargs.pop('tick_ms', 100) # Remove non-standard kwargs
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
        #self.timer.Start(self.tick_ms)


    def on_key_down_event(self, event):
        if event.Key == 'Numlock' and not self.key_now_down:  # \ key = Oem_5
            print 'Ascii:', event.Key
            self.key_now_down = True
            self.canvas = ZoomCanvas(self, wx.ID_ANY,
                                 size=(400,400))
            self.Show()
            self.timer.Start(self.tick_ms)

        return True  # for pass through key events, False to eat Keys

    def update_zoom(self, event):  # This "event" is required...
        self.canvas.update()

    def on_key_up_event(self, event):

        self.key_now_down = False
        print 'Key up: ', event.Key
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
                      pos=(400,400),
                      size=(400,400),
                      style=wx.BORDER_NONE | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR,
                      tick_ms=50)


    hm = pyHook.HookManager()
    hm.KeyDown = frame.on_key_down_event
    hm.KeyUp = frame.on_key_up_event
    hm.HookKeyboard()


    heartbeat_thread = threading.Thread(target=pytribe.heartbeat_loop, args=(100,))
    heartbeat_thread.daemon = True
    heartbeat_thread.start()

    frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()

