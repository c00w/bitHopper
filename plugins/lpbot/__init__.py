# Backdoor plugin
try:
    import eventlet
except Exception, e:
    print "You need to install greenlet. See the readme."
    raise e
from eventlet import wsgi, greenpool, backdoor
from eventlet.green import os, time, socket
import lpbot
eventlet.monkey_patch()

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

def main(bitHopper):
    bot = None
    if bitHopper.options.p2pLP:
        bot = lpbot.LpBot(bitHopper)
    return bot

