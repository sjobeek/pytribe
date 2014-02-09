import pytribe
import threading
import Queue
import time

#Start heartbeat thread
hb_thread = threading.Thread(target=pytribe.heartbeat_loop,
                             kwargs={"loops":100})
hb_thread.daemon = True
hb_thread.start()

#Give the tracker time to wait up
time.sleep(1)

#Get 50 raw samples from the eye tracker and add to a queue
q=Queue.Queue()
query_thread = threading.Thread(target=pytribe.queue_tracker_frames, args=(q,),
                                kwargs=dict(points=50))
query_thread.start()

#Wait for data to be collected
time.sleep(1)

#Extract all of the samples from the queue
list_of_data_dicts = pytribe.extract_queue(q)

#First "average" data point
print list_of_data_dicts[0]['values']['frame']['avg']
#First "raw" data point
print list_of_data_dicts[0]['values']['frame']['raw']

