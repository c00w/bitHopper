"""
Deals with lagging logic for the system
"""

import gevent
from .. import Network

lagged = set() #A list of tuples (server, worker, password)
    
def lag( server, worker, password):
    """Mark an item as lagged """
    if (server, worker, password) not in lagged:
        lagged.add((server, worker, password))
        gevent.spawn(_unlag, server, worker, password)
    
def _unlag( server, worker, password):
    """
    Function that checks for a server responding again
    """
    sleep_time = 1
    while True:
        work = Network.get_work_credentials(server, worker, password)
        if work:
            lagged.remove((server, worker, password))
            return
        gevent.sleep(60 * sleep_time)
        sleep_time = sleep_time+1 if sleep_time < 10 else 10
        
def filter_lag( source):
    """
    Lag based filter
    """
    for server, worker, password in source:
        if (server, worker, password) not in lagged:
            yield (server, worker, password)
    
