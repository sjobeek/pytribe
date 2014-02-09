pytribe
=======

Simple python API wrapper for communicating with the EyeTribe eye-tracking server



Installation
-----

To install with pip, use `pip install git+https://github.com/sjobeek/pytribe.git`




Usage
-----

To simply read a single set of data, first `import pytribe` then `data = pytribe.query_tracker()`

See `example.py` for an example of how to read tracking data using non-blocking threads and a queue. This is useful for GUI applications where you can't allow the data collection polling to block the main loop.



Disclaimer
-----
This is extremely alpha-quality software - expect significant changes to API and interface in subsequent versions.
