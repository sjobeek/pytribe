
"""
A WX cross-platform method to capture any arbitrary portion
of the Desktop screen. Any extended screens can be captured using
appropriate absolute screen coordinates.

Ray Pasco
pascor(at)verizon(dot)net
2011-04-20-Wed__PM-04-52-36__April

Adapted from "How to Take a Screenshot of Your wxPython App and Print it" @
http://www.blog.pythonlibrary.org/2010/04/16/how-to-take-a-screenshot-of-your-wxpython-app-and-print-it/


Revision History :

2011-04-20 Debug Rev v1.2.2
    Using wx.Bitmap.IsOk() as the validity check for the call to wx.ScreenDC.GetAsBitmap().

Platform  Linux
Python    2.6.6 (r266:84292, Sep 15 2010, 15:52:39)
[GCC 4.4.5]
Wx Version 2.8.11.0
Wx Platform ('__WXGTK__', 'wxGTK', 'unicode', 'gtk2', 'wx-assertions-off', 'SWIG-1.3.29')

2011-04-18  Debug Rev v1.2.1
    Added statements specifically for debugging. Enable by calling with "(... , debug=True)"

2011-04-15  Rev 1.2  RDP:
    screenDC.GetAsBitmap() isn't implemented on MSW :(  Reversion to original Desktop bitmap
    aquisition code only if scrDC.GetAsBitmap() isn't implemented.

2011-03-25  Rev. 1.1   OS-X 10.6 tested:
Adapted for Mac by:
Chris Barker
Chris.Barker (at) noaa (dot) gov

Wx Version 2.8.11.0
Wx Pltform ('__WXMAC__', 'wxMac', 'unicode', 'wx-assertions-on', 'SWIG-1.3.29', 'mac-cg', 'mac-native-tb')


2011-03-25  Rev. 1.0    MS Win7 tested.
Ray Pasco
pascor(at)verizon(dot)net

Windows   6.1.7600
Python    2.6.5 (r265:79096, Mar 19 2010, 21:48:26) [MSC v.1500 32 bit (Intel)]
Wx Version 2.8.11.0
Wx Pltform ('__WXMSW__', 'wxMSW', 'unicode', 'wx-assertions-on', 'SWIG-1.3.29')

"""
import sys
import wx

#------------------------------------------------------------------------------

def screencapture( captureStartPos, captureBmapSize, debug=False ):
    """
    General Desktop screen portion capture - partial or entire Desktop.

    My particular screen hardware configuration:
        wx.Display( 0 ) refers to the extended Desktop display monitor screen.
        wx.Display( 1 ) refers to the primary  Desktop display monitor screen.

    Any particular Desktop screen size is :
        screenRect = wx.Display( n ).GetGeometry()

    Different wx.Display's in a single system may have different dimensions.
    """

    # A wx.ScreenDC provides access to the entire Desktop.
    # This includes any extended Desktop monitor screens that are enabled in the OS.
    scrDC = wx.ScreenDC()
    scrDcSize = scrDC.Size
    scrDcSizeX, scrDcSizeY = scrDcSize

    # Cross-platform adaptations :
    scrDcBmap     = scrDC.GetAsBitmap()
    scrDcBmapSize = scrDcBmap.GetSize()
    if debug :
        print 'DEBUG:  Size of scrDC.GetAsBitmap() ', scrDcBmapSize

    # Check if scrDC.GetAsBitmap() method has been implemented on this platform.
    if   not scrDcBmap.IsOk() :   # Not implemented :  Get the screen bitmap the long way.

        if debug :
            print 'DEBUG:  Using memDC.Blit() since scrDC.GetAsBitmap() is nonfunctional.'

        # Create a new empty (black) destination bitmap the size of the scrDC.
        # Overwrire the invalid original "scrDcBmap".
        scrDcBmap = wx.EmptyBitmap( *scrDcSize )
        scrDcBmapSizeX, scrDcBmapSizeY = scrDcSize

        # Create a DC tool that is associated with scrDcBmap.
        memDC = wx.MemoryDC( scrDcBmap )

        # Copy (blit, "Block Level Transfer") a portion of the screen bitmap
        #   into the returned capture bitmap.
        # The bitmap associated with memDC (scrDcBmap) is the blit destination.

        memDC.Blit( 0, 0,                           # Copy to this start coordinate.
                    scrDcBmapSizeX, scrDcBmapSizeY, # Copy an area this size.
                    scrDC,                          # Copy from this DC's bitmap.
                    0, 0,                    )      # Copy from this start coordinate.

        memDC.SelectObject( wx.NullBitmap )     # Finish using this wx.MemoryDC.
                                                # Release scrDcBmap for other uses.
    else :

        if debug :
            print 'DEBUG:  Using scrDC.GetAsBitmap()'

        # This platform has scrDC.GetAsBitmap() implemented.
        scrDcBmap = scrDC.GetAsBitmap()     # So easy !  Copy the entire Desktop bitmap.

        if debug :
            print 'DEBUG:  scrDcBmap.GetSize() ', scrDcBmap.GetSize()

    #end if

    return scrDcBmap.GetSubBitmap( wx.RectPS( captureStartPos, captureBmapSize ) )

#end ScreenCapture def
