pytribe
=======

Simple python API wrapper for communicating with the EyeTribe eye-tracking server



Installation
-----

To install with pip, use `pip install git+https://github.com/sjobeek/pytribe.git`




Usage
-----

Currently the eyetribe server must be started, and then calibrated using the eyetribe UI before this API can be used. The eyetribe UI does not need to remain open after calibration.

The current version ONLY supports simple reading of data using the pull and push methods.

To simply read a single set of data, first `import pytribe` then `data = pytribe.query_tracker()`

See `example.py` for an example of how to read tracking data using non-blocking threads and a queue. This is useful for GUI applications where you can't allow the data collection polling to block the main loop.  [NOTE: Currently a bug in this implementation - recommend using pull method only for now]



Disclaimer
-----
This is extremely alpha-quality software - expect significant changes to API and interface in subsequent versions.
