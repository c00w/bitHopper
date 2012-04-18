import time, gevent

seen = None

def used(url, http_pool):
    __patch()
    seen[(url, http_pool)] = time.time()
    
def __patch():
    global seen
    if seen is None:
        seen = {}
        gevent.spawn(clean)
        
def clean():
    while True:
        for k, last_seen in seen.items():
            if time.time()-last_seen < 0.3:
                continue
            
            url, pool = k
            pool.request(url, 'GET', headers = {'Connection':'close'})
        gevent.sleep(0.3)
            
                
