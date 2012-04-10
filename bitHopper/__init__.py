"""
BitHopper Library which handles everything.
The following functions need to be called
custom_pools() sets up additional pools for btcnet_info
setup_miner sets the port for the miner
setup_control sets the port for the control website
setup_logging() sets up the logging level
"""

import gevent.monkey
#Not patching thread so we can spin of db file ops.
gevent.monkey.patch_all(thread=False, time=False)

#Monkey Patch httplib2
#import geventhttpclient.httplib
#geventhttpclient.httplib.patch()
import httplib2
import gevent
import btcnet_info

import bitHopper.Logic
import bitHopper.Network
import bitHopper.Website
import bitHopper.Configuration
import bitHopper.Mining_Site

import logging, sys
def setup_logging(level=logging.INFO):
    """
    Sets up the logging output we want
    """
    logging.basicConfig(
            stream=sys.stdout, 
            format="%(asctime)s|%(module)s|%(funcName)s: %(message)s", 
            datefmt="%H:%M:%S", 
            level = level)


import gevent.wsgi, os

def custom_pools():
    """
    Loads custom pool filenames and tells btcnet_info about them
    """
    #Ugly hack to figure out where we are
    try:
        # determine if application is a script file or frozen exe
        if hasattr(sys, 'frozen'):
            FD_DIR = os.path.dirname(sys.executable)
        else:
            FD_DIR = os.path.dirname(os.path.abspath(__file__))
    except:
        FD_DIR = os.curdir
        
    filenames = [name for name in os.listdir(
                    os.path.join(FD_DIR,'../custom_pools')) 
                    if '.ignore' not in name]
    filenames = map(lambda x: os.path.join(os.path.join(FD_DIR,'../custom_pools'), x), filenames)
    filenames = map(os.path.abspath, filenames)
    btcnet_info.add_pools(filenames)
        

def setup_miner(port = 8337, host = ''):
    """
    Sets up the miner listening port
    """
    #Don't show the gevent logsg
    log = open(os.devnull, 'wb')
    server = gevent.wsgi.WSGIServer((host, port), 
            bitHopper.Mining_Site.mine,  
            backlog=512,  
            log=log)
    gevent.spawn(_tb_wrapper, server)
    gevent.sleep(0)
    
def setup_control(port = 8339, host = ''):
    """
    Sets up the miner listening port
    """
    #Don't show the gevent logsg
    log = open(os.devnull, 'wb')
    server = gevent.wsgi.WSGIServer((host, port), 
            bitHopper.Website.app,  
            backlog=512,  
            log=log)
    gevent.spawn(_tb_wrapper, server)
    gevent.sleep(0)
    
import traceback
def _tb_wrapper(server):
    """
    Traceback Wrapper
    """
    while True:
        try:
            server.serve_forever()
        except:
            logging.error(traceback.format_exc())
            gevent.sleep(10)
