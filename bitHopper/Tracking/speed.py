#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

import gevent
import time, socket

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

class Speed():
    """
    This class keeps track of the number of shares and
    tracks a running rate in self.rate
    
    Add shares with
    a = Speed()
    a.add_shares(1)
    
    Get the rate with 
    a.get_rate()
    
    Note rates are tallied once per minute.
    
    """
    def __init__(self):
        self.shares = 0
        gevent.spawn(self.update_rate)
        self.rate = 0
        self.old_time = time.time()

    def add_shares(self, share):
        self.shares += share

    def update_rate(self, loop=True):
        while True:
            now = time.time()
            diff = now -self.old_time
            if diff <= 0:
                diff = 1e-10
            self.old_time = now
            self.rate = int((float(self.shares) * (2**32)) / (diff * 1000000))
            self.shares = 0
            
            if loop:
                gevent.sleep(60)
            else:
                return
            

    def get_rate(self):
        return self.rate
