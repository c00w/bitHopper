#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import time

from twisted.internet.task import LoopingCall

class Request_store:
    
    def __init__(self, bitHopper):
        self.data = {}
        self.bitHopper = bitHopper

    def add(self, request):
        self.data[request] = time.time()
        request.notifyFinish().addCallback(self.notifyFinished, request)
    
    def closed(self, request):
        return request not in self.data

    def notifyFinished(self, value, request):
        del self.data[request]
    
    def prune(self):
        for key, work in self.data.items():
            if work[1] < (time.time() - (60*5)):
                del self.data[key]
