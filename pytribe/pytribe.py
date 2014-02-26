import time, socket, Queue

def jprint(your_json):
    import json
    parsed = json.loads(your_json)
    return json.dumps(parsed, indent=4, sort_keys=True)

def parse_center(data_dict_list, default=None, raw=False, round_int=False):
    """Parses the center value of the LAST item in a LIST of tracker data"""
    if len(data_dict_list) > 0:
        if raw:
            center_dict = data_dict_list[-1]['values']['frame']['raw']
            center = (center_dict['x'], center_dict['y'])
        else:
            center_dict = data_dict_list[-1]['values']['frame']['avg']
            center = (center_dict['x'], center_dict['y'])
    else:
        center = default
    if round_int:
        center = (int(round(center[0])), int(round(center[1])))
    return center

def query_tracker(message="""
                    {
                        "category": "tracker",
                        "request" : "get",
                        "values": [ "frame" ]
                    }""",
                  get_status=False, host='localhost',
                  port=6555, buffer_size=1024,
                  avg_only=False, post_wake_delay=None):
    """Directly query the eye-tribe tracker.

    Data is returned as a nested set of dictionaries and lists.
    The eye tracker server must be running and calibrated.
    Use get_status=True to over-ride message and query status.
    post_wake_delay to re-read sample _ sec after waking device"""

    import socket
    import json
    import time
    if get_status == True:
        message = """{
            "category": "tracker",
            "request" : "get",
            "values": [ "push", "iscalibrated" ]
        }"""

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.send(message)
    #pause to allow message to come through
    time.sleep(0.01)
    if post_wake_delay == None:
        data = s.recv(buffer_size)
    else:
        _ = s.recv(buffer_size)
        time.sleep(post_wake_delay)
        s.send(message)
        data = s.recv(buffer_size)
    s.close()
    try: parsed = json.loads(data)
    except ValueError: parsed = None
    if avg_only:  # Return a tuple if kwarg avg_only=True
        center_dict = parsed['values']['frame']['avg']
        parsed = (center_dict['x'], center_dict['y'])
    return parsed

def extract_queue(q, l=None):
    if l == None: l = []

    while True:
        try:
            l.append(q.get(block=False))
        except Queue.Empty:
            return l


def connect_to_tracker(host = 'localhost', port = 6555, buffer_size = 1024):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s


def queue_tracker_frames(queue, message=None, interval=0.01, event=None):
    """Read data from tracker in PUSH mode.

    Data is pushed into queue as it arrives, once per interval seconds.
    Does not play well with interval > 0.4
    """
    if message == None:
        message="""
        {
            "category": "tracker",
            "request": "set",
            "values": {
                "push": true,
                "version": 1
            }
        }"""

    import json
    s = connect_to_tracker()
    s.send(message)
    _ = s.recv(2**15)  # Discard first response
    loop = 0
    time.sleep(0.01)
    while True:
        loop += 1
        data = s.recv(2**15)
        data_list = [json.loads(line) for line in data.split('\n')
                     if line.split()]
        for point in data_list:
            queue.put(point)
        if loop > 20:
            s.send(message)
            _ = s.recv(2**15)
            loop = 0

        time.sleep(interval)

        if event is not None:
            if event.is_set():
                break
    s.close()


def raw_value_tuples(raw_dict):
    raw_coords = raw_dict['values']['frame']['raw']
    x_y_tup = (raw_coords['x'],raw_coords['y'])
    return x_y_tup

def heartbeat_loop(loops=None):
    if loops is None:
        while True:
            query_tracker(message='{"category": "heartbeat"}')
            time.sleep(0.2)
            print "HB"
    else:
        for _ in range(loops):
            query_tracker(message='{"category": "heartbeat"}')
            time.sleep(0.2)
