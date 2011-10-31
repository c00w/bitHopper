# Backdoor plugin
try:
    import eventlet
except Exception, e:
    print "You need to install greenlet. See the readme."
    raise e
from eventlet import wsgi, greenpool, backdoor
from eventlet.green import os, time, socket
import lpdump
eventlet.monkey_patch()

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

def main(bitHopper):
    bot = None
    bot = lpdump.LpDump(bitHopper)
    return bot

