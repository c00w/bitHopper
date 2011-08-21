#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import time
import threading

class LP_Callback():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self._lplock = threading.Lock()
        self._lplock.acquire()
        self.lp_data = None

    def read(self):
        "Gets the New Block work unit to send to clients
        self._lplock.acquire()
        return self.lp_data

    def new_block(self,work):
        "Called by LP to indicate a new_block as well as the work to send to clients"
        #Store the merkle root
        merkle_root = work['data'][72:136]
        self.bitHopper.getwork_store.add(server, merkle_root)

        #Setup the new locks, store the data and then release the old lock
        self.lp_data = work
        old_lock = self._lplock
        new_lock = threading.Lock()
        new_lock.acquire()
        self._lplock = new_lock
        old_lock.release()
        
