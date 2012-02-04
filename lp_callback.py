#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import time
from gevent import event
import threading, socket

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

class LP_Callback():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self._event = event.Event()

    def read(self):
        "Gets the New Block work unit to send to clients"
        return self._event.wait()

    def new_block(self, work, server):
        "Called by LP to indicate a new_block as well as the work to send to clients"
        #Store the merkle root
        merkle_root = work['data'][72:136]
        self.bitHopper.getwork_store.add(server, merkle_root)

        #Setup the new locks, store the data and then release the old lock
        old = self._event
        self._event = event.Event()
        old.send(work)
        
