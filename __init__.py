import time, socket, Queue

def jprint(your_json):
    import json
    parsed = json.loads(your_json)
    return json.dumps(parsed, indent=4, sort_keys=True)


def query_tracker(message=None):
    import socket
    HOST = 'localhost'
    PORT = 6555
    BUFFER_SIZE = 1024
    if message is None:
        message = """{
            "category": "tracker",
            "request" : "get",
            "values": [ "push", "iscalibrated" ]
        }"""

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.send(message)
    data = s.recv(BUFFER_SIZE)
    s.close()
    return jprint(data)


def extract_queue(q, l=None):
    if l == None: l = []

    while True:
        try:
            l.append(q.get(block=False))
        except Queue.Empty:
            return l
            break


def connect_to_tracker(host = 'localhost', port = 6555, buffer_size = 1024):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s


def queue_tracker_frames(queue, message=None, interval=0.03, points=100,
                        parse_func = lambda x: x['values']['frame']['raw']):
    if message == None:
        message = """
        {
            "category": "tracker",
            "request" : "get",
            "values": [ "frame" ]
        }"""

    import json
    s = connect_to_tracker()
    for _ in range(points):
        s.send(message)
        data = s.recv(1024)
        try: parsed = parse_func(json.loads(data))
        except ValueError: parsed = None
        q.put(parsed)
        time.sleep(interval)
    s.close()
    try: parsed = json.loads(data)
    except ValueError: parsed = None


def raw_value_tuples(raw_dict):
    raw_coords = raw_dict['values']['frame']['raw']
    x_y_tup = (raw_coords['x'],raw_coords['y'])
    return x_y_tup

def heartbeat_loop(loops=None):
    if loops is None:
        while True:
            query_tracker(message='{"category": "heartbeat"}')
            time.sleep(0.3)
    else:
        for _ in range(loops):
            query_tracker(message='{"category": "heartbeat"}')
            time.sleep(0.3)
