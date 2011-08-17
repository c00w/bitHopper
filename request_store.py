#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import time

from twisted.internet.task import LoopingCall

class Request_store:
    
    def __init__(self, bitHopper):
        self.data = {}
        self.bitHopper = bitHopper

    def add(self, request, save_time = 0):
        self.data[request] = time.time() + save_time * 60
        d = request.notifyFinish()
        d.addCallback(self.notifyFinished, request)
        d.addErrback(self.notifyFinished, request)
        call = LoopingCall(self.prune)
        call.start(60)

    def closed(self, request):
        return request not in self.data

    def notifyFinished(self, value, request):
        try:
            del self.data[request]
        except Exception, e:
            self.bitHopper.log_dbg('Error deleting request')
            self.bitHopper.log_dbg(e)

    def prune(self):
        for key, work in self.data.items():
            if work < (time.time() - (60*5)):
                del self.data[key]
