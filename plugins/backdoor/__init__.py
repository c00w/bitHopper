# Backdoor plugin
try:
    import eventlet
except Exception, e:
    print "You need to install greenlet. See the readme."
    raise e
import logging 
   
from eventlet import wsgi, greenpool, backdoor
from eventlet.green import os, time, socket
eventlet.monkey_patch()

# Global timeout for sockets in case something leaks
socket.setdefaulttimeout(900)

def main(bitHopper):
    backdoor_port = bitHopper.config.getint('backdoor', 'port')
    try:
        lastDefaultTimeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(None)
        bitHopper.pile.spawn(backdoor.backdoor_server, eventlet.listen(('127.0.0.1', backdoor_port)), locals={'bh':bitHopper})
        socket.setdefaulttimeout(lastDefaultTimeout)
    except Exception, e:
        logging.info("Unable to start up backdoor: %s") % (e)

