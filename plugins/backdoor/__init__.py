# Backdoor plugin
try:
    import eventlet
except Exception, e:
    print "You need to install greenlet. See the readme."
    raise e
from eventlet import wsgi, greenpool, backdoor
from eventlet.green import os, time, socket
eventlet.monkey_patch()

def main(bitHopper):
    lastDefaultTimeout = socket.getdefaulttimeout()
    options = bitHopper.options
    config = bitHopper.config
    log = None 
    if options.debug:        
        backdoor_port = config.getint('backdoor', 'port')
        backdoor_enabled = config.getboolean('backdoor', 'enabled')
        if backdoor_enabled:
            try:
                socket.setdefaulttimeout(None)
                bitHopper.pile.spawn(backdoor.backdoor_server, eventlet.listen(('127.0.0.1', backdoor_port)), locals={'bh':bitHopper})
                socket.setdefaulttimeout(lastDefaultTimeout)
            except Exception, e:
                print e   
    else:
        log = open(os.devnull, 'wb')