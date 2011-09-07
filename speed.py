#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import eventlet
from eventlet.green import threading, time, socket

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

class Speed():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.shares = 0
        self.lock = threading.RLock()
        eventlet.spawn_n(self.update_rate)
        self.rate = 0

    def add_shares(self, share):
        self.shares += share

    def update_rate(self):
        self.old_time=time.time()
        while True:
            now = time.time()
            diff = now -self.old_time
            if diff <=0:
                diff = 1
            self.old_time = now
            self.rate = int((float(self.shares) * (2**32)) / (diff * 1000000))
            self.shares = 0
            eventlet.sleep(60)

    def get_rate(self):
        return int(self.rate)
