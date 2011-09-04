# example hooks
import time
import eventlet

from eventlet.green import time, threading
from peak.util import plugins


class HookExample:
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.log_dbg('Registering hooks')
        # register plugin hooks        
        hook_ann = plugins.Hook('plugins.lp.announce')
        hook_ann.register(self.lp_announce)
        
    def log_msg(self, msg):
        self.bitHopper.log_msg(msg, cat='block-accuracy')
    
    def log_dbg(self, msg):
        self.bitHopper.log_dbg(msg, cat='block-accuracy')
        
    def lp_announce(self, lpobj, body, server, block):
        self.log_dbg('lpobj: ' + str(lpobj))
        self.log_dbg('body: ' + str(lpobj))
        self.log_dbg('server: ' + str(server))
        self.log_dbg('block: ' + str(block))

def main(bitHopper):
    obj = HookExample(bitHopper)
