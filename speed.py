#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import gevent
import threading, time, socket

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

    def add_shares(self, share):
        self.shares += share

    def update_rate(self, loop=True):
        self.old_time=time.time()
        while True:
            now = time.time()
            diff = now -self.old_time
            if diff <=0:
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
        
import unittest
class TestSpeed(unittest.TestCase):

    def setUp(self):
        import gevent.monkey
        gevent.monkey.patch_all(os=True, select=True, socket=True, thread=False, time=False)
        self.speed = Speed()

    def test_shares_add(self):
        self.speed.add_shares(100)
        self.speed.update_rate(loop=False)
        self.assertTrue(self.speed.get_rate() > 0)
   
    def test_shares_zero(self):
        self.speed.update_rate(loop=False)
        self.assertTrue(self.speed.get_rate() == 0)

if __name__ == '__main__':
    unittest.main()
