#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

import threading

class ResourceGenerator:
        def __init__(self, generate = lambda:None, pool = None, timeout = None):
            #Pool is a list of items
            #Generate creates a new item
            self.generate = generate
            self.pool = pool
            self.timeout = timeout
            
        def __enter__(self):
            #Check if an item is available
            for lock, item in self.pool:
                if lock.acquire(False):
                    self.lock = lock
                    return item
                    
            #Otherwise make a new item
            (lock, item) = (threading.Lock(), self.generate(self.timeout))
            lock.acquire()
            self.lock = lock
            self.pool.add((lock,item))
            return item
            
        def __exit__(self, type, value, traceback):
            self.lock.release()
            
class Pool:
    def __init__(self, generate):
        self.pools = {}
        self.generate = generate
        
    def __call__(self, url, timeout=None):
        key = url+str(timeout)
        if url not in self.pools:
        
            self.pools[key] = set()
        return ResourceGenerator(self.generate, pool = self.pools[key], timeout=timeout)
