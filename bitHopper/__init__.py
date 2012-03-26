import gevent.monkey
#Not patching thread so we can spin of db file ops.
gevent.monkey.patch_all(thread=False, time=False)

#Monkey Patch httplib2
#import geventhttpclient.httplib
#geventhttpclient.httplib.patch()
import httplib2

import Logic
import Network
import Website
import Configuration

import logging, sys
logging.basicConfig(stream=sys.stdout, format="%(asctime)s|%(module)s: %(message)s", datefmt="%H:%M:%S", level = logging.INFO)


import gevent.wsgi, os
import Mining_Site

def setup_miner(port = 8337, host = ''):
    """
    Sets up the miner listening port
    """
    #Don't show the gevent logsg
    log = open(os.devnull, 'wb')
    server = gevent.wsgi.WSGIServer((host, port), Mining_Site.mine,  backlog=512,  log=log)
    gevent.spawn(_tb_wrapper, server)
    gevent.sleep(0)
    
def setup_control(port = 8339, host = ''):
    """
    Sets up the miner listening port
    """
    #Don't show the gevent logsg
    log = open(os.devnull, 'wb')
    server = gevent.wsgi.WSGIServer((host, port), Website.app,  backlog=512,  log=log)
    gevent.spawn(_tb_wrapper, server)
    gevent.sleep(0)
    
import logging, traceback
def _tb_wrapper(server):
    """
    Traceback Wrapper
    """
    while True:
        try:
            server.serve_forever()
        except (Exception, e):
            logging.error(traceback.format_exc())
