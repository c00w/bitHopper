# Backdoor plugin
try:
    import gevent
except Exception, e:
    print "You need to install greenlet. See the readme."
    raise e
import logging 
   
from gevent import wsgi, backdoor
import os, time, socket

def main(bitHopper):
    backdoor_port = bitHopper.config.getint('backdoor', 'port')
    try:
        lastDefaultTimeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(None)
        gevent.spawn(backdoor.BackdoorServer, ('127.0.0.1', backdoor_port), locals={'bh':bitHopper})
        socket.setdefaulttimeout(lastDefaultTimeout)
    except Exception, e:
        logging.info("Unable to start up backdoor: %s", e)

