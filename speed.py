#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import threading
from twisted.internet.task import LoopingCall

class Speed():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.shares = 0
        self.lock = threading.RLock()
        call = LoopingCall(self.update_rate)
        call.start(60)
        self.rate = 0

    def add_shares(self, share):
        with self.lock:
            self.shares += share

    def update_rate(self):
        with self.lock:
            self.rate = int((float(self.shares) * (2**32)) / (60 * 1000000))
            self.shares = 0

    def get_rate(self):
        with self.lock:
            return int(self.rate)
