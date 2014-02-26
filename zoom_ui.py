import Queue
import wx
import pyHook
import pytribe


# Start eye tracker: zoom and click with alt-space
def main():

    data_q = Queue.Queue()

    app = wx.App(False)
    frame = pytribe.ZoomFrame(None,
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

