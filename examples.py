import pytribe
import threading
import Queue

#Start heartbeat thread
hb_thread = threading.Thread(target=pytribe.heartbeat_loop,
                             kwargs={"loops":100})
hb_thread.daemon = True
hb_thread.start()


#Get 50 raw samples from the eye tracker and add to a queue
q=Queue.Queue()
query_thread = threading.Thread(target=pytribe.queue_tracker_frames, args=(q,),
                                kwargs=dict(parse_func=pytribe.raw_value_tuples,
                                            points=50))
query_thread.start()

#Wait for data to be collected
import time
time.sleep(2)

#Extract the 50 samples from the queue
print pytribe.extract_queue(q)


