# example hooks
import time
import gevent

import time, threading
from peak.util import plugins
import logging


class HookExample:
    """
    Example Plugin. Hooks into the main lp system and prints output
    """
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.log_dbg('Registering hooks')
        # Hook into the system and register a function
        hook_ann = plugins.Hook('plugins.lp.announce')
        hook_ann.register(self.lp_announce)
        
    def log_msg(self, msg):
        logging.info(msg)
    
    def log_dbg(self, msg):
        logging.debug(msg)
        
    def lp_announce(self, lpobj, body, server, block):
        """
        Recieved an LP, Log it.
        """
        self.log_dbg('lpobj: ' + str(lpobj))
        self.log_dbg('body: ' + str(lpobj))
        self.log_dbg('server: ' + str(server))
        self.log_dbg('block: ' + str(block))

def main(bitHopper):
    obj = HookExample(bitHopper)
