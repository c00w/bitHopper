"""
BitHopper Library which handles everything.
The following functions need to be called
custom_pools() sets up additional pools for btcnet_info
setup_miner sets the port for the miner
setup_control sets the port for the control website
setup_logging() sets up the logging level
"""

import gevent
import gevent.pywsgi as pywsgi
import gevent.monkey
#Not patching thread so we can spin of db file ops.
gevent.monkey.patch_all(thread=False, time=False)

import btcnet_info

import bitHopper.Logic
import bitHopper.Network
import bitHopper.Website
import bitHopper.Configuration
import bitHopper.Mining_Site
import logging
import sys

def btcni_version_ok(min_version, version_string):
    version = [int(i) for i in version_string.split('.')]
    for i, j in zip(min_version, version):
        if j < i:
            return False
    return True

def print_btcni_ver():
    """
    Prints btcnet_info version info
    """
    if '__version__' not in dir(btcnet_info):
        logging.info('btcnet_info older than 0.1.2.22')
        logging.info('Please run sudo python setup.py install')
        sys.exit(0)

    logging.info('btcnet_info version %s', btcnet_info.__version__)

    min_version = [0, 1, 2, 27]
    if not btcni_version_ok([0, 1, 2, 27], btcnet_info.__version__):
        logging.info('Version to old, please use a version >= %s' % '.'.join(min_version))
        logging.info('Please run sudo python setup.py install')
        sys.exit(0)

    
__patched = False
def __patch():
    """
    One Time things should be done here
    """
    global __patched
    if __patched == False:
        __patched = True
        print_btcni_ver()
        

def setup_logging(level=logging.INFO):
    """
    Sets up the logging output we want
    """
    
    logging.basicConfig(
            stream=sys.stdout, 
            format="%(asctime)s|%(module)s|%(funcName)s: %(message)s", 
            datefmt="%H:%M:%S", 
            level = level)
    __patch()


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
    server = pywsgi.WSGIServer((host, port), 
            bitHopper.Mining_Site.mine,  
            backlog=32,  
            log=log)
    gevent.spawn(_tb_wrapper, server)
    gevent.sleep(0)
    
def setup_control(port = 8339, host = ''):
    """
    Sets up the miner listening port
    """
    #Don't show the gevent logsg
    log = open(os.devnull, 'wb')
    server = pywsgi.WSGIServer((host, port), 
            bitHopper.Website.app,  
            backlog=1024,  
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
