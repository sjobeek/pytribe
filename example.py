import pytribe
import threading
import Queue
import time

#Start heartbeat thread
hb_thread = threading.Thread(target=pytribe.heartbeat_loop,
                             kwargs={})
hb_thread.daemon = True
hb_thread.start()

#Give the tracker time to wake up
time.sleep(0.1)

#Start collecting samples from the eye tracker and add to a queue
q=Queue.Queue()
query_thread = threading.Thread(target=pytribe.queue_tracker_frames, args=(q,),
                                kwargs=dict(interval=0.01))
query_thread.daemon=True
query_thread.start()

#Wait for data to be collected
time.sleep(1)

#Extract all of the samples from the queue
list_of_data_dicts = pytribe.extract_queue(q)

#First "average" data point
for item in list_of_data_dicts:
    print item['values']['frame']['avg']

