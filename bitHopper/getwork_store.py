#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

import gevent
import threading, time, socket

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

class Getwork_store:
    
    def __init__(self, bitHopper):
        self.data = {}
        self.bitHopper = bitHopper
        self.lock = threading.RLock()
        gevent.spawn(self.prune)

    def add(self, server, merkle_root, auth):
        with self.lock:
            self.data[merkle_root] = [server, time.time(), auth]

    def get_server(self, merkle_root):
        with self.lock:
            if self.data.has_key(merkle_root):
                return self.data[merkle_root][0] , self.data[merkle_root][2]
            return None , None    
            
    def drop_roots(self):
        with self.lock:
            self.data = {} 
    
    def prune(self):
        while True:
            with self.lock:
                for key, work in self.data.items():
                    if work[1] < (time.time() - (60*5)):
                        del self.data[key]
            gevent.sleep(60)
