"""
Deals with lagging logic for the system
"""

import btcnet_info
import gevent
import bitHopper.Network as Network
import bitHopper.LaggingLogic
import logging, traceback

def _unlag_fetcher(server, worker, password):
    """
    Actually fetches and unlags the server
    """
    try:
        url = btcnet_info.get_pool(server)['mine.address']
        work = Network.send_work(url, worker, password)
        if work:
            bitHopper.LaggingLogic.lagged.remove((server, worker, password))
            return
    except:
        logging.debug(traceback.format_exc())
        pass
   
def _unlag():
    """
    Function that checks for a server responding again
    """
    while True:
        for server, worker, password in bitHopper.LaggingLogic.lagged:
            gevent.spawn(_unlag_fetcher, server, worker, password)
               
        gevent.sleep(60)

gevent.spawn(_unlag)
