#!/usr/bin/python
#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

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
        self._event.wait()
        return self.work

    def new_block(self, work, server, auth):
        "Called by LP to indicate a new_block as well as the work to send to clients"
        
        #Drop all current merkle roots
        self.bitHopper.getwork_store.drop_roots()
        
        #Store the merkle root
        merkle_root = work['data'][72:136]
        self.bitHopper.getwork_store.add(server, merkle_root, auth)

        #Setup the new locks, store the data and then release the old lock
        old = self._event
        self._event = event.Event()
        self.work = work
        old.set()
        
